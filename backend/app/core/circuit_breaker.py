"""LLM circuit breaker — three-state machine protecting the pipeline.

PlotPilot-inspired: after `failure_threshold` consecutive failures the breaker
opens (sleeps `reset_timeout`), moves to half-open (lets ONE call through as a
probe), and closes on success — preventing an overloaded/inaccessible endpoint
from turning a multi-hour pipeline into a line-by-line crash.
"""

from __future__ import annotations

import asyncio
import time
from enum import Enum


class BreakerState(str, Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class CircuitBreaker:
    """A single-endpoint breaker. Thread-safe as long as the caller serialises.

    Defaults are tuned for an LLM endpoint that sees transient rate-limit /
    gateway-timeout bursts: 5 consecutive failures open it, 120s reset timeout,
    one half-open probe.
    """

    def __init__(
        self,
        failure_threshold: int = 5,
        reset_timeout: float = 120.0,
    ) -> None:
        self._threshold = failure_threshold
        self._reset = reset_timeout
        self._state = BreakerState.CLOSED
        self._failures = 0
        self._opened_at = 0.0

    @property
    def state(self) -> BreakerState:
        return self._state

    @property
    def is_open(self) -> bool:
        self._maybe_transition()
        return self._state == BreakerState.OPEN

    def record_success(self) -> None:
        self._failures = 0
        self._state = BreakerState.CLOSED

    def record_failure(self) -> None:
        self._failures += 1
        if self._state == BreakerState.HALF_OPEN:
            return
        if self._failures >= self._threshold:
            self._state = BreakerState.OPEN
            self._opened_at = time.monotonic()

    async def wait_if_open(self) -> None:
        """Block until the breaker is no longer OPEN. Idempotent."""
        self._maybe_transition()
        while self._state == BreakerState.OPEN:
            await asyncio.sleep(min(5.0, self._reset / 10))

    def _maybe_transition(self) -> None:
        if self._state == BreakerState.OPEN:
            elapsed = time.monotonic() - self._opened_at
            if elapsed >= self._reset:
                self._state = BreakerState.HALF_OPEN
