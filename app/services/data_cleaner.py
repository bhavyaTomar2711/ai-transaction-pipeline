"""
Data Cleaner — normalizes raw CSV rows into clean, structured data.

Handles:
- Date format normalization (DD-MM-YYYY, YYYY/MM/DD, etc.) → ISO 8601
- Currency symbol stripping from amounts
- Status/currency uppercasing
- Missing category fill → 'Uncategorised'
- Exact duplicate removal
- Missing txn_id generation
"""
import logging
import uuid
import re
from datetime import datetime
from typing import List, Dict, Optional
from decimal import Decimal, InvalidOperation

logger = logging.getLogger(__name__)

# Date format patterns to try in order
DATE_FORMATS = [
    "%d-%m-%Y",     # DD-MM-YYYY
    "%Y/%m/%d",     # YYYY/MM/DD
    "%Y-%m-%d",     # YYYY-MM-DD (ISO)
    "%d/%m/%Y",     # DD/MM/YYYY
    "%m-%d-%Y",     # MM-DD-YYYY
    "%Y/%d/%m",     # YYYY/DD/MM
    "%m/%d/%Y",     # MM/DD/YYYY
]


def parse_date(date_str: str) -> Optional[datetime]:
    """Try multiple date formats and return parsed datetime or None."""
    if not date_str:
        return None

    date_str = date_str.strip()

    for fmt in DATE_FORMATS:
        try:
            return datetime.strptime(date_str, fmt)
        except ValueError:
            continue

    logger.warning(f"Could not parse date: '{date_str}'")
    return None


def clean_amount(amount_str: str) -> Optional[Decimal]:
    """Strip currency symbols and parse amount to Decimal."""
    if not amount_str:
        return None

    # Remove $, ₹, commas, spaces
    cleaned = re.sub(r'[$₹,\s]', '', amount_str.strip())

    try:
        return Decimal(cleaned)
    except (InvalidOperation, ValueError):
        logger.warning(f"Could not parse amount: '{amount_str}'")
        return None


def normalize_status(status_str: str) -> str:
    """Uppercase and validate status values."""
    if not status_str:
        return "PENDING"
    return status_str.strip().upper()


def normalize_currency(currency_str: str) -> str:
    """Uppercase currency codes."""
    if not currency_str:
        return "INR"
    return currency_str.strip().upper()


def generate_txn_id() -> str:
    """Generate a unique transaction ID for rows missing one."""
    return f"GEN-{uuid.uuid4().hex[:8].upper()}"


def create_dedup_key(row: Dict) -> str:
    """Create a key for exact duplicate detection."""
    return "|".join([
        str(row.get("txn_id", "")),
        str(row.get("date", "")),
        str(row.get("merchant", "")),
        str(row.get("amount", "")),
        str(row.get("currency", "")),
        str(row.get("status", "")),
        str(row.get("category", "")),
        str(row.get("account_id", "")),
        str(row.get("notes", "")),
    ])


def clean_rows(raw_rows: List[Dict[str, str]]) -> List[Dict]:
    """
    Clean and normalize all raw CSV rows.
    Returns list of cleaned row dicts ready for DB insertion.
    """
    cleaned = []
    seen_keys = set()
    duplicates_removed = 0

    for row in raw_rows:
        # --- Duplicate detection (on raw data before cleaning) ---
        dedup_key = create_dedup_key(row)
        if dedup_key in seen_keys:
            duplicates_removed += 1
            continue
        seen_keys.add(dedup_key)

        # --- Clean individual fields ---
        cleaned_row = {
            "txn_id": row.get("txn_id", "").strip() or generate_txn_id(),
            "date": parse_date(row.get("date", "")),
            "merchant": row.get("merchant", "").strip() or None,
            "amount": clean_amount(row.get("amount", "")),
            "currency": normalize_currency(row.get("currency", "")),
            "status": normalize_status(row.get("status", "")),
            "category": row.get("category", "").strip() or "Uncategorised",
            "account_id": row.get("account_id", "").strip() or None,
            "notes": row.get("notes", "").strip() or None,
        }

        cleaned.append(cleaned_row)

    logger.info(
        f"Cleaning complete: {len(raw_rows)} raw → {len(cleaned)} clean "
        f"({duplicates_removed} duplicates removed)"
    )
    return cleaned
