"""Bounds concurrent in-flight calls to vLLM - the "deliberate load
shedding" the plan calls for (docs/adr/0024).

A plain counter, not `asyncio.Semaphore`: this process is single-threaded
cooperative asyncio, so a check-then-increment with no `await` between
the two statements is already atomic - nothing here needs a lock, and
`try_acquire` returning `bool` (rather than awaiting) is exactly what
lets chat.py shed load immediately instead of queueing behind it.
"""

from __future__ import annotations


class InFlightLimiter:
    def __init__(self, limit: int) -> None:
        self._limit = limit
        self._count = 0

    def try_acquire(self) -> bool:
        if self._count >= self._limit:
            return False
        self._count += 1
        return True

    def release(self) -> None:
        self._count -= 1

    @property
    def in_flight(self) -> int:
        return self._count
