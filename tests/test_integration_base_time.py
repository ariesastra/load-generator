"""
Integration tests for base_time functionality.

This module tests the end-to-end flow of base_time from YAML config
through to generated payloads.
"""

import pytest
from pathlib import Path
from datetime import datetime, timezone

from loadgen.config import load_config, PayloadConfig
from loadgen.publisher import Publisher
from loadgen.payload import PayloadFactory
from loadgen.slot_planner import SlotPlanner


class TestBaseTimeIntegration:
    """Integration tests for base_time feature."""

    def test_yaml_to_config_to_datetime_flow(self, tmp_path, sample_csv_file):
        """Test flow: YAML -> PayloadConfig -> datetime."""
        # Create test YAML with base_time
        config_yaml = tmp_path / "base_time_test.yaml"
        config_content = f"""name: test_scenario
message_count: 1000
rate_limit: 100

payload:
  dcu_id: DCU-999
  meter_id_source: {sample_csv_file}
  base_time: "2026-03-11T00:00:00Z"
"""
        config_yaml.write_text(config_content)

        # Load config
        config = load_config(config_yaml)

        # Verify base_time string
        assert config.payload.base_time == "2026-03-11T00:00:00Z"

        # Verify conversion to datetime
        dt = config.payload.get_base_time_datetime()
        assert dt is not None
        assert dt.year == 2026
        assert dt.month == 3
        assert dt.day == 11
        assert dt.hour == 0
        assert dt.minute == 0
        assert dt.second == 0
        assert dt.tzinfo == timezone.utc

    def test_config_to_publisher_to_payload_factory_flow(self):
        """Test flow: PayloadConfig -> Publisher -> PayloadFactory."""
        base_time = datetime(2026, 3, 11, 0, 0, 0, tzinfo=timezone.utc)

        # Create Publisher with base_time
        publisher = Publisher(
            broker_config={
                "host": "localhost",
                "port": 1883,
                "qos": 1,
                "tls_enabled": False,
            },
            worker_count=2,
            message_count=10,
            meter_ids=["000000000001", "000000000002"],
            base_time=base_time,
        )

        # Verify base_time stored in Publisher
        assert publisher._base_time == base_time

        # Verify PayloadFactory has base_time
        # SlotPlanner inside PayloadFactory should use the base_time
        assert publisher._payload_factory._slot_planner.base_time == base_time.replace(second=0, microsecond=0)

    def test_payload_factory_uses_custom_base_time(self):
        """Test that PayloadFactory generates payloads with custom base_time."""
        base_time = datetime(2026, 3, 11, 0, 0, 0, tzinfo=timezone.utc)

        # Create PayloadFactory with custom base_time
        factory = PayloadFactory(dcu_id="DCU-TEST", base_time=base_time)

        # Generate payload at slot 0
        payload = factory.generate_payload(meter_id="000000000001", slot_index=0)

        # Verify sampling_time uses custom base_time
        sampling_time = payload["operationResult"]["samplingTime"]
        assert sampling_time == "2026-03-11T00:00:00Z"

        # Generate payload at slot 1 (15 minutes later)
        payload = factory.generate_payload(meter_id="000000000001", slot_index=1)
        sampling_time = payload["operationResult"]["samplingTime"]
        assert sampling_time == "2026-03-11T00:15:00Z"

    def test_slot_planner_with_custom_base_time(self):
        """Test that SlotPlanner uses custom base_time."""
        base_time = datetime(2026, 3, 11, 14, 7, 0, tzinfo=timezone.utc)

        # Create SlotPlanner with custom base_time
        planner = SlotPlanner(base_time=base_time)

        # Slot 0 should be rounded to nearest 15-min boundary
        slot_0 = planner.assign_slot(0)
        assert slot_0 == "2026-03-11T14:00:00Z"

        # Slot 1 should be 15 minutes later
        slot_1 = planner.assign_slot(1)
        assert slot_1 == "2026-03-11T14:15:00Z"

    def test_backward_compatibility_none_base_time(self):
        """Test that None base_time works (backward compatible)."""
        # Create PayloadFactory without base_time
        factory = PayloadFactory(dcu_id="DCU-TEST")

        # Generate payload
        payload = factory.generate_payload(meter_id="000000000001", slot_index=0)

        # Verify sampling_time is generated (should use current time)
        sampling_time = payload["operationResult"]["samplingTime"]
        assert sampling_time is not None
        # Should be a valid ISO 8601 string
        assert "T" in sampling_time
        assert "Z" in sampling_time

    def test_config_without_base_time_backward_compatible(self, tmp_path, sample_csv_file):
        """Test that config without base_time works (backward compatible)."""
        # Create test YAML without base_time
        config_yaml = tmp_path / "no_base_time_test.yaml"
        config_content = f"""name: test_scenario
message_count: 1000
rate_limit: 100

payload:
  dcu_id: DCU-999
  meter_id_source: {sample_csv_file}
"""
        config_yaml.write_text(config_content)

        # Load config
        config = load_config(config_yaml)

        # Verify base_time is None
        assert config.payload.base_time is None

        # Verify get_base_time_datetime returns None
        dt = config.payload.get_base_time_datetime()
        assert dt is None

    @pytest.mark.asyncio
    async def test_end_to_end_with_yaml_scenario(self, tmp_path, sample_csv_file):
        """Test end-to-end flow: YAML -> Publisher -> Generated payloads."""
        # Create test YAML with base_time
        config_yaml = tmp_path / "e2e_test.yaml"
        config_content = f"""name: e2e_test
message_count: 5
worker_count: 1
rate_limit: 100

payload:
  dcu_id: DCU-E2E
  meter_id_source: {sample_csv_file}
  base_time: "2026-03-11T12:00:00Z"
"""
        config_yaml.write_text(config_content)

        # Load config
        config = load_config(config_yaml)

        # Extract base_time
        base_time = config.payload.get_base_time_datetime()

        # Create Publisher
        publisher = Publisher(
            broker_config={
                "host": "localhost",
                "port": 1883,
                "qos": 1,
                "tls_enabled": False,
            },
            worker_count=1,
            message_count=5,
            meter_ids=["000000000049"],
            base_time=base_time,
        )

        # Generate payloads
        payloads = await publisher._generate_payloads()

        # Verify payloads use custom base_time
        assert len(payloads) == 5

        # First payload should have sampling_time at base_time (slot 0)
        assert payloads[0]["operationResult"]["samplingTime"] == "2026-03-11T12:00:00Z"

        # Second payload should be 15 minutes later
        assert payloads[1]["operationResult"]["samplingTime"] == "2026-03-11T12:15:00Z"

        # Third payload should be 30 minutes later
        assert payloads[2]["operationResult"]["samplingTime"] == "2026-03-11T12:30:00Z"
