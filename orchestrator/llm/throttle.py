# orchestrator/llm/throttle.py
import time
import threading


class TokenBucket:
    def __init__(self, rate_per_sec: float, capacity: int):
        self.rate = rate_per_sec
        self.capacity = capacity
        self.tokens = capacity
        self.timestamp = time.time()
        self.lock = threading.Lock()

    def take(self, tokens: float = 1.0) -> bool:
        with self.lock:
            now = time.time()
            elapsed = now - self.timestamp
            self.timestamp = now
            self.tokens = min(self.capacity, self.tokens + elapsed * self.rate)
            if self.tokens >= tokens:
                self.tokens -= tokens
                return True
            return False
