"""
Test stubs for CSV loader module (INPUT-01).

These tests verify CSV loading, validation, and deduplication functionality.
"""

import pytest
from pathlib import Path

# Import the module to test (will fail until implemented)
# from loadgen.csv_reader import load_meter_ids, MeterIdValidationError


def test_load_meter_ids_from_csv_valid(sample_csv_file):
    """Test loading valid CSV returns list of meter IDs."""
    from loadgen.csv_reader import load_meter_ids

    result = load_meter_ids(str(sample_csv_file))
    expected = ["000000000049", "000000000050", "000000000051", "000000000052", "000000000053"]
    assert result == expected
    assert isinstance(result, list)
    assert all(isinstance(id, str) for id in result)


def test_load_meter_ids_deduplicates(csv_with_duplicates):
    """Test duplicate meter IDs are removed."""
    from loadgen.csv_reader import load_meter_ids

    result = load_meter_ids(str(csv_with_duplicates))
    # CSV has 6 entries (3 unique IDs, each duplicated twice)
    assert len(result) == 3
    assert sorted(result) == sorted(["000000000049", "000000000050", "000000000051"])


def test_load_meter_ids_skips_invalid_rows(csv_with_invalid_rows):
    """Test rows with missing/invalid meter_id are skipped."""
    from loadgen.csv_reader import load_meter_ids

    result = load_meter_ids(str(csv_with_invalid_rows))
    # CSV has 7 rows, but only 3 valid meter IDs
    assert len(result) == 3
    assert result == ["000000000049", "000000000050", "000000000051"]


def test_load_meter_ids_validates_format():
    """Test 12-character format validation."""
    from loadgen.csv_reader import load_meter_ids
    import tempfile

    # Create CSV with invalid format IDs
    with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
        f.write("meter_id\n")
        f.write("123\n")  # Too short
        f.write("000000000000000000049\n")  # Too long
        f.write("000000000049\n")  # Valid (12 characters)
        csv_path = f.name

    result = load_meter_ids(csv_path)
    assert result == ["000000000049"]
    assert len(result) == 1


def test_load_meter_ids_validates_non_empty():
    """Test non-empty validation for meter_id."""
    from loadgen.csv_reader import load_meter_ids
    import tempfile

    # Create CSV with empty meter_id
    with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
        f.write("meter_id\n")
        f.write("\n")  # Empty
        f.write("000000000049\n")  # Valid
        csv_path = f.name

    result = load_meter_ids(csv_path)
    assert result == ["000000000049"]


def test_load_meter_ids_strips_whitespace():
    """Test whitespace is stripped from meter_id."""
    from loadgen.csv_reader import load_meter_ids
    import tempfile

    # Create CSV with whitespace
    with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
        f.write("meter_id\n")
        f.write(" 000000000049 \n")
        f.write("000000000050\n")
        f.write(" 000000000051\n")
        csv_path = f.name

    result = load_meter_ids(csv_path)
    assert result == ["000000000049", "000000000050", "000000000051"]


def test_load_meter_ids_case_insensitive_column():
    """Test meter_id column is found case-insensitively."""
    from loadgen.csv_reader import load_meter_ids
    import tempfile

    # Create CSV with uppercase column name
    with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
        f.write("METER_ID\n")
        f.write("000000000049\n")
        f.write("000000000050\n")
        csv_path = f.name

    result = load_meter_ids(csv_path)
    assert result == ["000000000049", "000000000050"]


def test_load_meter_ids_missing_column_raises_error(csv_missing_meter_column):
    """Test missing meter_id column raises clear error."""
    from loadgen.csv_reader import load_meter_ids
    from loadgen.csv_reader import MeterIdValidationError

    with pytest.raises(MeterIdValidationError) as exc_info:
        load_meter_ids(str(csv_missing_meter_column))

    assert "meter_id" in str(exc_info.value).lower()
