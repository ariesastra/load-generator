"""
Retry policy with exponential backoff for QoS-level publish failures.

This module provides the RetryPolicy class for handling transient publish
failures with configurable backoff strategies. Only QoS acknowledgment
failures are retryable; connection and broker errors fail immediately.

Key features:
- Configurable max retries (from YAML scenario config)
- Configurable backoff strategies: exponential, fixed, linear
- Distinct exception hierarchy: RetryableError vs NonRetryableError
- Artifact writing to failed_events.jsonl on retry exhaustion
- Run continues after retry exhaustion (non-fatal per message)

Exception hierarchy:
    RetryableError       - transient QoS failures (PUBACK timeout, QoS 1 ack)
    NonRetryableError    - permanent failures (connection errors, broker errors)
    MaxRetriesExceededError - raised when retry budget is fully consumed
"""

import asyncio
import json
import os
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Dict, Optional


# ─── Exception Classes ────────────────────────────────────────────────────────


class RetryableError(Exception):
    """
    Raised for transient QoS-level publish failures that should be retried.

    Examples:
    - PUBACK timeout (QoS 1 acknowledgment not received)
    - PUBREC/PUBCOMP timeout (QoS 2 handshake incomplete)

    These errors are transient and may succeed on retry.
    """

    pass


class NonRetryableError(Exception):
    """
    Raised for permanent failures that should NOT be retried.

    Examples:
    - Connection errors (refused, timeout during connect)
    - Broker errors (authentication failure, authorization error)
    - Protocol errors

    Retrying these errors is not beneficial; fail fast instead.
    """

    pass


class MaxRetriesExceededError(Exception):
    """
    Raised when all retry attempts are exhausted for a retryable error.

    The original error that triggered retries is available via __cause__.
    Failed message details are written to artifact file before this is raised.
    """

    pass


# ─── Backoff Strategy ─────────────────────────────────────────────────────────


class BackoffStrategy(Enum):
    """
    Enum defining available backoff delay calculation strategies.

    EXPONENTIAL: delay = base_delay * (multiplier ** attempt)
        Delays grow exponentially. Best for high-contention scenarios.

    FIXED: delay = base_delay
        Same delay on each retry. Simple and predictable.

    LINEAR: delay = base_delay * attempt
        Delays grow linearly. Moderate backoff pressure.

    Note: attempt starts at 0 for the first retry (after initial failure).
    """

    EXPONENTIAL = "exponential"
    FIXED = "fixed"
    LINEAR = "linear"


# ─── RetryPolicy ─────────────────────────────────────────────────────────────


class RetryPolicy:
    """
    Wraps publish calls with retry logic and backoff for transient QoS failures.

    Usage:
        policy = RetryPolicy(
            max_retries=3,
            strategy=BackoffStrategy.EXPONENTIAL,
            base_delay=1.0,
            multiplier=2.0,
            artifact_path="artifacts/failed_events.jsonl",
        )

        await policy.retry(publish_func, payload=message_dict)

    The retry() method:
    1. Calls the function immediately
    2. On RetryableError: waits (backoff) and retries up to max_retries times
    3. On NonRetryableError: re-raises immediately (no retry)
    4. On MaxRetriesExceeded: writes to artifact then raises

    Individual message failures do not stop the run — callers receive the
    MaxRetriesExceededError and continue processing other messages.
    """

    def __init__(
        self,
        max_retries: int,
        strategy: BackoffStrategy,
        base_delay: float = 1.0,
        multiplier: float = 2.0,
        artifact_path: Optional[str] = None,
    ):
        """
        Initialize RetryPolicy.

        Args:
            max_retries: Maximum number of retry attempts after initial failure.
                         With max_retries=3, the function may be called up to 4
                         times total (1 initial + 3 retries).
            strategy: Backoff delay strategy (EXPONENTIAL, FIXED, or LINEAR).
            base_delay: Base delay in seconds for backoff calculation.
                        Default: 1.0 second.
            multiplier: Multiplier for EXPONENTIAL strategy.
                        Ignored for FIXED and LINEAR strategies.
                        Default: 2.0 (doubles delay on each retry).
            artifact_path: Optional path to JSONL artifact file for failed
                           messages. If None, failed messages are not recorded.
        """
        self._max_retries = max_retries
        self._strategy = strategy
        self._base_delay = base_delay
        self._multiplier = multiplier
        self._artifact_path = artifact_path

    def _calculate_delay(self, attempt: int) -> float:
        """
        Calculate backoff delay for the given retry attempt number.

        Args:
            attempt: Zero-based retry attempt index (0 = first retry).

        Returns:
            Delay in seconds before the next retry attempt.
        """
        if self._strategy == BackoffStrategy.EXPONENTIAL:
            return self._base_delay * (self._multiplier ** attempt)
        elif self._strategy == BackoffStrategy.FIXED:
            return self._base_delay
        elif self._strategy == BackoffStrategy.LINEAR:
            return self._base_delay * attempt
        else:
            # Defensive: fall back to fixed delay for unknown strategies
            return self._base_delay

    async def _write_to_artifact(
        self,
        payload: Dict[str, Any],
        error: Exception,
        retry_count: int,
    ) -> None:
        """
        Write a failed message to the artifact file in JSONL format.

        Creates parent directories if needed. Opens file in append mode so
        multiple failures accumulate in the same file across the run.

        Args:
            payload: The message payload dictionary that failed to publish.
            error: The exception that caused final failure.
            retry_count: Number of retries that were attempted.
        """
        entry = {
            "trxId": payload.get("trxId", "unknown"),
            "payload": payload,
            "error": str(error),
            "retry_count": retry_count,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        artifact_path = self._artifact_path
        # Ensure parent directory exists
        parent_dir = os.path.dirname(artifact_path)
        if parent_dir:
            os.makedirs(parent_dir, exist_ok=True)

        # Append JSONL entry (sync I/O — aiofiles optional, sync is fine for
        # artifact writes which are on the error path)
        with open(artifact_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, default=str) + "\n")

    async def retry(
        self,
        func: Callable,
        *args: Any,
        payload: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
    ) -> Any:
        """
        Execute func with retry logic for RetryableError failures.

        Args:
            func: Async callable to execute. Called as await func(*args, **kwargs).
            *args: Positional arguments forwarded to func.
            payload: Optional message payload dict for artifact writing on failure.
                     If provided and retries are exhausted, written to artifact.
            **kwargs: Keyword arguments forwarded to func.

        Returns:
            Result from func on success.

        Raises:
            NonRetryableError: If func raises NonRetryableError (no retries).
            MaxRetriesExceededError: If all max_retries attempts fail.
            Any other exception from func is re-raised immediately.
        """
        last_error: Optional[Exception] = None

        # Initial attempt
        try:
            return await func(*args, **kwargs)
        except NonRetryableError:
            raise
        except RetryableError as e:
            last_error = e
        # Other exceptions propagate immediately

        # Retry loop
        for attempt in range(self._max_retries):
            delay = self._calculate_delay(attempt)
            await asyncio.sleep(delay)

            try:
                return await func(*args, **kwargs)
            except NonRetryableError:
                raise
            except RetryableError as e:
                last_error = e
                continue
            # Other exceptions propagate immediately

        # All retries exhausted
        if self._artifact_path is not None and payload is not None:
            await self._write_to_artifact(
                payload=payload,
                error=last_error,
                retry_count=self._max_retries,
            )

        raise MaxRetriesExceededError(
            f"Exceeded {self._max_retries} retries: {last_error}"
        ) from last_error
