import time
from riotwatcher import ApiError

class RateLimitRule:

    # Requests is number of requests allowable in given rule
    # Seconds in number of seconds rule lasts
    # Slack is how many seconds to add to each rule to account for lag
    def __init__(self, requests, seconds, slack=2):
        self.requests = requests
        self.seconds = seconds
        self.slack = slack
        self.window = []

    def enforce(self):
        now = time.time()
        # First remove entries outside of given time window
        filter_function = lambda t: (now - t) < (self.seconds + self.slack)
        self.window = list(filter(filter_function, self.window))
        # Next wait as long as necessary to send another request
        if len(self.window) == self.requests:
            time_to_wait = now - self.window[0]
            time.sleep(time_to_wait)
        # Finally add current time to time window
        self.window.append(time.time())
        


class RateLimiter:
    # Rules is [RateLimitRule]
    def __init__(self, rules=[]):
        self.rules = rules
    
    # Call a function with arguments while enforcing rate limit
    def call(self, func, *args):
        # enforce rate limit rules
        for rule in self.rules:
            rule.enforce()
        try:
            return func(*args)
        except ApiError as err:
            if err.response.status_code == 400:
                print("Error 400 - Bad request")
                exit(1)
            elif err.response.status_code == 401:
                print("Error 401 - Unauthorized")
                exit(1)
            elif err.response.status_code == 403:
                print("Error 403 - Forbidden")
                exit(1)
            elif err.response.status_code == 404:
                print("Error 404 - Data not found")
                exit(1)
            elif err.response.status_code == 405:
                print("Error 405 - Method not allowed")
                exit(1)
            elif err.response.status_code == 415:
                print("Error 415 - Unsupported media type")
                exit(1)
            elif err.response.status_code == 429:
                print("Error 429 - Rate limit exceeded")
                return self.call(func, *args)
            elif err.response.status_code == 500:
                print("Error 500 - Internal server error")
                return self.call(func, *args)
            elif err.response.status_code == 502:
                print("Error 502 - Bad gateway")
                return self.call(func, *args)
            elif err.response.status_code == 503:
                print("Error 503 - Service unavailable")
                return self.call(func, *args)
            elif err.response.status_code == 504:
                print("Error 504 - Gateway timeout")
                return self.call(func, *args)
            else:
                raise