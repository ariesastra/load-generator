"""
CSV meter ID loader with validation and deduplication.

This module provides functionality to load meter IDs from CSV files
with validation, deduplication, and error handling.
"""

import csv
import logging
from pathlib import Path
from typing import Optional


# Configure logging
logger = logging.getLogger(__name__)


class MeterIdValidationError(Exception):
    """Exception raised when meter_id column is missing from CSV."""

    pass


def load_meter_ids(csv_path: str) -> list[str]:
    """
    Load meter IDs from CSV file with validation and deduplication.

    This function reads a CSV file, extracts the meter_id column,
    validates each meter ID, and returns a deduplicated list of
    valid meter IDs.

    Args:
        csv_path: Path to the CSV file containing meter IDs

    Returns:
        Sorted list of unique, valid meter IDs (12 characters each)

    Raises:
        MeterIdValidationError: If meter_id column is not found in CSV
        FileNotFoundError: If CSV file doesn't exist

    Validation rules:
        - Meter ID must be non-empty after stripping whitespace
        - Meter ID must be exactly 12 characters
        - Invalid rows are skipped silently (logged as warnings)
        - Duplicate meter IDs are removed (logged as info)

    Example:
        >>> meter_ids = load_meter_ids("Asset-Meter.csv")
        >>> print(meter_ids)
        ['000000000049', '000000000050', '000000000051']
    """
    csv_file_path = Path(csv_path)

    # Check if file exists
    if not csv_file_path.exists():
        raise FileNotFoundError(f"CSV file not found: {csv_path}")

    meter_ids: set[str] = set()
    skipped_count = 0
    duplicate_count = 0

    # Find the meter_id column (case-insensitive)
    meter_id_column: Optional[str] = None

    with open(csv_file_path, 'r', encoding='utf-8') as csvfile:
        # Use DictReader for easy column access
        reader = csv.DictReader(csvfile)

        # Check if meter_id column exists
        if not reader.fieldnames:
            raise MeterIdValidationError("CSV file has no columns")

        # Find meter_id column (case-insensitive)
        for column in reader.fieldnames:
            if column.lower() == 'meter_id':
                meter_id_column = column
                break

        if meter_id_column is None:
            available_columns = ', '.join(reader.fieldnames)
            raise MeterIdValidationError(
                f"meter_id column not found in CSV. "
                f"Available columns: {available_columns}"
            )

        # Process each row
        total_rows = 0
        for row_num, row in enumerate(reader, start=2):  # start=2 because row 1 is header
            total_rows += 1

            # Get meter_id value
            raw_value = row.get(meter_id_column, '')

            # Skip if missing
            if raw_value is None:
                logger.debug(f"Row {row_num}: meter_id is missing")
                skipped_count += 1
                continue

            # Strip whitespace
            meter_id = str(raw_value).strip()

            # Skip if empty
            if not meter_id:
                logger.debug(f"Row {row_num}: meter_id is empty")
                skipped_count += 1
                continue

            # Validate length (must be 12 characters)
            if len(meter_id) != 12:
                logger.debug(
                    f"Row {row_num}: meter_id '{meter_id}' has invalid length "
                    f"(got {len(meter_id)}, expected 12)"
                )
                skipped_count += 1
                continue

            # Check for duplicate
            if meter_id in meter_ids:
                logger.debug(f"Row {row_num}: duplicate meter_id '{meter_id}'")
                duplicate_count += 1
                continue

            # Add to set
            meter_ids.add(meter_id)

    # Log summary
    if skipped_count > 0:
        logger.warning(
            f"Skipped {skipped_count} invalid rows from {csv_path}"
        )

    if duplicate_count > 0:
        logger.info(
            f"Removed {duplicate_count} duplicate meter IDs from {csv_path}"
        )

    logger.info(
        f"Loaded {len(meter_ids)} unique meter IDs from {csv_path} "
        f"(processed {total_rows} rows)"
    )

    # Return sorted list for consistent ordering
    return sorted(meter_ids)
