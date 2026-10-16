"""In-memory limit on questions per hour, so a public demo cannot use up the model quota.

Counts are kept per client and for everyone together. They live in this process only,
which is enough for a single small server; several servers would need a shared store.
"""
import threading
import time
from collections import deque
from collections.abc import Callable

EVERYONE = "*"
MAX_TRACKED_CLIENTS = 10_000


class RateLimiter:
    def __init__(self, per_client: int, total: int, window_seconds: float = 3600,
                 clock: Callable[[], float] = time.monotonic):
        self.per_client = per_client  # 0 turns the limit off
        self.total = total
        self.window = window_seconds
        self._clock = clock
        self._hits: dict[str, deque[float]] = {}
        self._lock = threading.Lock()  # endpoints run in worker threads

    def allow(self, client: str) -> bool:
        """Records a question and returns False when the client or everyone together is over the limit."""
        if self.per_client <= 0:
            return True
        now = self._clock()
        with self._lock:
            if len(self._hits) > MAX_TRACKED_CLIENTS:
                self._forget_idle(now)
            client_hits = self._recent(client, now)
            all_hits = self._recent(EVERYONE, now)
            if len(client_hits) >= self.per_client or len(all_hits) >= self.total:
                return False
            client_hits.append(now)
            all_hits.append(now)
            return True

    def _recent(self, key: str, now: float) -> deque[float]:
        hits = self._hits.setdefault(key, deque())
        while hits and hits[0] <= now - self.window:
            hits.popleft()
        return hits

    def _forget_idle(self, now: float) -> None:
        self._hits = {key: hits for key, hits in self._hits.items() if hits and hits[-1] > now - self.window}
