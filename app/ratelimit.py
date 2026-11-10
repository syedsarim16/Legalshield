import time
from collections import defaultdict, deque

from .errors import ApiError


class RateLimiter:
    """Simple in-memory sliding window (single process). Use Redis when scaling out."""

    def __init__(self, max_calls: int, window_seconds: int, code: str, message: str):
        self.max_calls, self.window, self.code, self.message = max_calls, window_seconds, code, message
        self._hits: dict[str, deque] = defaultdict(deque)

    def check(self, key: str) -> None:
        now = time.monotonic()
        q = self._hits[key]
        while q and now - q[0] > self.window:
            q.popleft()
        if len(q) >= self.max_calls:
            raise ApiError(429, self.code, self.message)
        q.append(now)

    def reset(self) -> None:
        self._hits.clear()
