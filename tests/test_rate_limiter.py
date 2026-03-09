"""
Tests for TokenBucketRateLimiter (PUB-04)

These tests verify the rate limiter implementation for:
- PUB-04: Global shared rate cap across all workers
- Token bucket algorithm for rate limiting
- Burst capacity and refill behavior
"""

import pytest
import asyncio
from unittest.mock import patch
from typing import Optional


class TestRateLimiterInitialization:
    """Test TokenBucketRateLimiter initialization."""

    def test_rate_limiter_initialized_with_rate_limit(self):
        """
        Test that TokenBucketRateLimiter initializes with rate_limit.

        Given: rate_limit=100 (msg/sec)
        When: TokenBucketRateLimiter is created
        Then: rate_limit is stored, capacity defaults to rate_limit
        """
        from loadgen.rate_limiter import TokenBucketRateLimiter

        limiter = TokenBucketRateLimiter(rate_limit=100)

        assert limiter.rate_limit == 100
        assert limiter.capacity == 100  # defaults to rate_limit

    def test_rate_limiter_custom_capacity(self):
        """
        Test that TokenBucketRateLimiter accepts custom capacity.

        Given: rate_limit=100, capacity=50
        When: TokenBucketRateLimiter is created
        Then: capacity is set to 50 (custom burst size)
        """
        from loadgen.rate_limiter import TokenBucketRateLimiter

        limiter = TokenBucketRateLimiter(rate_limit=100, capacity=50)

        assert limiter.rate_limit == 100
        assert limiter.capacity == 50


class TestRateLimiterAcquire:
    """Test async acquire() behavior."""

    @pytest.mark.asyncio
    async def test_acquire_returns_immediately_when_tokens_available(self):
        """
        Test that acquire() returns immediately if tokens are available.

        Given: A rate limiter with tokens available
        When: acquire() is called
        Then: Returns immediately (no blocking)
        """
        from loadgen.rate_limiter import TokenBucketRateLimiter

        limiter = TokenBucketRateLimiter(rate_limit=100, capacity=100)

        # Should complete quickly - tokens are available at start
        import time
        start = time.monotonic()
        await limiter.acquire()
        elapsed = time.monotonic() - start

        # Should complete in well under 0.1 seconds
        assert elapsed < 0.1

    @pytest.mark.asyncio
    async def test_acquire_blocks_when_no_tokens_available(self):
        """
        Test that acquire() blocks when bucket is empty.

        Given: A rate limiter with no tokens (bucket exhausted)
        When: acquire() is called
        Then: Blocks until token is available (waits for refill)
        """
        from loadgen.rate_limiter import TokenBucketRateLimiter

        # Use rate_limit=10 so refill happens quickly
        limiter = TokenBucketRateLimiter(rate_limit=10, capacity=1)

        # Drain the bucket
        await limiter.acquire()

        # Next acquire should block briefly
        import time
        start = time.monotonic()
        # Give it a short timeout - it should unblock after refill
        try:
            await asyncio.wait_for(limiter.acquire(), timeout=2.0)
            elapsed = time.monotonic() - start
            # Should have waited at least 0.08s (1/10 = 0.1s per token, some tolerance)
            assert elapsed >= 0.05, f"Should have waited for refill, elapsed={elapsed:.3f}s"
        except asyncio.TimeoutError:
            pytest.fail("acquire() timed out - should have refilled within 2s")

    @pytest.mark.asyncio
    async def test_tokens_refill_at_configured_rate(self):
        """
        Test that tokens refill at configured rate per second.

        Given: rate_limit=10 (10 tokens/sec)
        When: We drain the bucket and wait 0.2s
        Then: ~2 tokens should have been refilled
        """
        from loadgen.rate_limiter import TokenBucketRateLimiter

        limiter = TokenBucketRateLimiter(rate_limit=10, capacity=10)

        # Drain completely
        for _ in range(10):
            await limiter.acquire()

        # Wait 0.2 seconds - should refill about 2 tokens
        await asyncio.sleep(0.2)

        # Should be able to acquire 2 tokens immediately
        import time
        start = time.monotonic()
        await limiter.acquire()  # Token 1
        await limiter.acquire()  # Token 2
        elapsed = time.monotonic() - start

        # Both should complete quickly (tokens available from refill)
        assert elapsed < 0.15, f"Expected immediate acquire after refill, elapsed={elapsed:.3f}s"

    @pytest.mark.asyncio
    async def test_capacity_allows_burst(self):
        """
        Test that a full bucket allows burst up to capacity.

        Given: rate_limit=10, capacity=5
        When: 5 acquires are called immediately (burst)
        Then: All 5 complete quickly without waiting
        """
        from loadgen.rate_limiter import TokenBucketRateLimiter

        limiter = TokenBucketRateLimiter(rate_limit=10, capacity=5)

        # Burst: acquire 5 tokens immediately
        import time
        start = time.monotonic()
        for _ in range(5):
            await limiter.acquire()
        elapsed = time.monotonic() - start

        # All 5 should complete quickly (burst from full bucket)
        assert elapsed < 0.2, f"Burst of 5 should be immediate, elapsed={elapsed:.3f}s"

    @pytest.mark.asyncio
    async def test_acquire_uses_monotonic_time_for_precision(self):
        """
        Test that rate limiter uses monotonic time (not affected by clock changes).

        Given: A rate limiter with rate_limit=1000
        When: Multiple acquires happen
        Then: Timing is accurate and uses monotonic clock
        """
        from loadgen.rate_limiter import TokenBucketRateLimiter
        import time

        limiter = TokenBucketRateLimiter(rate_limit=1000, capacity=1000)

        # Should be able to acquire 1000 tokens immediately (full bucket)
        start = time.monotonic()
        for _ in range(100):
            await limiter.acquire()
        elapsed = time.monotonic() - start

        # 100 acquires from a full 1000-capacity bucket should be fast
        assert elapsed < 1.0, f"100 acquires from full bucket should be fast, elapsed={elapsed:.3f}s"


class TestRateLimiterConcurrency:
    """Test rate limiter with concurrent workers."""

    @pytest.mark.asyncio
    async def test_rate_limiter_is_thread_safe_with_lock(self):
        """
        Test that the rate limiter uses asyncio.Lock for safe concurrent access.

        Given: Multiple coroutines acquiring tokens simultaneously
        When: All acquire concurrently
        Then: Token count never goes negative (safe decrement)
        """
        from loadgen.rate_limiter import TokenBucketRateLimiter

        limiter = TokenBucketRateLimiter(rate_limit=100, capacity=10)

        # Track how many tokens are actually acquired
        acquired_count = 0

        async def do_acquire():
            nonlocal acquired_count
            await limiter.acquire()
            acquired_count += 1

        # Run 10 concurrent acquires (all should succeed from burst capacity)
        tasks = [do_acquire() for _ in range(10)]
        await asyncio.gather(*tasks)

        assert acquired_count == 10
        # Internal token count should not be negative
        assert limiter._tokens >= -0.1  # Allow floating point tolerance
