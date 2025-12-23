import time


class Cache:
    def __init__(self, ttl: int = 300):
        """Кэш с временем жизни ttl (секунды)"""
        self.ttl = ttl
        self._data: dict[str, tuple[float, object]] = {}

    def get(self, key: str):
        if key not in self._data:
            return None
        expires_at, value = self._data[key]
        if time.time() > expires_at:
            del self._data[key]
            return None
        return value

    def set(self, key: str, value):
        self._data[key] = (time.time() + self.ttl, value)
