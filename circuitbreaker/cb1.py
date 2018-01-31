from datetime import datetime, timedelta
from functools import wraps
import sched, time

class CircuitBreaker(object):
    STATE_CLOSED = "closed"
    STATE_OPEN = "open"
    STATE_HALF_OPEN = "half_open"

    DEFAULT_FAILURE_THRESHOLD = 3
    DEFAULT_RECOVERY_TIMEOUT = 5
    DEFAULT_EXPECTED_EXCEPTIONS = (Exception)

    def __init__(self,
                 failure_threshold=None,
                 recovery_timeout=None,
                 expected_exceptions=None,
                 name=None):
        print("Init")
        self._failure_count = 0
        self._failure_threshold = failure_threshold or self.DEFAULT_FAILURE_THRESHOLD
        self._recovery_timeout = recovery_timeout or self.DEFAULT_RECOVERY_TIMEOUT

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
        self._opened = datetime.utcnow()

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
            raise CircuitBreakerError(self)

        try:
            result = func(*args, **kwargs)
        except self._expected_exceptions as e:
            print("Exception: ", type(e))
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
            self._opened = datetime.utcnow()

    @property
    def state(self):
        if self._state == self.STATE_OPEN and self.open_remaining <= 0:
            return self.STATE_HALF_OPEN

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
        return 'Circuit "%s" OPEN until %s (%d failures, %d sec remaining)' % (
            self._circuit_breaker.name,
            self._circuit_breaker.open_until,
            self._circuit_breaker.failure_count,
            round(self._circuit_breaker.open_remaining)
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


'''
def circuit(failure_threshold=None,
            recovery_timeout=None,
            expected_exceptions=None,
            name=None,
            cls=CircuitBreaker):

    if callable(failure_threshold):
        return cls().decorate(failure_threshold)

    return cls(
        failure_threshold=failure_threshold,
        recovery_timeout=recovery_timeout,
        expected_exceptions=expected_exceptions,
        name=name)
'''
