"""
CSV Parser — validates and parses uploaded CSV files into raw row dicts.
"""
import csv
import io
import logging
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)

REQUIRED_COLUMNS = {
    "txn_id", "date", "merchant", "amount", "currency",
    "status", "category", "account_id", "notes"
}


def validate_csv(file_content: str) -> tuple[bool, Optional[str]]:
    """
    Validate that the CSV content has the required columns.
    Returns (is_valid, error_message).
    """
    try:
        reader = csv.DictReader(io.StringIO(file_content))
        if reader.fieldnames is None:
            return False, "CSV file is empty or has no headers"

        # Normalize header names (strip whitespace, lowercase for comparison)
        headers = {h.strip().lower() for h in reader.fieldnames}
        missing = {col for col in REQUIRED_COLUMNS if col not in headers}

        if missing:
            return False, f"Missing required columns: {', '.join(sorted(missing))}"

        return True, None

    except csv.Error as e:
        return False, f"Invalid CSV format: {str(e)}"
    except Exception as e:
        return False, f"Error reading CSV: {str(e)}"


def parse_csv(file_content: str) -> List[Dict[str, str]]:
    """
    Parse CSV content into a list of dictionaries.
    Each dict represents a raw transaction row with string values.
    """
    rows = []
    reader = csv.DictReader(io.StringIO(file_content))

    for i, row in enumerate(reader):
        # Strip whitespace from keys and values
        cleaned_row = {}
        for key, value in row.items():
            clean_key = key.strip().lower()
            clean_value = value.strip() if value else ""
            cleaned_row[clean_key] = clean_value
        cleaned_row["_row_number"] = i + 2  # +2 for header row + 1-indexed
        rows.append(cleaned_row)

    logger.info(f"Parsed {len(rows)} rows from CSV")
    return rows
