"""Tests for slot_planner module - 15-minute boundary timestamp assignment."""

import pytest
from datetime import datetime, timezone, timedelta
from loadgen.slot_planner import SlotPlanner


class TestSlotPlannerInitialization:
    """Test SlotPlanner initialization and base time rounding."""

    def test_base_time_rounds_down_to_15min_boundary(self):
        """Test that base_time rounds down to nearest :00, :15, :30, or :45."""
        # Test with times that should round down
        test_cases = [
            (datetime(2026, 3, 9, 14, 7,  tzinfo=timezone.utc), datetime(2026, 3, 9, 14, 0,  tzinfo=timezone.utc)),
            (datetime(2026, 3, 9, 14, 15, tzinfo=timezone.utc), datetime(2026, 3, 9, 14, 15, tzinfo=timezone.utc)),
            (datetime(2026, 3, 9, 14, 22, tzinfo=timezone.utc), datetime(2026, 3, 9, 14, 15, tzinfo=timezone.utc)),
            (datetime(2026, 3, 9, 14, 30, tzinfo=timezone.utc), datetime(2026, 3, 9, 14, 30, tzinfo=timezone.utc)),
            (datetime(2026, 3, 9, 14, 37, tzinfo=timezone.utc), datetime(2026, 3, 9, 14, 30, tzinfo=timezone.utc)),
            (datetime(2026, 3, 9, 14, 45, tzinfo=timezone.utc), datetime(2026, 3, 9, 14, 45, tzinfo=timezone.utc)),
            (datetime(2026, 3, 9, 14, 52, tzinfo=timezone.utc), datetime(2026, 3, 9, 14, 45, tzinfo=timezone.utc)),
            (datetime(2026, 3, 9, 14, 59, tzinfo=timezone.utc), datetime(2026, 3, 9, 14, 45, tzinfo=timezone.utc)),
        ]

        for input_time, expected_base in test_cases:
            planner = SlotPlanner(base_time=input_time)
            assert planner.base_time == expected_base, \
                f"Input {input_time} should round to {expected_base}, got {planner.base_time}"

    def test_base_time_defaults_to_current_utc_time(self):
        """Test that base_time defaults to current UTC time when None."""
        now = datetime.now(timezone.utc)
        planner = SlotPlanner(base_time=None)

        # Due to rounding to 15-minute boundaries, the difference can be up to 75 seconds
        # (when now is at 12:31:14, it rounds to 12:30:00, difference is 1m14s)
        # We verify the rounded time is within 0-15 minutes of now
        time_diff = (now - planner.base_time).total_seconds()
        assert 0 <= time_diff <= 900, \
            f"Default base_time should be within 0-15 minutes of current time, got {time_diff}s"

        # Verify it's on a 15-minute boundary
        assert planner.base_time.minute % 15 == 0, \
            f"Base time should be on 15-minute boundary, got minute={planner.base_time.minute}"
        assert planner.base_time.second == 0, \
            f"Base time should have zero seconds, got second={planner.base_time.second}"
        assert planner.base_time.microsecond == 0, \
            f"Base time should have zero microseconds, got microsecond={planner.base_time.microsecond}"

    def test_base_time_preserves_provided_boundary_time(self):
        """Test that a time already on a 15-minute boundary is preserved."""
        boundary_time = datetime(2026, 3, 9, 14, 30, tzinfo=timezone.utc)
        planner = SlotPlanner(base_time=boundary_time)
        assert planner.base_time == boundary_time, \
            f"Boundary time should be preserved: {boundary_time}"


