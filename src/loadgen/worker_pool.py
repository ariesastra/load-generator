"""
Worker Pool for concurrent MQTT publishing.

This module provides the WorkerPool class that manages multiple MQTTClient
instances (workers) for parallel async publishing with pre-connect and
fail-fast behavior.

Key features:
- Creates N MQTTClient workers on initialization
- Pre-connects all workers before publishing begins
- Fail-fast if any worker fails to connect
- Concurrent publish dispatch using asyncio.gather (Python 3.9 compatible)
- Round-robin message distribution across workers
- Cleanup method to disconnect all workers gracefully
"""

import asyncio
import json
import structlog
from typing import List, Dict, Any, Optional, Union

# Placeholder for MQTTClient - will be implemented in 02-01
# For now, we'll use a placeholder that the tests will mock
class MQTTClient:
    """
    Placeholder for MQTTClient.

    This is a placeholder that will be replaced by the actual MQTTClient
    implementation from plan 02-01. The tests will mock this class.
    """

    def __init__(
        self,
        host: str,
        port: int,
        qos: int,
        tls_enabled: bool = False,
        username: Optional[str] = None,
        password: Optional[str] = None,
    ):
        self.host = host
        self.port = port
        self.qos = qos
        self.tls_enabled = tls_enabled
        self.username = username
        self.password = password
        self._connected = False

    async def connect(self) -> None:
        """Connect to MQTT broker."""
        self._connected = True

    async def disconnect(self) -> None:
        """Disconnect from MQTT broker."""
        self._connected = False

    async def publish(self, topic: str, payload: Union[bytes, str]) -> None:
        """Publish message to MQTT broker."""
        if not self._connected:
            raise Exception("Not connected")


# Custom exceptions
class WorkerConnectionError(Exception):
    """
    Raised when any worker fails to connect during initialization.

    This exception is raised during the pre-connect phase if any worker
    cannot establish a connection to the MQTT broker. All already-connected
    workers are disconnected before this exception is raised.
    """

    pass


