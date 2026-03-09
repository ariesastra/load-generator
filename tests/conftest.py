"""
Shared test fixtures for Python MQTT Load Generator tests.

This module provides pytest fixtures used across multiple test files,
including sample CSV data, meter IDs, and test data scenarios.
"""

import pytest
from pathlib import Path
from datetime import datetime, timezone


@pytest.fixture
def sample_csv_file(tmp_path):
    """
    Create a temporary CSV file with valid meter_id column.

    Returns the Path object to the temporary CSV file.
    Format matches Asset-Meter.csv with meter_id column.
    """
    csv_path = tmp_path / "sample_meters.csv"
    csv_content = """meter_id
000000000049
000000000050
000000000051
000000000052
000000000053
"""
    csv_path.write_text(csv_content)
    return csv_path


@pytest.fixture
def sample_meter_ids():
    """
    Return list of test meter IDs.

    These are valid 12-character zero-padded meter IDs
    matching the format in Asset-Meter.csv.
    """
    return ["000000000049", "000000000050", "000000000051"]


@pytest.fixture
def csv_with_duplicates(tmp_path):
    """
    Create a CSV file with duplicate meter IDs.

    Used for testing deduplication logic.
    Contains 6 entries with 3 unique IDs (each duplicated once).
    """
    csv_path = tmp_path / "duplicate_meters.csv"
    csv_content = """meter_id
000000000049
000000000050
000000000051
000000000049
000000000050
000000000051
"""
    csv_path.write_text(csv_content)
    return csv_path


@pytest.fixture
def csv_with_invalid_rows(tmp_path):
    """
    Create a CSV file with missing/invalid meter_id values.

    Used for testing validation and error handling.
    Contains invalid entries: empty, wrong length, non-numeric.
    """
    csv_path = tmp_path / "invalid_meters.csv"
    csv_content = """meter_id
000000000049
000000000050

invalid
123
000000000051
"""
    csv_path.write_text(csv_content)
    return csv_path


@pytest.fixture
def sample_payload_template():
    """
    Return a sample payload template matching python-mqtt-benchmark.md spec.

    This fixture provides the expected structure for LP periodic payloads.
    Used for verifying payload generation correctness.
    """
    return {
        "trxId": "550e8400-e29b-41d4-a716-446655440000",
        "meterId": "000000000049",
        "dcuId": "DCU001",
        "operationType": "meterLoadProfilePeriodic",
        "operationResult": {
            "samplingTime": "2026-03-09T14:00:00Z",
            "collectionTime": "2026-03-09T14:05:00Z",
            "registers": [
                {
                    "registerId": "1.8.0",
                    "value": 123.45,
                    "unit": "kWh"
                }
            ]
        }
    }


@pytest.fixture
def known_base_time():
    """
    Return a known base time for deterministic testing.

    Uses a fixed timestamp that starts at a 15-minute boundary
    for testing slot planner logic.
    """
    return datetime(2026, 3, 9, 14, 0, 0, tzinfo=timezone.utc)


@pytest.fixture
def uniqueness_set():
    """
    Return a set for tracking (meterId, samplingTime) pairs.

    Used for testing uniqueness guarantees in payload generation.
    """
    return set()


@pytest.fixture
def csv_missing_meter_column(tmp_path):
    """
    Create a CSV file without meter_id column.

    Used for testing error handling when required column is missing.
    """
    csv_path = tmp_path / "no_meter_column.csv"
    csv_content = """warehouse_id,warehouse_name,project_id,hes_id,meter_manufacture
WH-PNP,Nusa Penida,pnp,pnp-trilliant,Sanxing
WH-PNP,Nusa Penida,pnp,pnp-trilliant,Sanxing
"""
    csv_path.write_text(csv_content)
    return csv_path
