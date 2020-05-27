import time

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
        except Exception:
            print("Oops")
            return self.call(func, *args)