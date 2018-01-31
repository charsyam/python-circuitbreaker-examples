# python-circuitbreaker-examples
Python CircuitBreaker Examples to show how circuitbreaker works.

## Notice
This is modification of https://github.com/fabfuel/circuitbreaker
I added two features to show how circuitbreaker works.
original version is just throw Exception and check periodically with HALF_OPEN_STATE.
so it will show error periodically to users.

### cb1

It is almost same with https://github.com/fabfuel/circuitbreaker.
but it can handle multiple exceptions.

### cb2

It supports fail_back function.
so it doesn't throw CircuitBreakerError Exception, it just runs fail_back.
I think this is more clear. But it still check using HALF_OPEN_STATE.
so it will show error periodically to users.

### cb3

It supports cb2 + health_checker function using another process.
so, when health_checker successed, circuitbreaker comes back to CLOSED state.
