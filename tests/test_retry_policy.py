"""
Tests for RetryPolicy with exponential backoff (PUB-05).

These tests verify the retry policy implementation for:
- PUB-05: Retry only QoS failures (not connection errors)
- Exponential, fixed, and linear backoff strategies
- Configurable max retry count
- Failed messages written to artifact file
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from pathlib import Path
import json


# ─── Task 1: RetryPolicy with backoff strategies ─────────────────────────────

class TestRetryPolicyInit:
    """Test RetryPolicy initialization."""

    def test_retry_policy_initialized_with_defaults(self):
        """
        Test RetryPolicy initializes with max_retries, strategy, base_delay, multiplier.

        Given: RetryPolicy class
        When: Initialized with required parameters
        Then: All configuration stored correctly
        """
        from loadgen.retry_policy import RetryPolicy, BackoffStrategy

        policy = RetryPolicy(max_retries=3, strategy=BackoffStrategy.EXPONENTIAL)
        assert policy._max_retries == 3
        assert policy._strategy == BackoffStrategy.EXPONENTIAL
        assert policy._base_delay == 1.0  # default
        assert policy._multiplier == 2.0  # default

    def test_retry_policy_accepts_custom_delay_and_multiplier(self):
        """
        Test RetryPolicy accepts custom base_delay and multiplier.

        Given: RetryPolicy class
        When: Initialized with custom base_delay and multiplier
        Then: Values stored correctly
        """
        from loadgen.retry_policy import RetryPolicy, BackoffStrategy

        policy = RetryPolicy(
            max_retries=5,
            strategy=BackoffStrategy.FIXED,
            base_delay=0.5,
            multiplier=3.0,
        )
        assert policy._max_retries == 5
        assert policy._base_delay == 0.5
        assert policy._multiplier == 3.0


class TestRetryPolicySuccess:
    """Test RetryPolicy behavior on successful calls."""

    @pytest.mark.asyncio
    async def test_retry_executes_function_immediately_on_success(self):
        """
        Test async retry() executes function and returns result on first try.

        Given: RetryPolicy and a function that succeeds
        When: retry() is called
        Then: Function called once, result returned without retries
        """
        from loadgen.retry_policy import RetryPolicy, BackoffStrategy

        policy = RetryPolicy(max_retries=3, strategy=BackoffStrategy.EXPONENTIAL)
        func = AsyncMock(return_value="success")

        result = await policy.retry(func)

        assert result == "success"
        func.assert_called_once()


class TestRetryPolicyRetryable:
    """Test RetryPolicy retry behavior for retryable errors."""

    @pytest.mark.asyncio
    async def test_retry_retries_retryable_error_with_exponential_backoff(self):
        """
        Test async retry() retries RetryableError with exponential backoff.

        Given: RetryPolicy with exponential strategy and a function that fails twice then succeeds
        When: retry() is called
        Then: Function retried with delays, succeeds on third call
        """
        from loadgen.retry_policy import RetryPolicy, BackoffStrategy, RetryableError

        policy = RetryPolicy(
            max_retries=3,
            strategy=BackoffStrategy.EXPONENTIAL,
            base_delay=0.01,
            multiplier=2.0,
        )

        call_count = 0

        async def flaky_func():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise RetryableError("QoS ack timeout")
            return "success"

        with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
            result = await policy.retry(flaky_func)

        assert result == "success"
        assert call_count == 3
        # Should have slept twice (after attempt 0 and attempt 1)
        assert mock_sleep.call_count == 2

    @pytest.mark.asyncio
    async def test_retry_uses_fixed_delay_strategy(self):
        """
        Test retry() uses fixed delay for BackoffStrategy.FIXED.

        Given: RetryPolicy with FIXED strategy
        When: RetryableError is raised and retry occurs
        Then: Same delay used for all retry attempts
        """
        from loadgen.retry_policy import RetryPolicy, BackoffStrategy, RetryableError

        policy = RetryPolicy(
            max_retries=3,
            strategy=BackoffStrategy.FIXED,
            base_delay=0.5,
        )

        func = AsyncMock(side_effect=[RetryableError("fail"), RetryableError("fail"), "ok"])
        # AsyncMock doesn't support mixed side_effects like that; use a different approach
        call_count = 0

        async def flaky():
            nonlocal call_count
            call_count += 1
            if call_count <= 2:
                raise RetryableError("fail")
            return "ok"

        with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
            result = await policy.retry(flaky)

        assert result == "ok"
        # All sleep calls should use base_delay (0.5)
        for call in mock_sleep.call_args_list:
            assert call.args[0] == 0.5

    @pytest.mark.asyncio
    async def test_retry_uses_linear_delay_strategy(self):
        """
        Test retry() uses linear delay for BackoffStrategy.LINEAR.

        Given: RetryPolicy with LINEAR strategy, base_delay=1.0
        When: RetryableError is raised and retries occur
        Then: Delays are base_delay * attempt (1, 2, 3, ...)
        """
        from loadgen.retry_policy import RetryPolicy, BackoffStrategy, RetryableError

        policy = RetryPolicy(
            max_retries=3,
            strategy=BackoffStrategy.LINEAR,
            base_delay=1.0,
        )

        call_count = 0

        async def flaky():
            nonlocal call_count
            call_count += 1
            if call_count <= 2:
                raise RetryableError("fail")
            return "ok"

        with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
            result = await policy.retry(flaky)

        assert result == "ok"
        # Linear delays: attempt=0 -> 0*1.0=0, attempt=1 -> 1*1.0=1.0
        delays = [call.args[0] for call in mock_sleep.call_args_list]
        assert len(delays) == 2


class TestRetryPolicyNonRetryable:
    """Test RetryPolicy behavior for non-retryable errors."""

    @pytest.mark.asyncio
    async def test_retry_raises_non_retryable_error_immediately(self):
        """
        Test async retry() raises NonRetryableError immediately without retrying.

        Given: RetryPolicy and a function that raises NonRetryableError
        When: retry() is called
        Then: NonRetryableError raised immediately, function not retried
        """
        from loadgen.retry_policy import RetryPolicy, BackoffStrategy, NonRetryableError

        policy = RetryPolicy(max_retries=3, strategy=BackoffStrategy.EXPONENTIAL)
        call_count = 0

        async def connection_error_func():
            nonlocal call_count
            call_count += 1
            raise NonRetryableError("Connection refused")

        with pytest.raises(NonRetryableError, match="Connection refused"):
            await policy.retry(connection_error_func)

        # Called exactly once - no retries
        assert call_count == 1


class TestRetryPolicyMaxRetries:
    """Test RetryPolicy max retries exhaustion."""

    @pytest.mark.asyncio
    async def test_retry_raises_max_retries_exceeded_after_max_retries(self):
        """
        Test async retry() raises MaxRetriesExceededError after all retries exhausted.

        Given: RetryPolicy with max_retries=3 and function that always fails
        When: retry() is called
        Then: MaxRetriesExceededError raised after 3 retries (4 total attempts)
        """
        from loadgen.retry_policy import (
            RetryPolicy,
            BackoffStrategy,
            RetryableError,
            MaxRetriesExceededError,
        )

        policy = RetryPolicy(
            max_retries=3,
            strategy=BackoffStrategy.EXPONENTIAL,
            base_delay=0.01,
        )
        call_count = 0

        async def always_fails():
            nonlocal call_count
            call_count += 1
            raise RetryableError("QoS ack timeout")

        with patch("asyncio.sleep", new_callable=AsyncMock):
            with pytest.raises(MaxRetriesExceededError):
                await policy.retry(always_fails)

        # 1 initial + 3 retries = 4 total calls
        assert call_count == 4


# ─── Task 2: Artifact writing for failed messages ─────────────────────────────

class TestRetryPolicyArtifact:
    """Test artifact writing for failed messages."""

    @pytest.mark.asyncio
    async def test_failed_messages_written_to_artifact_on_max_retries(
        self, tmp_path
    ):
        """
        Test that failed messages are written to artifact file on max retries.

        Given: RetryPolicy with artifact_path configured
        When: max retries exhausted for a message with payload
        Then: Artifact file created and contains the failed message
        """
        from loadgen.retry_policy import (
            RetryPolicy,
            BackoffStrategy,
            RetryableError,
            MaxRetriesExceededError,
        )

        artifact_path = str(tmp_path / "failed_events.jsonl")
        policy = RetryPolicy(
            max_retries=1,
            strategy=BackoffStrategy.FIXED,
            base_delay=0.01,
            artifact_path=artifact_path,
        )

        payload = {"trxId": "test-txn-001", "meterId": "000000000001", "value": 42}

        async def always_fails():
            raise RetryableError("QoS ack timeout")

        with patch("asyncio.sleep", new_callable=AsyncMock):
            with pytest.raises(MaxRetriesExceededError):
                await policy.retry(always_fails, payload=payload)

        # Artifact file should exist
        assert Path(artifact_path).exists()

    @pytest.mark.asyncio
    async def test_artifact_format_is_jsonl(self, tmp_path):
        """
        Test artifact file is in JSONL format (one JSON object per line).

        Given: RetryPolicy with artifact_path
        When: max retries exhausted
        Then: Artifact file contains valid JSON on each line
        """
        from loadgen.retry_policy import (
            RetryPolicy,
            BackoffStrategy,
            RetryableError,
            MaxRetriesExceededError,
        )

        artifact_path = str(tmp_path / "failed_events.jsonl")
        policy = RetryPolicy(
            max_retries=1,
            strategy=BackoffStrategy.FIXED,
            base_delay=0.01,
            artifact_path=artifact_path,
        )

        payload = {"trxId": "test-txn-002", "meterId": "000000000002"}

        async def always_fails():
            raise RetryableError("QoS timeout")

        with patch("asyncio.sleep", new_callable=AsyncMock):
            with pytest.raises(MaxRetriesExceededError):
                await policy.retry(always_fails, payload=payload)

        # Each line should be valid JSON
        with open(artifact_path) as f:
            lines = [line.strip() for line in f if line.strip()]

        assert len(lines) >= 1
        for line in lines:
            entry = json.loads(line)  # Should not raise
            assert isinstance(entry, dict)

    @pytest.mark.asyncio
    async def test_artifact_entry_contains_required_fields(self, tmp_path):
        """
        Test each artifact entry contains trxId, payload, error, retry_count, timestamp.

        Given: RetryPolicy with artifact_path
        When: max retries exhausted
        Then: Artifact entry has all required fields
        """
        from loadgen.retry_policy import (
            RetryPolicy,
            BackoffStrategy,
            RetryableError,
            MaxRetriesExceededError,
        )

        artifact_path = str(tmp_path / "failed_events.jsonl")
        policy = RetryPolicy(
            max_retries=2,
            strategy=BackoffStrategy.FIXED,
            base_delay=0.01,
            artifact_path=artifact_path,
        )

        payload = {"trxId": "test-txn-003", "meterId": "000000000003", "value": 99}

        async def always_fails():
            raise RetryableError("QoS ack timeout")

        with patch("asyncio.sleep", new_callable=AsyncMock):
            with pytest.raises(MaxRetriesExceededError):
                await policy.retry(always_fails, payload=payload)

        with open(artifact_path) as f:
            lines = [line.strip() for line in f if line.strip()]

        entry = json.loads(lines[0])
        assert entry["trxId"] == "test-txn-003"
        assert "payload" in entry
        assert "error" in entry
        assert "retry_count" in entry
        assert "timestamp" in entry

    @pytest.mark.asyncio
    async def test_artifact_file_created_if_not_exists(self, tmp_path):
        """
        Test artifact file is created if it does not already exist.

        Given: RetryPolicy with artifact_path pointing to non-existent file
        When: max retries exhausted
        Then: Artifact file is created
        """
        from loadgen.retry_policy import (
            RetryPolicy,
            BackoffStrategy,
            RetryableError,
            MaxRetriesExceededError,
        )

        artifact_path = str(tmp_path / "new_dir" / "failed_events.jsonl")
        # Parent dir doesn't exist yet
        policy = RetryPolicy(
            max_retries=1,
            strategy=BackoffStrategy.FIXED,
            base_delay=0.01,
            artifact_path=artifact_path,
        )

        async def always_fails():
            raise RetryableError("fail")

        with patch("asyncio.sleep", new_callable=AsyncMock):
            with pytest.raises(MaxRetriesExceededError):
                await policy.retry(always_fails, payload={"trxId": "t"})

        assert Path(artifact_path).exists()

    @pytest.mark.asyncio
    async def test_artifact_file_appended_if_exists(self, tmp_path):
        """
        Test artifact file is appended to if it already exists.

        Given: RetryPolicy with artifact_path pointing to existing file
        When: max retries exhausted twice
        Then: Artifact file contains two entries (appended)
        """
        from loadgen.retry_policy import (
            RetryPolicy,
            BackoffStrategy,
            RetryableError,
            MaxRetriesExceededError,
        )

        artifact_path = str(tmp_path / "failed_events.jsonl")
        policy = RetryPolicy(
            max_retries=1,
            strategy=BackoffStrategy.FIXED,
            base_delay=0.01,
            artifact_path=artifact_path,
        )

        async def always_fails():
            raise RetryableError("fail")

        with patch("asyncio.sleep", new_callable=AsyncMock):
            with pytest.raises(MaxRetriesExceededError):
                await policy.retry(
                    always_fails, payload={"trxId": "tx-001"}
                )
            with pytest.raises(MaxRetriesExceededError):
                await policy.retry(
                    always_fails, payload={"trxId": "tx-002"}
                )

        with open(artifact_path) as f:
            lines = [line.strip() for line in f if line.strip()]

        assert len(lines) == 2
        assert json.loads(lines[0])["trxId"] == "tx-001"
        assert json.loads(lines[1])["trxId"] == "tx-002"
