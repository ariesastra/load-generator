"""
Tests for configuration loading and validation.

This module tests the configuration data classes and YAML loader,
including validation of all fields and error handling.
"""

import pytest
from pathlib import Path
from datetime import datetime, timezone

from loadgen.config import (
    load_config,
    ScenarioConfig,
    BrokerConfig,
    MqttConfig,
    PayloadConfig,
    ConfigValidationError,
)


class TestValidConfig:
    """Tests for valid configuration loading."""

    def test_valid_yaml_loads_successfully(self, tmp_path, sample_csv_file):
        """Test that a valid YAML configuration loads successfully."""
        config_yaml = tmp_path / "valid_config.yaml"
        config_content = f"""name: test_scenario
description: Test scenario for load generator
message_count: 1000
worker_count: 4
rate_limit: 100
qos: 1

broker:
  host: test.example.com
  port: 8883
  tls: true
  username: testuser
  password: testpass

mqtt:
  topic: custom/topic
  qos: 2

payload:
  dcu_id: DCU-999
  meter_id_source: {sample_csv_file}
"""
        config_yaml.write_text(config_content)

        # Load and verify
        config = load_config(config_yaml)

        assert config.name == "test_scenario"
        assert config.description == "Test scenario for load generator"
        assert config.message_count == 1000
        assert config.worker_count == 4
        assert config.rate_limit == 100
        assert config.qos == 1

        # Verify broker config
        assert config.broker.host == "test.example.com"
        assert config.broker.port == 8883
        assert config.broker.tls is True
        assert config.broker.username == "testuser"
        assert config.broker.password == "testpass"

        # Verify MQTT config
        assert config.mqtt.topic == "custom/topic"
        assert config.mqtt.qos == 2

        # Verify payload config
        assert config.payload.dcu_id == "DCU-999"
        assert config.payload.meter_id_source == str(sample_csv_file)

    def test_minimal_config_with_defaults(self, tmp_path):
        """Test that minimal YAML gets proper default values."""
        config_yaml = tmp_path / "minimal_config.yaml"
        config_content = """name: minimal_scenario
message_count: 500
rate_limit: 50
"""
        config_yaml.write_text(config_content)

        # Load and verify defaults
        config = load_config(config_yaml)

        assert config.name == "minimal_scenario"
        assert config.message_count == 500
        assert config.worker_count == 4  # Default
        assert config.rate_limit == 50
        assert config.qos == 1  # Default
        assert config.description is None  # Optional

        # Verify broker defaults
        assert config.broker.host == "localhost"  # Default
        assert config.broker.port == 1883  # Default
        assert config.broker.tls is False  # Default
        assert config.broker.username is None  # Default
        assert config.broker.password is None  # Default

        # Verify MQTT defaults
        assert config.mqtt.topic == "meter/loadProfile"  # Default
        assert config.mqtt.qos == 1  # Default

        # Verify payload defaults
        assert config.payload.dcu_id == "DCU-001"  # Default
        assert config.payload.meter_id_source is None  # Optional


