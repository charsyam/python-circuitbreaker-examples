from circuitbreaker.cb2 import CircuitBreaker, CircuitBreakerError, CircuitBreakerMonitor
import random
import urllib3
import requests
import sys

def fail_back(v):
    return "FailBack: Hello, {v}".format(v=v)

@CircuitBreaker(fail_back=fail_back)
def call_circuit(v):
    url = 'http://127.0.0.1:5000/{v}'.format(v=v)
    r = requests.get(url)
    return r.text
        
def run():
    while True:
        try:
            result = call_circuit(random.randint(1, 100000))
            print(result)
        except KeyboardInterrupt:
            raise
        except Exception as e:
            print(type(e))
            print(sys.exc_info())


if __name__ == '__main__':
    run()
