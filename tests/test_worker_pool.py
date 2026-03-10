"""
Tests for WorkerPool concurrent MQTT publishing.

This module tests the WorkerPool class that manages multiple MQTTClient
workers for concurrent async publishing with pre-connect and fail-fast behavior.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import asyncio
from typing import Union


# Mock MQTTClient before it exists
class MockMQTTClient:
    """Mock MQTTClient for testing WorkerPool without actual broker."""

    def __init__(self, host: str, port: int, qos: int, **kwargs):
        self.host = host
        self.port = port
        self.qos = qos
        self.kwargs = kwargs
        self._connected = False

    async def connect(self) -> None:
        """Mock connect - mark as connected."""
        self._connected = True

    async def disconnect(self) -> None:
        """Mock disconnect - mark as disconnected."""
        self._connected = False

    async def publish(self, topic: str, payload: Union[bytes, str]) -> None:
        """Mock publish - check connection state."""
        if not self._connected:
            raise Exception("Not connected")


@pytest.fixture
def broker_config():
    """
    Return broker configuration for WorkerPool.

    Provides standard MQTT broker connection parameters.
    """
    return {
        "host": "localhost",
        "port": 1883,
        "qos": 1,
        "tls_enabled": False,
        "username": None,
        "password": None,
    }


@pytest.fixture
def mock_mqtt_client_class():
    """
    Return a mock MQTTClient class factory.

    Allows creating mock MQTTClient instances with controllable
    connect/disconnect behavior for testing.
    """

    def _create_client(host, port, qos, **kwargs):
        return MockMQTTClient(host, port, qos, **kwargs)

    return _create_client


class TestWorkerPoolCreation:
    """Test WorkerPool initialization and worker creation."""

    @pytest.mark.asyncio
    async def test_creates_n_workers_on_initialization(
        self, broker_config, mock_mqtt_client_class
    ):
        """
        Test that WorkerPool creates N MQTTClient workers on initialization.

        Given: A broker_config and worker_count
        When: WorkerPool is initialized
        Then: Exactly worker_count MQTTClient instances are created
        """
        # This will fail until WorkerPool is implemented
        from loadgen.worker_pool import WorkerPool, MQTTClient

        worker_count = 5
        pool = WorkerPool(
            worker_count=worker_count, broker_config=broker_config
        )

        assert len(pool._workers) == worker_count
        for worker in pool._workers:
            assert isinstance(worker, MQTTClient)
            assert worker.host == broker_config["host"]
            assert worker.port == broker_config["port"]
            assert worker.qos == broker_config["qos"]

    @pytest.mark.asyncio
    async def test_workers_use_same_connection_config(
        self, broker_config, mock_mqtt_client_class
    ):
        """
        Test that all workers use the same connection configuration.

        Given: A broker_config with specific parameters
        When: WorkerPool is initialized
        Then: All workers have identical connection parameters
        """
        from loadgen.worker_pool import WorkerPool

        worker_count = 3
        pool = WorkerPool(
            worker_count=worker_count, broker_config=broker_config
        )

        # All workers should have the same config
        first_worker = pool._workers[0]
        for worker in pool._workers[1:]:
            assert worker.host == first_worker.host
            assert worker.port == first_worker.port
            assert worker.qos == first_worker.qos


class TestWorkerPoolInitialization:
    """Test async initialize() pre-connect behavior."""

    @pytest.mark.asyncio
    async def test_initialize_pre_connects_all_workers(
        self, broker_config, mock_mqtt_client_class
    ):
        """
        Test that initialize() calls connect() on all workers.

        Given: A WorkerPool with N workers
        When: async initialize() is called
        Then: All N workers have connect() called and are connected
        """
        from loadgen.worker_pool import WorkerPool

        worker_count = 3
        pool = WorkerPool(
            worker_count=worker_count, broker_config=broker_config
        )

        await pool.initialize()

        # All workers should be connected
        for worker in pool._workers:
            assert worker._connected is True

    @pytest.mark.asyncio
    async def test_initialize_raises_if_any_worker_fails(
        self, broker_config, mock_mqtt_client_class
    ):
        """
        Test that initialize() raises WorkerConnectionError if any worker fails.

        Given: A WorkerPool where one worker fails to connect
        When: async initialize() is called
        Then: WorkerConnectionError is raised
        """
        from loadgen.worker_pool import WorkerPool, WorkerConnectionError

        worker_count = 3
        pool = WorkerPool(
            worker_count=worker_count, broker_config=broker_config
        )

        # Make the second worker fail to connect
        original_connect = pool._workers[1].connect
        pool._workers[1].connect = AsyncMock(
            side_effect=Exception("Connection failed")
        )

        with pytest.raises(WorkerConnectionError):
            await pool.initialize()

    @pytest.mark.asyncio
    async def test_initialize_cleansup_on_failure(
        self, broker_config, mock_mqtt_client_class
    ):
        """
        Test that initialize() disconnects connected workers if one fails.

        Given: A WorkerPool where worker 2 fails after worker 1 connects
        When: async initialize() is called
        Then: Worker 1 is disconnected before error is raised
        """
        from loadgen.worker_pool import WorkerPool, WorkerConnectionError

        worker_count = 3
        pool = WorkerPool(
            worker_count=worker_count, broker_config=broker_config
        )

        # Make the second worker fail to connect
        async def failing_connect():
            # First worker connects, then second fails
            if pool._workers[0]._connected:
                raise Exception("Connection failed")

        pool._workers[1].connect = AsyncMock(side_effect=failing_connect)

        with pytest.raises(WorkerConnectionError):
            await pool.initialize()

        # First worker should be disconnected after failure
        assert pool._workers[0]._connected is False

    @pytest.mark.asyncio
    async def test_initialize_idempotent(
        self, broker_config, mock_mqtt_client_class
    ):
        """
        Test that initialize() can only be called once.

        Given: A WorkerPool that is already initialized
        When: async initialize() is called again
        Then: RuntimeError is raised or call is ignored
        """
        from loadgen.worker_pool import WorkerPool

        worker_count = 2
        pool = WorkerPool(
            worker_count=worker_count, broker_config=broker_config
        )

        await pool.initialize()

        # Second initialize should raise or be ignored
        with pytest.raises(RuntimeError):
            await pool.initialize()


class TestWorkerPoolCleanup:
    """Test async cleanup() method."""

    @pytest.mark.asyncio
    async def test_cleanup_disconnects_all_workers(
        self, broker_config, mock_mqtt_client_class
    ):
        """
        Test that cleanup() calls disconnect() on all workers.

        Given: An initialized WorkerPool
        When: async cleanup() is called
        Then: All workers are disconnected
        """
        from loadgen.worker_pool import WorkerPool

        worker_count = 3
        pool = WorkerPool(
            worker_count=worker_count, broker_config=broker_config
        )

        await pool.initialize()
        assert all(w._connected for w in pool._workers)

        await pool.cleanup()

        # All workers should be disconnected
        for worker in pool._workers:
            assert worker._connected is False

    @pytest.mark.asyncio
    async def test_cleanup_allows_reinitialize(
        self, broker_config, mock_mqtt_client_class
    ):
        """
        Test that cleanup allows re-initialization.

        Given: A WorkerPool that was initialized then cleaned up
        When: async initialize() is called again
        Then: Workers connect successfully
        """
        from loadgen.worker_pool import WorkerPool

        worker_count = 2
        pool = WorkerPool(
            worker_count=worker_count, broker_config=broker_config
        )

        await pool.initialize()
        await pool.cleanup()

        # Should be able to initialize again
        await pool.initialize()

        assert all(w._connected for w in pool._workers)


class TestWorkerPoolPublish:
    """Test async publish() method for concurrent dispatch."""

    @pytest.mark.asyncio
    async def test_publish_dispatches_messages_concurrently(
        self, broker_config, mock_mqtt_client_class
    ):
        """
        Test that publish() dispatches messages across workers concurrently.

        Given: An initialized WorkerPool with 3 workers
        When: async publish() is called with 5 messages
        Then: All 5 messages are published across workers
        """
        from loadgen.worker_pool import WorkerPool

        worker_count = 3
        pool = WorkerPool(
            worker_count=worker_count, broker_config=broker_config
        )

        await pool.initialize()

        messages = [
            {"meterId": f"00000000004{i}", "value": i}
            for i in range(5)
        ]
        topic = "test/topic"

        # Track publish calls per worker
        publish_calls = []

        original_publish = pool._workers[0].publish
        for idx, worker in enumerate(pool._workers):
            async def tracking_publish(topic, payload, worker_idx=idx):
                publish_calls.append(worker_idx)
                await original_publish(topic, payload)

            worker.publish = tracking_publish

        await pool.publish(messages, topic)

        assert len(publish_calls) == 5

    @pytest.mark.asyncio
    async def test_publish_distributes_round_robin(
        self, broker_config, mock_mqtt_client_class
    ):
        """
        Test that messages are distributed round-robin across workers.

        Given: A WorkerPool with 3 workers
        When: 6 messages are published
        Then: Each worker gets 2 messages (round-robin: 0,1,2,0,1,2)
        """
        from loadgen.worker_pool import WorkerPool

        worker_count = 3
        pool = WorkerPool(
            worker_count=worker_count, broker_config=broker_config
        )

        await pool.initialize()

        messages = [{"meterId": f"00000000004{i}", "value": i} for i in range(6)]
        topic = "test/topic"

        # Track publish calls per worker
        worker_counts = {0: 0, 1: 0, 2: 0}

        original_publish = pool._workers[0].publish
        for idx, worker in enumerate(pool._workers):
            async def tracking_publish(topic, payload, worker_idx=idx):
                worker_counts[worker_idx] += 1
                await original_publish(topic, payload)

            worker.publish = tracking_publish

        await pool.publish(messages, topic)

        # Each worker should have published 2 messages (round-robin)
        assert worker_counts[0] == 2
        assert worker_counts[1] == 2
        assert worker_counts[2] == 2

    @pytest.mark.asyncio
    async def test_publish_raises_if_not_initialized(
        self, broker_config, mock_mqtt_client_class
    ):
        """
        Test that publish() raises RuntimeError if not initialized.

        Given: A WorkerPool that has not been initialized
        When: async publish() is called
        Then: RuntimeError is raised
        """
        from loadgen.worker_pool import WorkerPool

        worker_count = 2
        pool = WorkerPool(
            worker_count=worker_count, broker_config=broker_config
        )

        messages = [{"meterId": "000000000049", "value": 100}]
        topic = "test/topic"

        with pytest.raises(RuntimeError, match="not initialized"):
            await pool.publish(messages, topic)

    @pytest.mark.asyncio
    async def test_publish_logs_individual_failures(
        self, broker_config, mock_mqtt_client_class
    ):
        """
        Test that individual publish failures are logged but don't stop others.

        Given: A WorkerPool where worker 1 fails to publish
        When: async publish() is called with 3 messages
        Then: Other workers continue publishing, failure is logged
        """
        from loadgen.worker_pool import WorkerPool

        worker_count = 3
        pool = WorkerPool(
            worker_count=worker_count, broker_config=broker_config
        )

        await pool.initialize()

        messages = [
            {"meterId": "000000000049", "value": 100},
            {"meterId": "000000000050", "value": 200},
            {"meterId": "000000000051", "value": 300},
        ]
        topic = "test/topic"

        # Make worker 1 fail
        async def failing_publish(topic, payload):
            raise Exception("Publish failed")

        pool._workers[1].publish = failing_publish

        # Should not raise - individual failures are logged
        await pool.publish(messages, topic)

        # Verify other workers published
        # Worker 0 and 2 should have published successfully

    @pytest.mark.asyncio
    async def test_publish_all_workers_simultaneously(
        self, broker_config, mock_mqtt_client_class
    ):
        """
        Test that all workers can publish simultaneously using TaskGroup.

        Given: A WorkerPool with 3 workers
        When: 3 messages are published (one per worker)
        Then: All workers publish concurrently
        """
        from loadgen.worker_pool import WorkerPool

        worker_count = 3
        pool = WorkerPool(
            worker_count=worker_count, broker_config=broker_config
        )

        await pool.initialize()

        messages = [
            {"meterId": f"00000000004{i}", "value": i}
            for i in range(3)
        ]
        topic = "test/topic"

        # Add delay to verify concurrent execution
        import time

        async def delayed_publish(topic, payload, delay=0.01):
            await asyncio.sleep(delay)

        for worker in pool._workers:
            worker.publish = delayed_publish

        start = time.time()
        await pool.publish(messages, topic)
        elapsed = time.time() - start

        # With 3 concurrent tasks of 0.01s each, total should be ~0.01s, not 0.03s
        assert elapsed < 0.02  # Allow some margin


# ─── Task 2: Rate Limiter integration ────────────────────────────────────────


class TestWorkerPoolRateLimiter:
    """Test WorkerPool integration with RateLimiter."""

    @pytest.mark.asyncio
    async def test_workerpool_accepts_optional_rate_limiter(self, broker_config):
        """
        Test WorkerPool accepts optional rate_limiter parameter.

        Given: WorkerPool class
        When: Initialized with a rate_limiter
        Then: Rate limiter stored and accessible
        """
        from loadgen.worker_pool import WorkerPool
        from loadgen.rate_limiter import TokenBucketRateLimiter

        rate_limiter = TokenBucketRateLimiter(rate_limit=100)
        pool = WorkerPool(
            worker_count=2, broker_config=broker_config, rate_limiter=rate_limiter
        )
        assert pool._rate_limiter is rate_limiter

    @pytest.mark.asyncio
    async def test_workerpool_without_rate_limiter_works_normally(self, broker_config):
        """
        Test WorkerPool works normally without rate_limiter (default None).

        Given: WorkerPool without rate_limiter
        When: Initialized and used
        Then: rate_limiter is None and pool functions normally
        """
        from loadgen.worker_pool import WorkerPool

        pool = WorkerPool(worker_count=2, broker_config=broker_config)
        assert pool._rate_limiter is None

    @pytest.mark.asyncio
    async def test_publish_calls_rate_limiter_acquire_for_each_message(
        self, broker_config
    ):
        """
        Test publish() calls rate_limiter.acquire() for each message.

        Given: WorkerPool with rate_limiter
        When: publish() is called with messages
        Then: rate_limiter.acquire() called once per message
        """
        from loadgen.worker_pool import WorkerPool
        from loadgen.rate_limiter import TokenBucketRateLimiter

        rate_limiter = TokenBucketRateLimiter(rate_limit=100)
        rate_limiter.acquire = AsyncMock(return_value=None)

        pool = WorkerPool(
            worker_count=2, broker_config=broker_config, rate_limiter=rate_limiter
        )
        await pool.initialize()

        messages = [
            {"trxId": "tx-001", "value": 1},
            {"trxId": "tx-002", "value": 2},
        ]
        topic = "test/topic"

        await pool.publish(messages, topic)

        # acquire should be called once per message
        assert rate_limiter.acquire.call_count == 2

    @pytest.mark.asyncio
    async def test_rate_limiter_shared_across_all_workers(self, broker_config):
        """
        Test rate limiter is shared across all workers (global throttling).

        Given: WorkerPool with rate_limiter and multiple workers
        When: publish() is called
        Then: Rate limiter is called for each message (shared global limit)
        """
        from loadgen.worker_pool import WorkerPool
        from loadgen.rate_limiter import TokenBucketRateLimiter

        rate_limiter = TokenBucketRateLimiter(rate_limit=10)
        acquire_calls = []

        async def tracking_acquire():
            acquire_calls.append(1)
            await asyncio.sleep(0)  # Yield

        rate_limiter.acquire = tracking_acquire

        pool = WorkerPool(
            worker_count=3, broker_config=broker_config, rate_limiter=rate_limiter
        )
        await pool.initialize()

        # Publish 10 messages across 3 workers
        messages = [{"trxId": f"tx-{i}", "value": i} for i in range(10)]
        await pool.publish(messages, "test/topic")

        # Rate limiter should be called 10 times (once per message)
        assert len(acquire_calls) == 10

    @pytest.mark.asyncio
    async def test_publish_without_rate_limiter_works_normally(self, broker_config):
        """
        Test publish() works normally without rate limiter.

        Given: WorkerPool without rate_limiter
        When: publish() is called
        Then: Works normally without calling acquire
        """
        from loadgen.worker_pool import WorkerPool

        pool = WorkerPool(worker_count=2, broker_config=broker_config)
        await pool.initialize()

        messages = [{"trxId": "tx-nolimit", "value": 99}]
        # Should not raise - no rate limiting
        await pool.publish(messages, "test/topic")
        # Success means it worked without rate limiter


# ─── Task 3: Retry Policy integration ────────────────────────────────────────


class TestWorkerPoolRetryPolicy:
    """Test WorkerPool integration with RetryPolicy."""

    @pytest.mark.asyncio
    async def test_workerpool_accepts_optional_retry_policy(self, broker_config):
        """
        Test WorkerPool accepts optional retry_policy parameter.

        Given: WorkerPool class
        When: Initialized with a retry_policy
        Then: Policy stored and accessible
        """
        from loadgen.worker_pool import WorkerPool
        from loadgen.retry_policy import RetryPolicy, BackoffStrategy

        policy = RetryPolicy(max_retries=3, strategy=BackoffStrategy.EXPONENTIAL)
        pool = WorkerPool(
            worker_count=2, broker_config=broker_config, retry_policy=policy
        )
        assert pool._retry_policy is policy

    @pytest.mark.asyncio
    async def test_workerpool_without_retry_policy_works_normally(self, broker_config):
        """
        Test WorkerPool works normally without retry_policy (default None).

        Given: WorkerPool without retry_policy
        When: Initialized
        Then: retry_policy is None and pool functions normally
        """
        from loadgen.worker_pool import WorkerPool

        pool = WorkerPool(worker_count=2, broker_config=broker_config)
        assert pool._retry_policy is None

    @pytest.mark.asyncio
    async def test_publish_wraps_each_call_in_retry_policy(self, broker_config):
        """
        Test publish() wraps each publish call in retry_policy.retry().

        Given: WorkerPool with a retry_policy
        When: publish() is called with messages
        Then: retry_policy.retry() is called for each message
        """
        from loadgen.worker_pool import WorkerPool
        from loadgen.retry_policy import RetryPolicy, BackoffStrategy

        policy = RetryPolicy(max_retries=3, strategy=BackoffStrategy.EXPONENTIAL)
        policy.retry = AsyncMock(return_value=None)

        pool = WorkerPool(
            worker_count=2, broker_config=broker_config, retry_policy=policy
        )
        await pool.initialize()

        messages = [
            {"trxId": "tx-001", "value": 1},
            {"trxId": "tx-002", "value": 2},
        ]
        await pool.publish(messages, "test/topic")

        # retry should be called once per message
        assert policy.retry.call_count == 2

    @pytest.mark.asyncio
    async def test_retryable_errors_trigger_retries_via_policy(self, broker_config):
        """
        Test retryable errors are handled via retry_policy (retries occur).

        Given: WorkerPool with retry_policy and a worker that raises RetryableError twice
        When: publish() is called
        Then: retry_policy handles retries without raising at publish level
        """
        from loadgen.worker_pool import WorkerPool
        from loadgen.retry_policy import RetryPolicy, BackoffStrategy, RetryableError

        policy = RetryPolicy(
            max_retries=3,
            strategy=BackoffStrategy.FIXED,
            base_delay=0.001,  # Very short for tests
        )

        pool = WorkerPool(
            worker_count=1, broker_config=broker_config, retry_policy=policy
        )
        await pool.initialize()

        call_count = 0
        original_publish = pool._workers[0].publish

        async def flaky_publish(topic, payload):
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise RetryableError("QoS ack timeout")
            return await original_publish(topic, payload)

        pool._workers[0].publish = flaky_publish

        messages = [{"trxId": "tx-retry", "value": 42}]
        # Should not raise - retry_policy handles the retries
        await pool.publish(messages, "test/topic")

        # 2 failures + 1 success = 3 calls
        assert call_count == 3

    @pytest.mark.asyncio
    async def test_non_retryable_errors_fail_immediately(self, broker_config):
        """
        Test NonRetryableError fails immediately without retrying.

        Given: WorkerPool with retry_policy and a worker that raises NonRetryableError
        When: publish() is called
        Then: Worker called only once (no retries), failure logged
        """
        from loadgen.worker_pool import WorkerPool
        from loadgen.retry_policy import RetryPolicy, BackoffStrategy, NonRetryableError

        policy = RetryPolicy(
            max_retries=3,
            strategy=BackoffStrategy.FIXED,
            base_delay=0.001,
        )

        pool = WorkerPool(
            worker_count=1, broker_config=broker_config, retry_policy=policy
        )
        await pool.initialize()

        call_count = 0

        async def non_retryable_publish(topic, payload):
            nonlocal call_count
            call_count += 1
            raise NonRetryableError("Connection refused")

        pool._workers[0].publish = non_retryable_publish

        messages = [{"trxId": "tx-nr", "value": 1}]
        # Should not raise at publish level (individual failures logged)
        await pool.publish(messages, "test/topic")

        # Called exactly once — NonRetryableError not retried
        assert call_count == 1

    @pytest.mark.asyncio
    async def test_failed_messages_written_to_artifact_if_configured(
        self, broker_config, tmp_path
    ):
        """
        Test failed messages written to artifact when retry_policy has artifact_path.

        Given: WorkerPool with retry_policy that has artifact_path configured
        When: publish() is called and all retries exhausted
        Then: Artifact file contains failed message entry
        """
        from loadgen.worker_pool import WorkerPool
        from loadgen.retry_policy import RetryPolicy, BackoffStrategy, RetryableError

        artifact_path = str(tmp_path / "failed_events.jsonl")
        policy = RetryPolicy(
            max_retries=1,
            strategy=BackoffStrategy.FIXED,
            base_delay=0.001,
            artifact_path=artifact_path,
        )

        pool = WorkerPool(
            worker_count=1, broker_config=broker_config, retry_policy=policy
        )
        await pool.initialize()

        async def always_fails(topic, payload):
            raise RetryableError("QoS ack timeout")

        pool._workers[0].publish = always_fails

        messages = [{"trxId": "tx-fail-artifact", "value": 99}]
        # Should not raise at publish level
        await pool.publish(messages, "test/topic")

        # Artifact file should contain the failed message
        from pathlib import Path
        import json

        assert Path(artifact_path).exists()
        with open(artifact_path) as f:
            lines = [line.strip() for line in f if line.strip()]
        assert len(lines) == 1
        entry = json.loads(lines[0])
        assert entry["trxId"] == "tx-fail-artifact"