class TestValidationErrors:
    """Tests for configuration validation errors."""

    def test_missing_required_field_message_count(self, tmp_path):
        """Test that missing message_count raises ConfigValidationError."""
        config_yaml = tmp_path / "no_message_count.yaml"
        config_content = """name: test_scenario
rate_limit: 100
"""
        config_yaml.write_text(config_content)

        with pytest.raises(ConfigValidationError) as exc_info:
            load_config(config_yaml)

        assert "Missing required field: message_count" in str(exc_info.value)

    def test_missing_required_field_rate_limit(self, tmp_path):
        """Test that missing rate_limit raises ConfigValidationError."""
        config_yaml = tmp_path / "no_rate_limit.yaml"
        config_content = """name: test_scenario
message_count: 1000
"""
        config_yaml.write_text(config_content)

        with pytest.raises(ConfigValidationError) as exc_info:
            load_config(config_yaml)

        assert "Missing required field: rate_limit" in str(exc_info.value)

    def test_missing_required_field_name(self, tmp_path):
        """Test that missing name raises ConfigValidationError."""
        config_yaml = tmp_path / "no_name.yaml"
        config_content = """message_count: 1000
rate_limit: 100
"""
        config_yaml.write_text(config_content)

        with pytest.raises(ConfigValidationError) as exc_info:
            load_config(config_yaml)

        assert "Missing required field: name" in str(exc_info.value)

    def test_invalid_qos_value_3(self, tmp_path):
        """Test that invalid QoS (3) raises ConfigValidationError."""
        config_yaml = tmp_path / "invalid_qos.yaml"
        config_content = """name: test_scenario
message_count: 1000
rate_limit: 100
qos: 3
"""
        config_yaml.write_text(config_content)

        with pytest.raises(ConfigValidationError) as exc_info:
            load_config(config_yaml)

        assert "Invalid QoS: 3" in str(exc_info.value)
        assert "must be 0, 1, or 2" in str(exc_info.value)

    def test_invalid_qos_value_negative(self, tmp_path):
        """Test that negative QoS raises ConfigValidationError."""
        config_yaml = tmp_path / "negative_qos.yaml"
        config_content = """name: test_scenario
message_count: 1000
rate_limit: 100
qos: -1
"""
        config_yaml.write_text(config_content)

        with pytest.raises(ConfigValidationError) as exc_info:
            load_config(config_yaml)

        assert "Invalid QoS: -1" in str(exc_info.value)

    def test_negative_message_count(self, tmp_path):
        """Test that negative message_count raises ConfigValidationError."""
        config_yaml = tmp_path / "negative_count.yaml"
        config_content = """name: test_scenario
message_count: -100
rate_limit: 100
"""
        config_yaml.write_text(config_content)

        with pytest.raises(ConfigValidationError) as exc_info:
            load_config(config_yaml)

        assert "Invalid message_count: -100" in str(exc_info.value)
        assert "must be a positive integer" in str(exc_info.value)

    def test_negative_rate_limit(self, tmp_path):
        """Test that negative rate_limit raises ConfigValidationError."""
        config_yaml = tmp_path / "negative_rate.yaml"
        config_content = """name: test_scenario
message_count: 1000
rate_limit: -50
"""
        config_yaml.write_text(config_content)

        with pytest.raises(ConfigValidationError) as exc_info:
            load_config(config_yaml)

        assert "Invalid rate_limit: -50" in str(exc_info.value)
        assert "must be a positive integer" in str(exc_info.value)

    def test_negative_worker_count(self, tmp_path):
        """Test that negative worker_count raises ConfigValidationError."""
        config_yaml = tmp_path / "negative_workers.yaml"
        config_content = """name: test_scenario
message_count: 1000
rate_limit: 100
worker_count: -2
"""
        config_yaml.write_text(config_content)

        with pytest.raises(ConfigValidationError) as exc_info:
            load_config(config_yaml)

        assert "Invalid worker_count: -2" in str(exc_info.value)
        assert "must be a positive integer" in str(exc_info.value)

    def test_nonexistent_meter_id_source(self, tmp_path):
        """Test that non-existent meter_id_source raises ConfigValidationError."""
        config_yaml = tmp_path / "bad_csv.yaml"
        config_content = """name: test_scenario
message_count: 1000
rate_limit: 100

payload:
  meter_id_source: /nonexistent/path/to/meters.csv
"""
        config_yaml.write_text(config_content)

        with pytest.raises(ConfigValidationError) as exc_info:
            load_config(config_yaml)

        assert "Meter ID source file not found" in str(exc_info.value)
        assert "/nonexistent/path/to/meters.csv" in str(exc_info.value)

    def test_invalid_yaml_syntax(self, tmp_path):
        """Test that invalid YAML syntax raises ConfigValidationError."""
        config_yaml = tmp_path / "invalid_yaml.yaml"
        config_content = """name: test_scenario
message_count: 1000
rate_limit: 100
broker:
  host: [unclosed list
"""
        config_yaml.write_text(config_content)

        with pytest.raises(ConfigValidationError) as exc_info:
            load_config(config_yaml)

        assert "Invalid YAML syntax" in str(exc_info.value)

    def test_missing_broker_section_invalid(self, tmp_path):
        """Test that non-dict broker section raises ConfigValidationError."""
        config_yaml = tmp_path / "bad_broker.yaml"
        config_content = """name: test_scenario
message_count: 1000
rate_limit: 100
broker: "invalid"
"""
        config_yaml.write_text(config_content)

        with pytest.raises(ConfigValidationError) as exc_info:
            load_config(config_yaml)

        assert "Invalid broker section" in str(exc_info.value)

    def test_invalid_port_string(self, tmp_path):
        """Test that string port raises ConfigValidationError."""
        config_yaml = tmp_path / "string_port.yaml"
        config_content = """name: test_scenario
message_count: 1000
rate_limit: 100

broker:
  port: "not-a-number"
"""
        config_yaml.write_text(config_content)

        with pytest.raises(ConfigValidationError) as exc_info:
            load_config(config_yaml)

        # The error will be about invalid integer conversion
        assert "invalid" in str(exc_info.value).lower()

    def test_empty_broker_host(self, tmp_path):
        """Test that empty broker host raises ConfigValidationError."""
        config_yaml = tmp_path / "empty_host.yaml"
        config_content = """name: test_scenario
message_count: 1000
rate_limit: 100

broker:
  host: ""
"""
        config_yaml.write_text(config_content)

        with pytest.raises(ConfigValidationError) as exc_info:
            load_config(config_yaml)

        assert "Invalid host" in str(exc_info.value)