class WorkerPool:
    """
    Manages multiple MQTTClient workers for concurrent async publishing.

    The WorkerPool creates N MQTTClient instances on initialization and
    provides methods to pre-connect all workers (with fail-fast behavior)
    and disconnect all workers gracefully.

    Usage:
        pool = WorkerPool(worker_count=5, broker_config=config)
        await pool.initialize()  # Pre-connect all workers
        # ... use workers for publishing ...
        await pool.cleanup()  # Disconnect all workers
    """

    def __init__(self, worker_count: int, broker_config: Dict[str, Any]):
        """
        Initialize WorkerPool with N workers.

        Args:
            worker_count: Number of MQTTClient workers to create
            broker_config: Dictionary with broker connection parameters:
                - host: MQTT broker hostname or IP
                - port: MQTT broker port (default 1883)
                - qos: MQTT QoS level (0, 1, or 2)
                - tls_enabled: Whether to use TLS (default False)
                - username: Optional username for authentication
                - password: Optional password for authentication

        Raises:
            ValueError: If worker_count is less than 1
        """
        if worker_count < 1:
            raise ValueError("worker_count must be at least 1")

        self._worker_count = worker_count
        self._broker_config = broker_config
        self._workers: List[MQTTClient] = []
        self._initialized = False
        self._logger = structlog.get_logger()
        self._current_worker_index = 0  # For round-robin distribution

        # Create N MQTTClient instances
        for _ in range(worker_count):
            worker = MQTTClient(
                host=broker_config["host"],
                port=broker_config["port"],
                qos=broker_config["qos"],
                tls_enabled=broker_config.get("tls_enabled", False),
                username=broker_config.get("username"),
                password=broker_config.get("password"),
            )
            self._workers.append(worker)

    async def initialize(self) -> None:
        """
        Pre-connect all workers before publishing begins.

        This method connects all workers to the MQTT broker. If any worker
        fails to connect, all already-connected workers are disconnected
        and WorkerConnectionError is raised (fail-fast behavior).

        Raises:
            WorkerConnectionError: If any worker fails to connect
            RuntimeError: If already initialized
        """
        if self._initialized:
            raise RuntimeError("WorkerPool already initialized")

        connected_workers: List[MQTTClient] = []

        try:
            # Connect all workers
            for i, worker in enumerate(self._workers):
                try:
                    await worker.connect()
                    connected_workers.append(worker)
                    self._logger.info(
                        "worker_connected",
                        worker_index=i,
                        host=self._broker_config["host"],
                        port=self._broker_config["port"],
                    )
                except Exception as e:
                    self._logger.error(
                        "worker_connection_failed",
                        worker_index=i,
                        error=str(e),
                    )
                    # Cleanup already-connected workers
                    for connected_worker in connected_workers:
                        try:
                            await connected_worker.disconnect()
                        except Exception:
                            # Ignore disconnect errors during cleanup
                            pass
                    raise WorkerConnectionError(
                        f"Worker {i} failed to connect: {e}"
                    )

            self._initialized = True
            self._logger.info(
                "worker_pool_initialized",
                worker_count=self._worker_count,
            )

        except Exception as e:
            if isinstance(e, WorkerConnectionError):
                raise
            # Re-raise unexpected exceptions
            raise

    async def cleanup(self) -> None:
        """
        Disconnect all workers gracefully.

        This method disconnects all workers from the MQTT broker.
        It should be called when the WorkerPool is no longer needed.
        """
        for i, worker in enumerate(self._workers):
            if worker._connected:  # Access internal state for cleanup
                try:
                    await worker.disconnect()
                    self._logger.info("worker_disconnected", worker_index=i)
                except Exception as e:
                    self._logger.warning(
                        "worker_disconnect_failed",
                        worker_index=i,
                        error=str(e),
                    )

        self._initialized = False
        self._logger.info("worker_pool_cleaned_up")

    async def publish(self, messages: List[Dict[str, Any]], topic: str) -> None:
        """
        Dispatch messages across workers concurrently using round-robin.

        This method distributes messages across workers in a round-robin fashion
        and publishes them concurrently using asyncio.gather. Individual publish
        failures are logged but don't stop other workers from publishing.

        Args:
            messages: List of message dictionaries to publish
            topic: MQTT topic to publish to

        Raises:
            RuntimeError: If WorkerPool has not been initialized
        """
        if not self._initialized:
            raise RuntimeError("WorkerPool not initialized. Call initialize() first.")

        # Create tasks for each message
        tasks = []
        for message in messages:
            # Select worker using round-robin
            worker_index = self._current_worker_index % self._worker_count
            worker = self._workers[worker_index]
            self._current_worker_index += 1

            # Create task for this message
            task = self._worker_publish_task(worker, topic, message)
            tasks.append(task)

        # Execute all tasks concurrently
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

    async def _worker_publish_task(
        self, worker: MQTTClient, topic: str, message: Dict[str, Any]
    ) -> None:
        """
        Publish a single message using the given worker.

        This private method wraps worker.publish() with error handling and logging.
        Individual failures are logged but don't propagate to stop other workers.

        Args:
            worker: The MQTTClient worker to use for publishing
            topic: MQTT topic to publish to
            message: Message dictionary to publish
        """
        try:
            # Serialize message to JSON (using stdlib json for now)
            payload = json.dumps(message).encode("utf-8")
            await worker.publish(topic, payload)
        except Exception as e:
            # Log failure but don't raise - other workers continue
            self._logger.warning(
                "worker_publish_failed",
                worker_id=id(worker),
                topic=topic,
                message_id=message.get("trxId", message.get("meterId", "unknown")),
                error=str(e),
            )

    @property
    def worker_count(self) -> int:
        """Return the number of workers in the pool."""
        return self._worker_count

    @property
    def initialized(self) -> bool:
        """Return whether the pool has been initialized."""
        return self._initialized
