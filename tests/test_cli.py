"""
CLI tests for MQTT load generator.

Tests the Click-based CLI interface including command parsing,
configuration validation, and error handling.
"""

from click.testing import CliRunner
from loadgen.cli import cli
import pytest


def test_cli_group_exists():
    """Test that CLI group exists and shows help."""
    runner = CliRunner()
    result = runner.invoke(cli, ['--help'])
    assert result.exit_code == 0
    assert 'Python MQTT Load Generator' in result.output


def test_run_command_help():
    """Test that run command shows help."""
    runner = CliRunner()
    result = runner.invoke(cli, ['run', '--help'])
    assert result.exit_code == 0
    assert 'SCENARIO' in result.output
    assert 'Run benchmark scenario' in result.output


def test_run_dry_run_validates_config(tmp_path):
    """Test dry-run mode validates configuration without running benchmark."""
    # Create minimal valid config
    config_file = tmp_path / "test.yaml"
    config_file.write_text("""
name: test
message_count: 10
worker_count: 2
rate_limit: 100
qos: 1
broker:
  host: localhost
  port: 1883
mqtt:
  topic: meter/loadProfile
payload:
  dcu_id: DCU-001
  meter_id_source: Asset-Meter.csv
""")

    runner = CliRunner()
    result = runner.invoke(cli, ['run', '--dry-run', str(config_file)])
    assert result.exit_code == 0
    assert 'Configuration validated successfully' in result.output


def test_run_invalid_config_file(tmp_path):
    """Test that invalid YAML configuration shows error."""
    config_file = tmp_path / "invalid.yaml"
    config_file.write_text("invalid: yaml: content:")

    runner = CliRunner()
    result = runner.invoke(cli, ['run', str(config_file)])
    assert result.exit_code != 0
    assert 'Error loading configuration' in result.output


def test_run_missing_scenario_file():
    """Test that missing scenario file shows appropriate error."""
    runner = CliRunner()
    result = runner.invoke(cli, ['run', 'nonexistent.yaml'])
    assert result.exit_code != 0
    assert 'does not exist' in result.output or 'not found' in result.output


def test_run_missing_csv_file(tmp_path):
    """Test that missing CSV file shows appropriate error."""
    config_file = tmp_path / "test.yaml"
    config_file.write_text("""
name: test
message_count: 10
worker_count: 2
rate_limit: 100
qos: 1
broker:
  host: localhost
  port: 1883
mqtt:
  topic: meter/loadProfile
payload:
  dcu_id: DCU-001
  meter_id_source: nonexistent.csv
""")

    runner = CliRunner()
    result = runner.invoke(cli, ['run', str(config_file)])
    assert result.exit_code != 0
    # Error can be either during config validation or CSV loading
    assert ('Error loading configuration' in result.output or
            'Error loading meter IDs' in result.output)
