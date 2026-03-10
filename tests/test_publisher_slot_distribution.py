"""Test per-meter slot distribution in Publisher._generate_payloads()."""

import pytest
from loadgen.publisher import Publisher


@pytest.mark.asyncio
async def test_per_meter_slot_tracking_with_single_meter():
    """With a single meter, all messages should have 15-minute gaps."""
    publisher = Publisher(
        broker_config={
            "host": "localhost",
            "port": 1883,
            "tls_enabled": False,
        },
        worker_count=2,
        message_count=10,
        rate_limit=100,
        qos=1,
        meter_ids=["METER001"],
        dcu_id="DCU-001",
        topic="test-topic",
    )

    messages = await publisher._generate_payloads()

    assert len(messages) == 10

    # All messages should be for METER001
    assert all(m['meterId'] == "METER001" for m in messages)

    # Check that all gaps are 15 minutes
    from datetime import datetime
    sampling_times = sorted([m['operationResult']['samplingTime'] for m in messages])

    for i in range(len(sampling_times) - 1):
        t1 = datetime.fromisoformat(sampling_times[i].replace('Z', '+00:00'))
        t2 = datetime.fromisoformat(sampling_times[i+1].replace('Z', '+00:00'))
        gap_minutes = (t2 - t1).total_seconds() / 60
        assert gap_minutes == 15.0, f"Gap {i}: expected 15 minutes, got {gap_minutes}"


@pytest.mark.asyncio
async def test_per_meter_slot_tracking_with_multiple_meters():
    """With multiple meters, each meter should have 15-minute gaps."""
    publisher = Publisher(
        broker_config={
            "host": "localhost",
            "port": 1883,
            "tls_enabled": False,
        },
        worker_count=2,
        message_count=20,  # 10 messages per meter
        rate_limit=100,
        qos=1,
        meter_ids=["METER001", "METER002"],
        dcu_id="DCU-001",
        topic="test-topic",
    )

    messages = await publisher._generate_payloads()

    assert len(messages) == 20

    # Each meter should have 10 messages
    from collections import Counter
    meter_counts = Counter(m['meterId'] for m in messages)
    assert meter_counts["METER001"] == 10
    assert meter_counts["METER002"] == 10

    # Check that each meter has 15-minute gaps
    from datetime import datetime
    for meter_id in ["METER001", "METER002"]:
        meter_messages = [m for m in messages if m['meterId'] == meter_id]
        sampling_times = sorted([m['operationResult']['samplingTime'] for m in meter_messages])

        for i in range(len(sampling_times) - 1):
            t1 = datetime.fromisoformat(sampling_times[i].replace('Z', '+00:00'))
            t2 = datetime.fromisoformat(sampling_times[i+1].replace('Z', '+00:00'))
            gap_minutes = (t2 - t1).total_seconds() / 60
            assert gap_minutes == 15.0, f"{meter_id} gap {i}: expected 15 minutes, got {gap_minutes}"


@pytest.mark.asyncio
async def test_no_duplicate_meter_sampling_time_pairs():
    """All (meterId, samplingTime) pairs should be unique."""
    publisher = Publisher(
        broker_config={
            "host": "localhost",
            "port": 1883,
            "tls_enabled": False,
        },
        worker_count=2,
        message_count=96,
        rate_limit=100,
        qos=1,
        meter_ids=["METER001", "METER002"],
        dcu_id="DCU-001",
        topic="test-topic",
    )

    messages = await publisher._generate_payloads()

    # Check for duplicate pairs
    pairs = [(m['meterId'], m['operationResult']['samplingTime']) for m in messages]
    unique_pairs = set(pairs)

    assert len(unique_pairs) == len(messages), "Found duplicate (meterId, samplingTime) pairs"
