"""
Test stubs for uniqueness tracking functionality (INPUT-03 requirement).

These tests validate that generated payloads have unique (meterId, samplingTime)
pairs with proper collision handling.
"""

import pytest
from loadgen.payload import PayloadFactory


def test_unique_meter_sampling_time_pairs():
    """
    Verify no duplicate (meterId, samplingTime) pairs in generated payloads.

    Given: Multiple payloads are generated for the same meter
    When: Each payload is assigned a sampling time
    Then: All (meterId, samplingTime) pairs are unique
    And: No two payloads share the same combination
    """
    factory = PayloadFactory()
    payloads = [
        factory.generate_payload(meter_id="000000000049", slot_index=0),
        factory.generate_payload(meter_id="000000000049", slot_index=1),
        factory.generate_payload(meter_id="000000000049", slot_index=2),
    ]

    # Extract (meterId, samplingTime) pairs
    pairs = [(p["meterId"], p["operationResult"]["samplingTime"]) for p in payloads]

    # Verify all pairs are unique
    assert len(pairs) == len(set(pairs)), "All (meterId, samplingTime) pairs must be unique"


def test_collision_handling():
    """
    Verify collision increments samplingTime by 15 minutes.

    Given: A (meterId, samplingTime) pair already exists
    When: A new payload would create a duplicate pair
    Then: The samplingTime is incremented by 15 minutes
    And: The new pair is unique
    """
    factory = PayloadFactory()

    # Generate first payload with slot_index=0
    payload1 = factory.generate_payload(meter_id="000000000049", slot_index=0)
    first_sampling_time = payload1["operationResult"]["samplingTime"]

    # Try to generate another payload with same (meter_id, slot_index)
    # This should detect collision and increment
    payload2 = factory.generate_payload(meter_id="000000000049", slot_index=0)
    second_sampling_time = payload2["operationResult"]["samplingTime"]

    # Verify they are different (collision was handled)
    assert first_sampling_time != second_sampling_time, "Collision should be handled with new timestamp"

    # Verify the second timestamp is 15 minutes later
    from datetime import datetime
    t1 = datetime.fromisoformat(first_sampling_time.replace('Z', '+00:00'))
    t2 = datetime.fromisoformat(second_sampling_time.replace('Z', '+00:00'))
    diff = (t2 - t1).total_seconds() / 60  # Convert to minutes

    assert diff == 15, f"Collision should increment by 15 minutes, got {diff} minutes"


def test_uniqueness_scope_per_run():
    """
    Verify uniqueness is per-run only.

    Given: Two separate run instances
    When: Each instance generates payloads
    Then: Uniqueness is tracked separately per run
    And: Different runs can have the same (meterId, samplingTime) pairs
    """
    # Simulate two separate runs
    factory1 = PayloadFactory()
    factory2 = PayloadFactory()

    # Both factories can generate the same pair without collision
    payload1 = factory1.generate_payload(meter_id="000000000049", slot_index=0)
    payload2 = factory2.generate_payload(meter_id="000000000049", slot_index=0)

    # They should have the same sampling time (since both start at slot_index=0)
    assert payload1["operationResult"]["samplingTime"] == payload2["operationResult"]["samplingTime"]

    # But different trxIds (each is unique)
    assert payload1["trxId"] != payload2["trxId"]


def test_uniqueness_tracking_with_multiple_meters():
    """
    Verify uniqueness tracking works correctly across multiple meters.

    Given: Payloads for multiple different meters
    When: Sampling times are assigned
    Then: Same sampling time can be used for different meters
    And: Each meter has unique sampling times within itself
    """
    factory = PayloadFactory()
    payloads = [
        factory.generate_payload(meter_id="000000000049", slot_index=0),
        factory.generate_payload(meter_id="000000000050", slot_index=0),  # Same time, different meter - OK
        factory.generate_payload(meter_id="000000000049", slot_index=1),
    ]

    pairs = [(p["meterId"], p["operationResult"]["samplingTime"]) for p in payloads]

    # All pairs should be unique
    assert len(pairs) == len(set(pairs)), "All pairs must be unique"

    # But different meters can share the same sampling time
    meter_49_times = [p["operationResult"]["samplingTime"] for p in payloads if p["meterId"] == "000000000049"]
    meter_50_times = [p["operationResult"]["samplingTime"] for p in payloads if p["meterId"] == "000000000050"]

    assert len(meter_49_times) == len(set(meter_49_times)), "Meter 49 should have unique times"
    assert len(meter_50_times) == len(set(meter_50_times)), "Meter 50 should have unique times"


