"""
Tests for Publisher graceful shutdown on Ctrl+C.

This module tests the Publisher shutdown behavior including:
- KeyboardInterrupt handling
- Immediate abort with graceful cleanup
- Partial artifact writing
- Double Ctrl+C force quit
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch, call
import asyncio
import time
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
        "message_count": 100,  # Larger number for interrupt testing
        "artifact_dir": Path("/tmp/test_artifacts"),
    }


@pytest.fixture
def mock_worker_pool():
    """Mock WorkerPool for testing Publisher."""
    with patch("loadgen.publisher.WorkerPool", autospec=True) as mock:
        pool = mock.return_value
        pool.initialize = AsyncMock()
        pool.publish = AsyncMock(return_value={"sent": 50, "failed": 0, "duration": 5.0})
        pool.cleanup = AsyncMock()
        yield pool


@pytest.fixture
def mock_payload_factory():
    """Mock PayloadFactory for testing Publisher."""
    with patch("loadgen.publisher.PayloadFactory", autospec=True) as mock:
        factory = mock.return_value

        # Generate mock payloads for testing
        def generate_payload(meter_id, slot_index):
            return f'{{"meterId":"{meter_id}","slotIndex":{slot_index}}}'.encode()

        factory.generate_payload = MagicMock(side_effect=generate_payload)
        yield factory


@pytest.fixture
def mock_csv_reader():
    """Mock csv_reader for loading meter IDs."""
    with patch("loadgen.publisher.csv_reader") as mock:
        mock.load_meter_ids = MagicMock(return_value=["123456789000"])
        yield mock


@pytest.mark.asyncio
async def test_keyboard_interrupt_triggers_immediate_abort(
    publisher_config, mock_worker_pool, mock_payload_factory, mock_csv_reader
):
    """Test 1: KeyboardInterrupt triggers immediate abort."""
    from loadgen.publisher import Publisher, PublishInterruptError

    pub = Publisher(
        broker_config=publisher_config["broker_config"],
        worker_count=publisher_config["worker_count"],
        message_count=publisher_config["message_count"],
    )

    # Trigger KeyboardInterrupt during run
    mock_worker_pool.publish.side_effect = KeyboardInterrupt()

    with pytest.raises(PublishInterruptError) as exc_info:
        await pub.run()

    # Verify interrupt error raised
    assert "interrupted" in str(exc_info.value).lower()


@pytest.mark.asyncio
async def test_interrupted_flag_stops_new_publish_tasks(
    publisher_config, mock_worker_pool, mock_payload_factory, mock_csv_reader
):
    """Test 2: Interrupted flag stops new publish tasks."""
    from loadgen.publisher import Publisher

    pub = Publisher(
        broker_config=publisher_config["broker_config"],
        worker_count=publisher_config["worker_count"],
        message_count=publisher_config["message_count"],
    )

    # Manually set interrupted flag
    pub._interrupted = True

    # Run should complete without calling publish (due to interrupted flag)
    stats = await pub.run()

    # Verify publish was not called
    mock_worker_pool.publish.assert_not_called()

    # Verify cleanup was still called
    mock_worker_pool.cleanup.assert_called_once()


@pytest.mark.asyncio
async def test_graceful_disconnect_called_during_shutdown(
    publisher_config, mock_worker_pool, mock_payload_factory, mock_csv_reader
):
    """Test 3: Graceful DISCONNECT called during shutdown."""
    from loadgen.publisher import Publisher, PublishInterruptError

    pub = Publisher(
        broker_config=publisher_config["broker_config"],
        worker_count=publisher_config["worker_count"],
        message_count=publisher_config["message_count"],
        artifact_dir=publisher_config["artifact_dir"],
    )

    # Trigger KeyboardInterrupt
    mock_worker_pool.publish.side_effect = KeyboardInterrupt()

    with pytest.raises(PublishInterruptError):
        await pub.run()

    # Verify cleanup was called for graceful DISCONNECT
    mock_worker_pool.cleanup.assert_called_once()


@pytest.mark.asyncio
async def test_partial_artifacts_written_on_interruption(
    publisher_config, mock_worker_pool, mock_payload_factory, mock_csv_reader
):
    """Test 4: Partial artifacts written on interruption."""
    from loadgen.publisher import Publisher, PublishInterruptError
    from pathlib import Path

    # Use tmp_path for isolated test artifacts
    artifact_dir = Path("/tmp/test_publisher_artifacts")
    artifact_dir.mkdir(exist_ok=True)

    pub = Publisher(
        broker_config=publisher_config["broker_config"],
        worker_count=publisher_config["worker_count"],
        message_count=publisher_config["message_count"],
        artifact_dir=artifact_dir,
    )

    # Mock stats returned before interrupt
    mock_worker_pool.publish.return_value = {"sent": 50, "failed": 1, "duration": 2.5}

    # Trigger KeyboardInterrupt during publish (after some work done)
    with pytest.raises(PublishInterruptError):
        # Trigger interrupt directly instead of trying to catch in run
        try:
            await pub.run()
        except Exception:
            pass
        # Now simulate the interrupt handling
        await pub._handle_interrupt(stats={"sent": 50, "failed": 1}, start_time=time.time())

    # Check artifact file exists
    artifact_file = artifact_dir / "run.json"
    assert artifact_file.exists()

    # Verify artifact content
    with open(artifact_file) as f:
        artifact_data = json.load(f)

    assert artifact_data["status"] == "interrupted"
    assert artifact_data["messages_sent"] == 50
    assert artifact_data["messages_failed"] == 1
    assert "duration_seconds" in artifact_data
    assert "interrupted_at" in artifact_data

    # Cleanup
    artifact_file.unlink()
    artifact_dir.rmdir()


@pytest.mark.asyncio
async def test_double_ctrl_c_force_quit(
    publisher_config, mock_worker_pool, mock_payload_factory, mock_csv_reader
):
    """Test 5: Double Ctrl+C triggers force quit."""
    from loadgen.publisher import Publisher
    import sys

    pub = Publisher(
        broker_config=publisher_config["broker_config"],
        worker_count=publisher_config["worker_count"],
        message_count=publisher_config["message_count"],
    )

    # Simulate double interrupt by setting count to 2
    pub._interrupt_count = 2
    pub._last_interrupt_time = time.time()  # Recent interrupt

    # Mock sys.exit to catch the force quit
    with pytest.raises(SystemExit) as exc_info:
        with patch("loadgen.publisher.sys.exit") as mock_exit:
            mock_exit.side_effect = SystemExit(1)
            # Run should trigger force quit
            await pub._handle_interrupt(stats={"sent": 0}, start_time=time.time())

    # Verify exit was called with error code
    assert exc_info.value.code == 1
