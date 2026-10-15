"""In-memory sliding-window rate limiter (CLAUDE.md 12.9).

Shared by the API and the MCP server so a client cannot bypass a limit by
switching transport. Single-instance, process-local — adequate for the
hackathon's single Railway service. A multi-instance deployment would move
this to Redis.

Limits are enforced per identity (user id or client IP). Every external call
also has its own timeout elsewhere; this guards against floods and cost abuse.
"""

from __future__ import annotations

import threading
import time
from collections import defaultdict, deque

# Default policy values (CLAUDE.md 12.9).
CHECK_PER_MINUTE = (10, 60)
CHECK_PER_DAY = (100, 86_400)
LOGIN_PER_MINUTE = (5, 60)
ALERT_PER_DAY = (3, 86_400)


class RateLimiter:
    def __init__(self) -> None:
        self._events: dict[str, deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()

    def allow(self, key: str, limit: int, window_seconds: int) -> bool:
        """Return True if an event under `key` is allowed right now."""
        now = time.monotonic()
        cutoff = now - window_seconds
        with self._lock:
            events = self._events[key]
            while events and events[0] < cutoff:
                events.popleft()
            if len(events) >= limit:
                return False
            events.append(now)
            return True

    def check(self, key: str, policy: tuple[int, int]) -> bool:
        limit, window = policy
        return self.allow(key, limit, window)


limiter = RateLimiter()
