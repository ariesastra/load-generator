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
