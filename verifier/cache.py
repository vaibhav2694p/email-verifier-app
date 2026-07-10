import threading
import time
from typing import Any, Dict, Optional


class TTLCache:
    def __init__(self, default_ttl: int = 3600, max_size: int = 10000):
        self._cache: Dict[str, tuple] = {}
        self._lock = threading.Lock()
        self._default_ttl = default_ttl
        self._max_size = max_size

    def get(self, key: str) -> Optional[Any]:
        with self._lock:
            if key in self._cache:
                value, expiry = self._cache[key]
                if time.time() < expiry:
                    return value
                del self._cache[key]
        return None

    def set(self, key: str, value: Any, ttl: Optional[int] = None):
        with self._lock:
            if len(self._cache) >= self._max_size:
                self._evict_expired()
                if len(self._cache) >= self._max_size:
                    self._evict_oldest()
            self._cache[key] = (value, time.time() + (ttl or self._default_ttl))

    def delete(self, key: str):
        with self._lock:
            self._cache.pop(key, None)

    def clear(self):
        with self._lock:
            self._cache.clear()

    def _evict_expired(self):
        now = time.time()
        expired = [k for k, (_, exp) in self._cache.items() if now >= exp]
        for k in expired:
            del self._cache[k]

    def _evict_oldest(self):
        if self._cache:
            oldest_key = min(self._cache, key=lambda k: self._cache[k][1])
            del self._cache[oldest_key]

    def __len__(self):
        return len(self._cache)
