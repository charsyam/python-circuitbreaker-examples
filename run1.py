from circuitbreaker.cb1 import CircuitBreaker, CircuitBreakerError, CircuitBreakerMonitor
import random
import urllib3
import requests
import sys

@CircuitBreaker()
def call_circuit(v):
    url = 'http://127.0.0.1:5000/{v}'.format(v=v)
    r = requests.get(url)
    print(r.text)
    return r.text
        
def run():
    while True:
        try:
            call_circuit(random.randint(1, 100000))
        except CircuitBreakerError:
            print("CircuitBreaker: Use another value")
        except KeyboardInterrupt:
            raise
        except Exception as e:
            print(type(e))
            print(sys.exc_info())


if __name__ == '__main__':
    import pdb; pdb.set_trace()
    run()
