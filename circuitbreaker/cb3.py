import marshal
import time
import types
import random
from datetime import datetime, timedelta
from functools import wraps
from multiprocessing import Process, Array, Queue


health_check_queue = Queue()
health_check_status = Array('i', [1] * 100)
circuitbreaker_index = 0


class CircuitBreakerHealthCheckerItem:
    def __init__(self, func, timeout, checked_at):
        self.func = func
        self.timeout = timeout
        self.checked_at = checked_at

 
def CircuitBreakerHealthChecker(queue, states):
    checker = {}

    while True:
        item = None
        try:
            item = queue.get(False)
        except Exception as e:
            pass
            
        if item is not None:
            idx = item[0]
            code = marshal.loads(item[1])
            timeout = item[2]
            func = types.FunctionType(code, globals(), "health_checker_{idx}".format(idx=idx))
            next_checked_at = datetime.utcnow() + timedelta(seconds=timeout)
            checker[idx] = CircuitBreakerHealthCheckerItem(func, timeout, next_checked_at)

        deleted_idxs = []

        now = datetime.utcnow()
        for idx in checker:
            item = checker[idx]
            if now >= item.checked_at:
                print("check: ", idx)
                ret = item.func()
                if ret == True:
                    states[idx] = 1
                    deleted_idxs.append(idx)
                else:
                    item.checked_at = now + timedelta(seconds=item.timeout)
            else:
                print("skip: ", idx)
            
        for idx in deleted_idxs:
            del checker[idx]

        time.sleep(1)
    

p = Process(target=CircuitBreakerHealthChecker, args=(health_check_queue, health_check_status,))
p.start()

    
class CircuitBreaker(object):
    STATE_CLOSED = "closed"
    STATE_OPEN = "open"
    STATE_HALF_OPEN = "half_open"

    DEFAULT_FAILURE_THRESHOLD = 3
    DEFAULT_RECOVERY_TIMEOUT = 5
    DEFAULT_EXPECTED_EXCEPTIONS = (Exception)

    def __init__(self,
                 health_checker,
                 failure_threshold=None,
                 recovery_timeout=None,
                 expected_exceptions=None,
                 name=None,
                 fail_back=None):
        global circuitbreaker_index
        self._circuitbreaker_index = circuitbreaker_index
        circuitbreaker_index += 1

        self._failure_count = 0
        self._failure_threshold = failure_threshold or self.DEFAULT_FAILURE_THRESHOLD
        self._recovery_timeout = recovery_timeout or self.DEFAULT_RECOVERY_TIMEOUT
        self._health_check_queue = health_check_queue
        self._health_check_status = health_check_status

        if expected_exceptions is None:
            self._expected_exceptions = self.DEFAULT_EXPECTED_EXCEPTIONS
        elif isinstance(expected_exceptions, list):
            self._expected_exceptions = tuple(expected_exceptions)
        elif isinstance(expected_exceptions, tuple):
            self._expected_exceptions = expected_exceptions
        else:
            #Single Parameters
            self._expected_exceptions = (expected_exceptions)

        self._name = name
        self._state = self.STATE_CLOSED
        self._fail_back = fail_back
        self._health_checker = health_checker
        self._serialized_func = marshal.dumps(self._health_checker.__code__)

    def __call__(self, wrapped):
        return self.decorate(wrapped)

    def decorate(self, func):
        if self._name is None:
            self._name = func.__name__

        CircuitBreakerMonitor.register(self)

        @wraps(func)
        def wrapper(*args, **kwargs):
            return self.call(func, *args, **kwargs)

        return wrapper


    def call(self, func, *args, **kwargs):
        if self.opened:
            if self._fail_back is not None:
                return self._fail_back(*args, **kwargs)
            else:
                raise CircuitBreakerError(self) 

        try:
            result = func(*args, **kwargs)
        except self._expected_exceptions as e:
            self.__call_failed()
            raise

        self.__call_succeeded()
        return result

    def __call_succeeded(self):
        self._state = self.STATE_CLOSED
        self._failure_count = 0

    def __call_failed(self):
        self._failure_count += 1
        if self._failure_count >= self._failure_threshold:
            self._state = self.STATE_OPEN
            self._health_check_status[self._circuitbreaker_index] = 0
            cb_item = (self._circuitbreaker_index, self._serialized_func, self._recovery_timeout)
            self._health_check_queue.put(cb_item)

    @property
    def state(self):
        if self._health_check_status[self._circuitbreaker_index] == 0:
            self._state = self.STATE_OPEN
        else:
            self._state = self.STATE_CLOSED

        return self._state

    @property
    def open_until(self):
        return self._opened + timedelta(seconds=self._recovery_timeout)

    @property
    def open_remaining(self):
        return (self.open_until - datetime.utcnow()).total_seconds()

    @property
    def failure_count(self):
        return self._failure_count

    @property
    def closed(self):
        return self.state == self.STATE_CLOSED

    @property
    def opened(self):
        return self.state == self.STATE_OPEN

    @property
    def name(self):
        return self._name

    def __str__(self, *args, **kwargs):
        return self._name


class CircuitBreakerError(Exception):
    def __init__(self, circuit_breaker, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._circuit_breaker = circuit_breaker

    def __str__(self, *args, **kwargs):
        return 'Circuit "%s" status : "%s"' % (
            self._circuit_breaker.name,
            self._circuit_breaker.state
        )
        

class CircuitBreakerMonitor(object):
    circuit_breakers = {}

    @classmethod
    def register(cls, circuit_breaker):
        cls.circuit_breakers[circuit_breaker.name] = circuit_breaker

    @classmethod
    def all_closed(cls) -> bool:
        return len(list(cls.get_open())) == 0

    @classmethod
    def get_circuits(cls) -> [CircuitBreaker]:
        return cls.circuit_breakers.values()

    @classmethod
    def get(cls, name) -> CircuitBreaker:
        return cls.circuit_breakers.get(name)

    @classmethod
    def get_open(cls) -> [CircuitBreaker]:
        for _circuit in cls.get_circuits():
            if _circuit.opened:
                yield _circuit

    @classmethod
    def get_closed(cls) -> [CircuitBreaker]:
        for _circuit in cls.get_circuits():
            if _circuit.closed:
                yield _circuit
