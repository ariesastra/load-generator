"""
Tests for Publisher orchestrator with graceful shutdown handling.

This module tests the Publisher class that orchestrates the full publishing
workflow and handles KeyboardInterrupt with immediate abort and graceful DISCONNECT.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch, call
import asyncio
import json
from pathlib import Path


@pytest.fixture
def publisher_config():
    """Return publisher configuration for testing."""
    return {
        "broker_config": {
            "host": "localhost",
            "port": 1883,
            "qos": 1,
            "tls_enabled": False,
        },
        "worker_count": 3,
        "message_count": 10,
        "rate_limit": 100,
        "retry_config": {"base_delay": 0.1, "max_delay": 5.0},
        "artifact_dir": Path("/tmp/test_artifacts"),
    }


@pytest.fixture
def mock_worker_pool():
    """Mock WorkerPool for testing Publisher."""
    with patch("loadgen.publisher.WorkerPool", autospec=True) as mock:
        pool = mock.return_value
        pool.initialize = AsyncMock()
        pool.publish = AsyncMock(return_value={"sent": 10, "failed": 0, "duration": 1.23})
        pool.cleanup = AsyncMock()
        yield pool


@pytest.fixture
def mock_payload_factory():
    """Mock PayloadFactory for testing Publisher."""
    with patch("loadgen.publisher.PayloadFactory", autospec=True) as mock:
        factory = mock.return_value
        # Generate mock payloads for testing
        def generate_payload(meter_id, slot_index):
            return json.dumps(
                {
                    "id": f"mode1-{meter_id}-{slot_index}",
                    "meterId": meter_id,
                    "trxId": f"test-trx-{slot_index}",
                    "slotIndex": slot_index,
                }
            ).encode()

        factory.generate_payload = MagicMock(side_effect=generate_payload)
        yield factory


@pytest.fixture
def mock_csv_reader():
    """Mock csv_reader for loading meter IDs."""
    with patch("loadgen.publisher.csv_reader") as mock:
        # Return sample meter IDs
        mock.load_meter_ids = MagicMock(return_value=["123456789000", "123456789001"])
        yield mock


@pytest.mark.asyncio
async def test_publisher_initialization(publisher_config, mock_worker_pool):
    """Test 1: Publisher initialized with broker_config, worker_count, rate_limit, retry_config."""
    from loadgen.publisher import Publisher

    pub = Publisher(
        broker_config=publisher_config["broker_config"],
        worker_count=publisher_config["worker_count"],
        message_count=publisher_config["message_count"],
        rate_limit=publisher_config["rate_limit"],
        retry_config=publisher_config["retry_config"],
        artifact_dir=publisher_config["artifact_dir"],
    )

    # Verify configuration stored
    assert pub.broker_config == publisher_config["broker_config"]
    assert pub.worker_count == publisher_config["worker_count"]
    assert pub.message_count == publisher_config["message_count"]
    assert pub.rate_limit == publisher_config["rate_limit"]
    assert pub.retry_config == publisher_config["retry_config"]
    assert pub.artifact_dir == publisher_config["artifact_dir"]

    # Verify WorkerPool created with correct parameters
    # Since mock_worker_pool is the return value, we check the mock class call
    from loadgen.publisher import WorkerPool
    WorkerPool.assert_called_once()

    # Get the actual call args
    call_args = WorkerPool.call_args
    assert call_args.kwargs["worker_count"] == publisher_config["worker_count"]
    assert call_args.kwargs["broker_config"] == publisher_config["broker_config"]

    # Verify PayloadFactory created
    assert hasattr(pub, "_payload_factory")

    # Verify interrupted flag initialized
    assert pub._interrupted is False


@pytest.mark.asyncio
async def test_publisher_run_generates_payloads(
    publisher_config, mock_worker_pool, mock_payload_factory, mock_csv_reader
):
    """Test 2: async run() generates payloads using PayloadFactory."""
    from loadgen.publisher import Publisher

    pub = Publisher(
        broker_config=publisher_config["broker_config"],
        worker_count=publisher_config["worker_count"],
        message_count=publisher_config["message_count"],
    )

    stats = await pub.run()

    # Verify payload factory used for each message
    assert mock_payload_factory.generate_payload.call_count == publisher_config["message_count"]

    # Verify different meter IDs used
    # Get call args and kwargs
    call_args = mock_payload_factory.generate_payload.call_args_list

    # Debug: print actual calls
    # print(f"Call args: {call_args}")

    # Handle both positional and keyword arguments
    meter_ids_used = []
    slot_indices = []
    for call in call_args:
        # Check if called with keyword args
        if "meter_id" in call.kwargs and "slot_index" in call.kwargs:
            meter_ids_used.append(call.kwargs["meter_id"])
            slot_indices.append(call.kwargs["slot_index"])
        # Check if called with positional args
        elif call.args:
            meter_ids_used.append(call.args[0])
            slot_indices.append(call.args[1])
        else:
            # Fallback for any other case
            continue

    assert set(meter_ids_used) == {"123456789000", "123456789001"}
    assert slot_indices == list(range(publisher_config["message_count"]))


@pytest.mark.asyncio
async def test_publisher_run_publishes_via_worker_pool(
    publisher_config, mock_worker_pool, mock_csv_reader
):
    """Test 3: async run() publishes messages via WorkerPool."""
    from loadgen.publisher import Publisher

    pub = Publisher(
        broker_config=publisher_config["broker_config"],
        worker_count=publisher_config["worker_count"],
        message_count=publisher_config["message_count"],
    )

    stats = await pub.run()

    # Verify worker pool initialized
    mock_worker_pool.initialize.assert_called_once()

    # Verify publish called with correct parameters
    mock_worker_pool.publish.assert_called_once()
    publish_call = mock_worker_pool.publish.call_args

    # Verify messages list passed
    messages_arg = publish_call.kwargs.get("messages")
    assert len(messages_arg) == publisher_config["message_count"]

    # Verify topic passed
    assert publish_call.kwargs.get("topic") == "load-profile"

    # Verify cleanup called
    mock_worker_pool.cleanup.assert_called_once()


@pytest.mark.asyncio
async def test_publisher_run_returns_statistics(
    publisher_config, mock_worker_pool, mock_csv_reader
):
    """Test 4: async run() returns publish statistics (sent, failed, duration)."""
    from loadgen.publisher import Publisher

    # Setup mock stats (WorkerPool returns these - duration is added by Publisher)
    worker_stats = {"sent": 10, "failed": 0}
    mock_worker_pool.publish.return_value = worker_stats

    pub = Publisher(
        broker_config=publisher_config["broker_config"],
        worker_count=publisher_config["worker_count"],
        message_count=publisher_config["message_count"],
    )

    stats = await pub.run()

    # Verify stats returned - check that it has the expected structure
    assert stats["sent"] == 10
    assert stats["failed"] == 0
    assert "duration" in stats  # Duration is added by Publisher
    assert stats["duration"] > 0  # Duration should be positive

    # Verify cleanup called after publish
    mock_worker_pool.cleanup.assert_called_once()