class TestTypeConversion:
    """Tests for YAML type conversion."""

    def test_yaml_string_to_int_conversion(self, tmp_path):
        """Test that YAML string numbers convert to integers."""
        config_yaml = tmp_path / "string_numbers.yaml"
        config_content = """name: test_scenario
message_count: "1000"
rate_limit: "100"
worker_count: "4"
"""
        config_yaml.write_text(config_content)

        # YAML should parse strings as strings, but we expect ints
        # This test verifies the behavior when YAML provides strings
        with pytest.raises(ConfigValidationError):
            load_config(config_yaml)

    def test_yaml_bool_conversion(self, tmp_path):
        """Test that YAML boolean values parse correctly."""
        config_yaml = tmp_path / "bool_test.yaml"
        config_content = """name: test_scenario
message_count: 1000
rate_limit: 100

broker:
  tls: true
"""
        config_yaml.write_text(config_content)

        config = load_config(config_yaml)
        assert config.broker.tls is True

    def test_tls_auto_port_8883(self, tmp_path):
        """Test that TLS with default port auto-sets to 8883."""
        config_yaml = tmp_path / "tls_auto_port.yaml"
        config_content = """name: test_scenario
message_count: 1000
rate_limit: 100

broker:
  tls: true
"""
        config_yaml.write_text(config_content)

        config = load_config(config_yaml)
        # When tls=true and port is default (1883), it should auto-set to 8883
        assert config.broker.tls is True
        assert config.broker.port == 8883


class TestFileErrors:
    """Tests for file-related errors."""

    def test_file_not_found(self, tmp_path):
        """Test that missing config file raises FileNotFoundError."""
        nonexistent = tmp_path / "does_not_exist.yaml"

        with pytest.raises(FileNotFoundError) as exc_info:
            load_config(nonexistent)

        assert "Configuration file not found" in str(exc_info.value)

    def test_empty_config_file(self, tmp_path):
        """Test that empty config file raises ConfigValidationError."""
        config_yaml = tmp_path / "empty.yaml"
        config_yaml.write_text("")

        with pytest.raises(ConfigValidationError) as exc_info:
            load_config(config_yaml)

        assert "empty" in str(exc_info.value).lower()