def test_uniqueness_set_initialization():
    """
    Verify uniqueness tracking set is properly initialized.

    Given: A new uniqueness tracker is created
    When: The tracker is initialized
    Then: The tracking set is empty
    And: Ready to track (meterId, samplingTime) pairs
    """
    factory = PayloadFactory()

    # Should have empty uniqueness set at start
    assert len(factory._seen_pairs) == 0, "New tracker should start empty"
    assert isinstance(factory._seen_pairs, set), "Tracker should use a set for O(1) lookups"


def test_collision_logging(caplog):
    """
    Verify collisions are logged when detected and resolved.

    Given: A collision occurs during payload generation
    When: The collision is detected and resolved
    Then: A warning is logged with details
    And: Generation continues without error
    """
    import logging
    caplog.set_level(logging.WARNING)

    factory = PayloadFactory()

    # Generate first payload
    factory.generate_payload(meter_id="000000000049", slot_index=0)

    # Generate duplicate (should trigger collision handling and logging)
    factory.generate_payload(meter_id="000000000049", slot_index=0)

    # Verify warning was logged
    assert any("Collision" in record.message for record in caplog.records), \
        "Collision should be logged"


def test_multiple_collisions_sequential():
    """
    Verify multiple sequential collisions are handled correctly.

    Given: A sampling time is already taken
    When: Multiple payloads request the same slot
    Then: Each collision increments by 15 minutes
    And: All payloads end up with unique times
    """
    factory = PayloadFactory()

    # Generate 3 payloads for the same slot
    payloads = [
        factory.generate_payload(meter_id="000000000049", slot_index=0),
        factory.generate_payload(meter_id="000000000049", slot_index=0),
        factory.generate_payload(meter_id="000000000049", slot_index=0),
    ]

    # Extract sampling times
    times = [p["operationResult"]["samplingTime"] for p in payloads]

    # All should be unique
    assert len(times) == len(set(times)), "All sampling times must be unique"

    # Verify they are 15 minutes apart
    from datetime import datetime
    t1 = datetime.fromisoformat(times[0].replace('Z', '+00:00'))
    t2 = datetime.fromisoformat(times[1].replace('Z', '+00:00'))
    t3 = datetime.fromisoformat(times[2].replace('Z', '+00:00'))

    diff12 = (t2 - t1).total_seconds() / 60
    diff23 = (t3 - t2).total_seconds() / 60

    assert diff12 == 15, f"First collision should increment by 15 minutes, got {diff12}"
    assert diff23 == 15, f"Second collision should increment by 15 minutes, got {diff23}"


def test_different_meters_same_slot():
    """
    Verify different meters can use the same slot without collision.

    Given: Multiple meters using the same slot index
    When: Payloads are generated
    Then: No collision occurs
    And: All payloads have the same sampling time
    """
    factory = PayloadFactory()

    payload1 = factory.generate_payload(meter_id="000000000049", slot_index=0)
    payload2 = factory.generate_payload(meter_id="000000000050", slot_index=0)
    payload3 = factory.generate_payload(meter_id="000000000051", slot_index=0)

    # All should have the same sampling time (no collision for different meters)
    times = [
        payload1["operationResult"]["samplingTime"],
        payload2["operationResult"]["samplingTime"],
        payload3["operationResult"]["samplingTime"],
    ]

    # All times should be identical since different meters can share the same slot
    assert len(times) == 3, "Should have 3 timestamps"
    assert len(set(times)) == 1, "Different meters should be able to use same slot time"
