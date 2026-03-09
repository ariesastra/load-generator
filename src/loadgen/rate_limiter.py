"""
Token Bucket Rate Limiter for global publish throttling.

This module provides the TokenBucketRateLimiter class that enforces a
messages-per-second rate cap across all workers. It uses the token bucket
algorithm which allows controlled bursts within capacity while maintaining
the configured long-term rate.

Key features:
- Token bucket algorithm with configurable capacity (burst size)
- async acquire() that blocks when rate exceeded (messages never dropped)
- Global shared limiter across all workers for total rate enforcement
- Uses time.monotonic() for precision (immune to system clock adjustments)
- asyncio.Lock for safe concurrent token access from multiple workers
- Second-level precision for rate tracking
"""

import asyncio
import time
from typing import Optional


class TokenBucketRateLimiter:
    """
    Token bucket rate limiter for MQTT publish throttling.

    The token bucket algorithm works as follows:
    - The bucket holds tokens up to a configurable capacity
    - Tokens are added at a constant rate (rate_limit tokens/second)
    - Each publish call consumes 1 token via acquire()
    - If the bucket is empty, acquire() blocks until a token is available
    - A full bucket allows a burst of up to capacity tokens immediately

    Usage:
        # Create a global limiter shared across all workers
        limiter = TokenBucketRateLimiter(rate_limit=1000)

        # In each worker before publishing:
        await limiter.acquire()
        await worker.publish(topic, payload)

    Args:
        rate_limit: Maximum messages per second (refill rate)
        capacity: Maximum token capacity / burst size.
                  Defaults to rate_limit (1-second burst capacity).
    """

    def __init__(self, rate_limit: int, capacity: Optional[int] = None):
        """
        Initialize the token bucket rate limiter.

        Args:
            rate_limit: Messages per second allowed (refill rate)
            capacity: Maximum tokens (burst size). Defaults to rate_limit.
        """
        self._rate_limit = rate_limit
        self._capacity = capacity if capacity is not None else rate_limit

        # Start with a full bucket (allows initial burst)
        self._tokens: float = float(self._capacity)

        # Track last refill time using monotonic clock
        self._last_refill_time: float = time.monotonic()

        # asyncio.Lock for safe concurrent token manipulation
        self._lock: asyncio.Lock = asyncio.Lock()

    @property
    def rate_limit(self) -> int:
        """Return the configured rate limit (msg/sec)."""
        return self._rate_limit

    @property
    def capacity(self) -> int:
        """Return the configured bucket capacity (burst size)."""
        return self._capacity

    @property
    def _tokens_count(self) -> float:
        """Return current token count (for inspection)."""
        return self._tokens

    async def _refill_tokens(self) -> None:
        """
        Refill tokens based on elapsed time since last refill.

        Calculates how many tokens to add based on:
            new_tokens = elapsed_seconds * rate_limit

        Tokens are capped at capacity. Updates _last_refill_time.
        Must be called while holding _lock.
        """
        now = time.monotonic()
        elapsed = now - self._last_refill_time

        if elapsed > 0:
            # Add tokens proportional to elapsed time and rate
            new_tokens = elapsed * self._rate_limit
            self._tokens = min(self._capacity, self._tokens + new_tokens)
            self._last_refill_time = now

    async def acquire(self) -> None:
        """
        Acquire one token, blocking until available.

        This method:
        1. Refills tokens based on elapsed time
        2. If a token is available, consumes it and returns immediately
        3. If no token available, calculates wait time and sleeps
        4. Loops until a token is acquired

        The asyncio.Lock ensures only one coroutine modifies token state
        at a time, making this safe for concurrent use across workers.

        Returns:
            None (blocks until token acquired)
        """
        while True:
            async with self._lock:
                # Refill any pending tokens based on elapsed time
                await self._refill_tokens()

                if self._tokens >= 1.0:
                    # Token available: consume and return
                    self._tokens -= 1.0
                    return
                else:
                    # Calculate how long to wait for next token
                    # tokens_needed = 1 - _tokens
                    # wait_time = tokens_needed / rate_limit
                    tokens_needed = 1.0 - self._tokens
                    wait_time = tokens_needed / self._rate_limit

            # Sleep outside the lock to allow other coroutines to run
            # Add a small buffer to ensure the refill will have happened
            await asyncio.sleep(wait_time)