class TestBaseTime:
    """Tests for base_time field in PayloadConfig."""

    def test_payload_config_with_base_time(self, tmp_path, sample_csv_file):
        """Test that PayloadConfig accepts valid ISO 8601 base_time string."""
        config_yaml = tmp_path / "base_time_config.yaml"
        config_content = f"""name: test_scenario
message_count: 1000
rate_limit: 100

payload:
  dcu_id: DCU-999
  meter_id_source: {sample_csv_file}
  base_time: "2026-03-11T00:00:00Z"
"""
        config_yaml.write_text(config_content)

        config = load_config(config_yaml)

        assert config.payload.base_time == "2026-03-11T00:00:00Z"

    def test_payload_config_without_base_time(self, tmp_path, sample_csv_file):
        """Test that PayloadConfig accepts None for base_time (backward compatible)."""
        config_yaml = tmp_path / "no_base_time_config.yaml"
        config_content = f"""name: test_scenario
message_count: 1000
rate_limit: 100

payload:
  dcu_id: DCU-999
  meter_id_source: {sample_csv_file}
"""
        config_yaml.write_text(config_content)

        config = load_config(config_yaml)

        assert config.payload.base_time is None

    def test_payload_config_invalid_base_time_format(self, tmp_path, sample_csv_file):
        """Test that invalid base_time format raises ConfigValidationError."""
        config_yaml = tmp_path / "invalid_base_time.yaml"
        config_content = f"""name: test_scenario
message_count: 1000
rate_limit: 100

payload:
  dcu_id: DCU-999
  meter_id_source: {sample_csv_file}
  base_time: "not-a-datetime"
"""
        config_yaml.write_text(config_content)

        with pytest.raises(ConfigValidationError) as exc_info:
            load_config(config_yaml)

        assert "Invalid base_time format" in str(exc_info.value)

    def test_payload_config_invalid_base_time_type(self, tmp_path, sample_csv_file):
        """Test that non-string base_time raises ConfigValidationError."""
        config_yaml = tmp_path / "invalid_base_time_type.yaml"
        config_content = f"""name: test_scenario
message_count: 1000
rate_limit: 100

payload:
  dcu_id: DCU-999
  meter_id_source: {sample_csv_file}
  base_time: 12345
"""
        config_yaml.write_text(config_content)

        with pytest.raises(ConfigValidationError) as exc_info:
            load_config(config_yaml)

        assert "Invalid base_time" in str(exc_info.value)
        assert "must be a string" in str(exc_info.value)

    def test_get_base_time_datetime_with_z_suffix(self, tmp_path, sample_csv_file):
        """Test that get_base_time_datetime() handles 'Z' suffix correctly."""
        config_yaml = tmp_path / "z_suffix_config.yaml"
        config_content = f"""name: test_scenario
message_count: 1000
rate_limit: 100

payload:
  dcu_id: DCU-999
  meter_id_source: {sample_csv_file}
  base_time: "2026-03-11T00:00:00Z"
"""
        config_yaml.write_text(config_content)

        config = load_config(config_yaml)

        dt = config.payload.get_base_time_datetime()
        assert dt is not None
        assert dt.year == 2026
        assert dt.month == 3
        assert dt.day == 11
        assert dt.hour == 0
        assert dt.minute == 0
        assert dt.second == 0
        assert dt.tzinfo == timezone.utc

    def test_get_base_time_datetime_with_offset(self, tmp_path, sample_csv_file):
        """Test that get_base_time_datetime() handles timezone offset correctly."""
        config_yaml = tmp_path / "offset_config.yaml"
        config_content = f"""name: test_scenario
message_count: 1000
rate_limit: 100

payload:
  dcu_id: DCU-999
  meter_id_source: {sample_csv_file}
  base_time: "2026-03-11T00:00:00+05:00"
"""
        config_yaml.write_text(config_content)

        config = load_config(config_yaml)

        dt = config.payload.get_base_time_datetime()
        assert dt is not None
        # Should be converted to UTC
        assert dt.hour == 19  # 00:00 +05:00 = 19:00 UTC (previous day)
        assert dt.day == 10  # Previous day due to timezone conversion
        assert dt.tzinfo == timezone.utc

    def test_get_base_time_datetime_none(self, tmp_path, sample_csv_file):
        """Test that get_base_time_datetime() returns None when base_time is None."""
        config_yaml = tmp_path / "none_base_time.yaml"
        config_content = f"""name: test_scenario
message_count: 1000
rate_limit: 100

payload:
  dcu_id: DCU-999
  meter_id_source: {sample_csv_file}
"""
        config_yaml.write_text(config_content)

        config = load_config(config_yaml)

        dt = config.payload.get_base_time_datetime()
        assert dt is None

    def test_payload_config_with_base_time_no_timezone(self, tmp_path, sample_csv_file):
        """Test that base_time without timezone defaults to UTC."""
        config_yaml = tmp_path / "no_tz_config.yaml"
        config_content = f"""name: test_scenario
message_count: 1000
rate_limit: 100

payload:
  dcu_id: DCU-999
  meter_id_source: {sample_csv_file}
  base_time: "2026-03-11T00:00:00"
"""
        config_yaml.write_text(config_content)

        config = load_config(config_yaml)

        dt = config.payload.get_base_time_datetime()
        assert dt is not None
        assert dt.tzinfo == timezone.utc  # Should default to UTC