class TestSlotAssignment:
    """Test assign_slot method for timestamp calculation."""

    def test_assign_slot_0_returns_base_time(self):
        """Test that assign_slot(0) returns the base time."""
        base_time = datetime(2026, 3, 9, 14, 0, tzinfo=timezone.utc)
        planner = SlotPlanner(base_time=base_time)

        slot_0 = planner.assign_slot(0)
        expected = "2026-03-09T14:00:00Z"

        assert slot_0 == expected, \
            f"Slot 0 should return base time, expected {expected}, got {slot_0}"

    def test_assign_slot_1_returns_base_plus_15_min(self):
        """Test that assign_slot(1) returns base_time + 15 minutes."""
        base_time = datetime(2026, 3, 9, 14, 0, tzinfo=timezone.utc)
        planner = SlotPlanner(base_time=base_time)

        slot_1 = planner.assign_slot(1)
        expected = "2026-03-09T14:15:00Z"

        assert slot_1 == expected, \
            f"Slot 1 should return base + 15min, expected {expected}, got {slot_1}"

    def test_assign_slot_n_returns_base_plus_n_times_15_min(self):
        """Test that assign_slot(n) returns base_time + (n * 15) minutes."""
        base_time = datetime(2026, 3, 9, 14, 0, tzinfo=timezone.utc)
        planner = SlotPlanner(base_time=base_time)

        test_cases = [
            (0, "2026-03-09T14:00:00Z"),
            (1, "2026-03-09T14:15:00Z"),
            (2, "2026-03-09T14:30:00Z"),
            (3, "2026-03-09T14:45:00Z"),
            (4, "2026-03-09T15:00:00Z"),
            (10, "2026-03-09T16:30:00Z"),
        ]

        for slot_index, expected_timestamp in test_cases:
            result = planner.assign_slot(slot_index)
            assert result == expected_timestamp, \
                f"Slot {slot_index} should return {expected_timestamp}, got {result}"

    def test_timestamps_are_iso8601_format(self):
        """Test that all timestamps are in ISO 8601 format with 'Z' suffix."""
        base_time = datetime(2026, 3, 9, 14, 30, tzinfo=timezone.utc)
        planner = SlotPlanner(base_time=base_time)

        # Test multiple slots
        for i in range(10):
            timestamp = planner.assign_slot(i)
            # ISO 8601 format: YYYY-MM-DDTHH:MM:SSZ
            assert timestamp.endswith('Z'), \
                f"Timestamp should end with 'Z': {timestamp}"
            assert 'T' in timestamp, \
                f"Timestamp should contain 'T' separator: {timestamp}"

            # Verify it can be parsed back
            parsed = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
            assert parsed.tzinfo == timezone.utc, \
                f"Parsed timestamp should be UTC: {timestamp}"

    def test_timestamps_end_in_15min_boundaries(self):
        """Test that all timestamps end in :00, :15, :30, or :45 minutes."""
        base_time = datetime(2026, 3, 9, 14, 7, tzinfo=timezone.utc)  # Will round to :00
        planner = SlotPlanner(base_time=base_time)

        valid_minutes = {0, 15, 30, 45}

        for i in range(10):
            timestamp = planner.assign_slot(i)
            # Extract minutes from timestamp
            minutes_str = timestamp.split(':')[1]
            minutes = int(minutes_str)

            assert minutes in valid_minutes, \
                f"Timestamp {timestamp} should end in :00, :15, :30, or :45"

    def test_assign_slot_with_nonzero_base(self):
        """Test slot assignment with a base time not on the hour."""
        base_time = datetime(2026, 3, 9, 14, 30, tzinfo=timezone.utc)
        planner = SlotPlanner(base_time=base_time)

        slot_0 = planner.assign_slot(0)
        slot_1 = planner.assign_slot(1)
        slot_2 = planner.assign_slot(2)

        assert slot_0 == "2026-03-09T14:30:00Z"
        assert slot_1 == "2026-03-09T14:45:00Z"
        assert slot_2 == "2026-03-09T15:00:00Z"

    def test_assign_slot_handles_large_indices(self):
        """Test that assign_slot works with larger slot indices."""
        base_time = datetime(2026, 3, 9, 0, 0, tzinfo=timezone.utc)
        planner = SlotPlanner(base_time=base_time)

        # Test slot 95 (should be near end of day)
        slot_95 = planner.assign_slot(95)
        expected = "2026-03-09T23:45:00Z"
        assert slot_95 == expected, \
            f"Slot 95 should return {expected}, got {slot_95}"
