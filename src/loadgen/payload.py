"""Payload factory for generating LP periodic events.

This module provides functionality to generate realistic Load Profile (LP)
periodic event payloads with guaranteed uniqueness constraints.
"""

import logging
import uuid
from datetime import datetime, timezone, timedelta
from typing import Optional

from loadgen.slot_planner import SlotPlanner


# Configure logging
logger = logging.getLogger(__name__)


class PayloadFactory:
    """Generates unique LP periodic payloads with guaranteed uniqueness constraints.

    This factory creates payloads that match the python-mqtt-benchmark.md specification
    for LP periodic events. It enforces uniqueness at two levels:
    1. Per-message: Unique trxId (UUID v4)
    2. Per-run: Unique (meterId, samplingTime) pairs

    On collision of (meterId, samplingTime), the samplingTime is incremented
    by 15 minutes until a unique pair is found.

    Example:
        >>> factory = PayloadFactory(dcu_id="DCU-001")
        >>> payload = factory.generate_payload(meter_id="000000000049", slot_index=0)
        >>> print(payload["trxId"])  # Unique UUID
        >>> print(payload["operationResult"]["samplingTime"])  # ISO 8601 timestamp
    """

    def __init__(self, dcu_id: str = "DCU-001"):
        """Initialize the payload factory.

        Args:
            dcu_id: The DCU ID to use in generated payloads. Defaults to "DCU-001".

        """
        self.dcu_id = dcu_id
        self._seen_pairs: set[tuple[str, str]] = set()  # Track (meterId, samplingTime)
        self._slot_planner = SlotPlanner()  # For timestamp generation
        self._slot_counter: int = 0  # Per-meter slot tracking

    def generate_payload(self, meter_id: str, slot_index: int = 0) -> dict:
        """Generate a unique LP periodic payload.

        This method generates a payload matching the python-mqtt-benchmark.md spec.
        It ensures uniqueness by tracking (meterId, samplingTime) pairs and
        incrementing the samplingTime by 15 minutes on collision.

        Args:
            meter_id: The meter ID (12 characters) for this payload
            slot_index: The slot index (0-based) for sampling time calculation.
                Each slot represents a 15-minute increment from the base time.

        Returns:
            A dictionary containing the LP periodic payload with all required fields.

        Raises:
            ValueError: If slot_index is negative

        Example:
            >>> factory = PayloadFactory()
            >>> payload = factory.generate_payload(meter_id="000000000049", slot_index=0)
            >>> payload["operationType"]
            'meterLoadProfilePeriodic'
            >>> payload["meterId"]
            '000000000049'
        """
        if slot_index < 0:
            raise ValueError(f"slot_index must be non-negative, got {slot_index}")

        # Generate unique transaction ID
        trx_id = str(uuid.uuid4())

        # Get initial sampling time from slot planner
        sampling_time = self._slot_planner.assign_slot(slot_index)

        # Handle collision: if (meter_id, sampling_time) already seen, increment until unique
        original_slot_index = slot_index
        while (meter_id, sampling_time) in self._seen_pairs:
            logger.warning(
                f"Collision detected for meter {meter_id} at {sampling_time}. "
                f"Incrementing slot index."
            )
            slot_index += 1
            sampling_time = self._slot_planner.assign_slot(slot_index)

        # Track this unique pair
        self._seen_pairs.add((meter_id, sampling_time))

        # Calculate collection time (samplingTime + 30 seconds)
        sampling_dt = datetime.fromisoformat(sampling_time.replace('Z', '+00:00'))
        collection_dt = sampling_dt + timedelta(seconds=30)
        collection_time = self._format_iso8601(collection_dt)

        # Build payload matching python-mqtt-benchmark.md schema
        payload = {
            "trxId": trx_id,
            "meterId": meter_id,
            "dcuId": self.dcu_id,
            "operationType": "meterLoadProfilePeriodic",
            "operationResult": {
                "samplingTime": sampling_time,
                "collectionTime": collection_time,
                "registers": {
                    # Placeholder LP register values for phase 1
                    # Real LP data simulation is deferred to phase 2+
                    "voltageL1": 220.0,
                    "voltageL2": 220.0,
                    "voltageL3": 220.0,
                    "currentL1": 5.0,
                    "currentL2": 5.0,
                    "currentL3": 5.0,
                    "powerFactor": 0.95,
                    "activePower": 3300.0,
                    "reactivePower": 1080.0,
                }
            }
        }

        return payload

    def _format_iso8601(self, dt: datetime) -> str:
        """Format a datetime as ISO 8601 string with 'Z' suffix.

        Args:
            dt: The datetime to format. Should be timezone-aware.

        Returns:
            ISO 8601 formatted string with 'Z' suffix, e.g., "2026-03-09T14:00:00Z"

        """
        # Convert to UTC if not already
        if dt.tzinfo is not None:
            dt = dt.astimezone(timezone.utc)

        # Format as ISO 8601 with 'Z' suffix
        return dt.strftime("%Y-%m-%dT%H:%M:%SZ")
