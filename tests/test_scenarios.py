"""
Scenario file validation tests.

This module tests that example scenario files load successfully and have
correct values for the scaling ladder (1k -> 5k -> 10k).
"""

from pathlib import Path

from loadgen import load_config

_SCENARIO_DIR = Path(__file__).parent.parent / "scenarios"


def test_scenario_1k_valid():
    """Test scenario_1k.yaml loads and has correct values."""
    config_path = _SCENARIO_DIR / "scenario_1k.yaml"
    config = load_config(config_path)

    assert config.name == "1k Message Benchmark"
    assert config.message_count == 1000
    assert config.worker_count == 2
    assert config.rate_limit == 100
    assert config.qos == 1
    assert config.broker.host == "localhost"
    assert config.broker.port == 1883
    assert config.mqtt.topic == "meter/loadProfile"
    assert config.payload.dcu_id == "DCU-001"
    assert "Asset-Meter.csv" in config.payload.meter_id_source


def test_scenario_5k_valid():
    """Test scenario_5k.yaml loads and has correct values."""
    config_path = _SCENARIO_DIR / "scenario_5k.yaml"
    config = load_config(config_path)

    assert config.name == "5k Message Benchmark"
    assert config.message_count == 5000
    assert config.worker_count == 4
    assert config.rate_limit == 250
    assert config.qos == 1
    assert config.mqtt.topic == "meter/loadProfile"


def test_scenario_10k_valid():
    """Test scenario_10k.yaml loads and has correct values."""
    config_path = _SCENARIO_DIR / "scenario_10k.yaml"
    config = load_config(config_path)

    assert config.name == "10k Message Benchmark"
    assert config.message_count == 10000
    assert config.worker_count == 8
    assert config.rate_limit == 500
    assert config.qos == 1
    assert config.mqtt.topic == "meter/loadProfile"
