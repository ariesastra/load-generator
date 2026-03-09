"""Slot planner for assigning 15-minute boundary timestamps.

This module provides functionality to generate samplingTime values that align
to :00, :15, :30, :45 minute boundaries for LP periodic payloads.
"""

from datetime import datetime, timezone, timedelta
from typing import Optional


class SlotPlanner:
    """Assigns sequential 15-minute slot timestamps from a base time.

    The base time is rounded down to the nearest 15-minute boundary
    (:00, :15, :30, or :45). Slots are then assigned sequentially,
    with each slot representing a 15-minute increment from the base time.

    Example:
        planner = SlotPlanner(base_time=datetime(2026, 3, 9, 14, 7, tzinfo=timezone.utc))
        # base_time is rounded to 2026-03-09T14:00:00Z
        planner.assign_slot(0)  # Returns: "2026-03-09T14:00:00Z"
        planner.assign_slot(1)  # Returns: "2026-03-09T14:15:00Z"
        planner.assign_slot(2)  # Returns: "2026-03-09T14:30:00Z"
    """

    def __init__(self, base_time: Optional[datetime] = None):
        """Initialize the slot planner with a base time.

        Args:
            base_time: The base time for slot calculation. If None, uses
                the current UTC time. The time is rounded down to the
                nearest 15-minute boundary (:00, :15, :30, or :45).

        """
        if base_time is None:
            base_time = datetime.now(timezone.utc)

        self.base_time = self._round_to_15_min_boundary(base_time)

    def assign_slot(self, slot_index: int) -> str:
        """Assign a timestamp for the given slot index.

        Args:
            slot_index: The slot index (0-based). Each slot represents
                a 15-minute increment from the base time.

        Returns:
            ISO 8601 formatted timestamp string with 'Z' suffix, e.g.,
            "2026-03-09T14:00:00Z".

        """
        if slot_index < 0:
            raise ValueError(f"slot_index must be non-negative, got {slot_index}")

        # Calculate the timestamp for this slot
        timestamp = self.base_time + timedelta(minutes=slot_index * 15)

        # Format as ISO 8601 with 'Z' suffix
        return timestamp.strftime("%Y-%m-%dT%H:%M:%SZ")

    def _round_to_15_min_boundary(self, dt: datetime) -> datetime:
        """Round a datetime down to the nearest 15-minute boundary.

        Args:
            dt: The datetime to round.

        Returns:
            A new datetime rounded down to the nearest :00, :15, :30, or :45.

        """
        # Round down minutes to nearest 15-minute boundary
        rounded_minutes = (dt.minute // 15) * 15

        # Create new datetime with rounded minutes and zero seconds/microseconds
        return dt.replace(
            minute=rounded_minutes,
            second=0,
            microsecond=0
        )
