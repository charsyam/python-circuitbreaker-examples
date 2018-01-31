from circuitbreaker.cb3 import CircuitBreaker, CircuitBreakerError, CircuitBreakerMonitor
import random
import urllib3
import requests
import sys

def fail_back(v):
    return "FailBack: Hello, {v}".format(v=v)

def health_checker():
    import requests
    ret = False
    try:
        url = 'http://127.0.0.1:5000/1'
        r = requests.get(url)
        ret = True
    except Exception as e:
        pass

    return ret
    
def fail_back2(v):
    return "FailBack2: Hello, {v}".format(v=v)

def health_checker2():
    import requests
    ret = False
    try:
        url = 'http://127.0.0.1:6000/1'
        r = requests.get(url)
        ret = True
    except Exception as e:
        pass

    return ret

@CircuitBreaker(fail_back=fail_back, recovery_timeout=10, health_checker=health_checker)
def call_circuit(v):
    url = 'http://127.0.0.1:5000/{v}'.format(v=v)
    r = requests.get(url)
    return r.text


@CircuitBreaker(fail_back=fail_back2, recovery_timeout=3, health_checker=health_checker2)
def call_circuit2(v):
    url = 'http://127.0.0.1:6000/{v}'.format(v=v)
    r = requests.get(url)
    return r.text
        

def run():
    while True:
        try:
            result = call_circuit(random.randint(1, 100000))
            result2 = call_circuit2(random.randint(1, 100000))
        except KeyboardInterrupt:
            raise
        except Exception as e:
            print(type(e))
            print(sys.exc_info())


if __name__ == '__main__':
    run()
