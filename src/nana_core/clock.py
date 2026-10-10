"""UTC occurrence times and injectable clocks; invalid input stays unknown."""
from datetime import datetime, timezone
import time


def parse_utc(value: str | None) -> int | None:
    if value is None:
        return None
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            return None
        delta = dt.astimezone(timezone.utc) - datetime(1970, 1, 1, tzinfo=timezone.utc)
        return (delta.days * 86400 + delta.seconds) * 1_000_000 + delta.microseconds
    except (ValueError, OverflowError):
        return None


class Clock:
    def utc_now_us(self) -> int:
        return time.time_ns() // 1000

    def monotonic_ns(self) -> int:
        return time.monotonic_ns()


class ManualClock(Clock):
    def __init__(self, now_us: int = 1_791_590_400_000_000):
        self.now_us = now_us

    def utc_now_us(self) -> int:
        return self.now_us

    def advance(self, microseconds: int) -> None:
        self.now_us += microseconds
