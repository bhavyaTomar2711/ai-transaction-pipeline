"""
Anomaly Detector — flags suspicious transactions based on rules.

Detects:
1. Amount > 3x the account's median (statistical outlier)
2. Currency=USD with domestic-only merchants
3. Notes containing 'SUSPICIOUS' or 'Duplicate?'
"""
import logging
from typing import List, Dict
from decimal import Decimal
from collections import defaultdict
from statistics import median

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


def compute_account_medians(transactions: List[Dict]) -> Dict[str, Decimal]:
    """Compute median transaction amount per account_id."""
    account_amounts = defaultdict(list)

    for txn in transactions:
        if txn.get("account_id") and txn.get("amount") is not None:
            account_amounts[txn["account_id"]].append(float(txn["amount"]))

    medians = {}
    for account_id, amounts in account_amounts.items():
        if amounts:
            medians[account_id] = Decimal(str(median(amounts)))

    return medians


def detect_anomalies(transactions: List[Dict]) -> List[Dict]:
    """
    Flag anomalous transactions. Modifies transactions in-place,
    setting is_anomaly=True and anomaly_reason for flagged rows.
    Returns the modified list.
    """
    # Normalize domestic merchant names for case-insensitive comparison
    domestic_merchants_lower = {m.lower() for m in settings.DOMESTIC_MERCHANTS}
    multiplier = settings.ANOMALY_MULTIPLIER

    # Pre-compute account medians
    account_medians = compute_account_medians(transactions)
    anomaly_count = 0

    for txn in transactions:
        reasons = []

        # Rule 1: Amount exceeds 3x account median
        account_id = txn.get("account_id")
        amount = txn.get("amount")
        if account_id and amount is not None and account_id in account_medians:
            account_median = account_medians[account_id]
            if account_median > 0 and Decimal(str(amount)) > multiplier * account_median:
                reasons.append(
                    f"Amount ({amount}) exceeds {multiplier}x account median "
                    f"({float(account_median):.2f})"
                )

        # Rule 2: USD currency with domestic-only merchant
        currency = txn.get("currency", "").upper()
        merchant = txn.get("merchant", "") or ""
        if currency == "USD" and merchant.lower() in domestic_merchants_lower:
            reasons.append(
                f"Currency mismatch: {merchant} is domestic-only but currency is USD"
            )

        # Rule 3: Suspicious notes
        notes = txn.get("notes", "") or ""
        if "SUSPICIOUS" in notes.upper():
            reasons.append("Flagged as SUSPICIOUS in notes")
        if "Duplicate?" in notes:
            reasons.append("Flagged as potential Duplicate in notes")

        if reasons:
            txn["is_anomaly"] = True
            txn["anomaly_reason"] = " | ".join(reasons)
            anomaly_count += 1
        else:
            txn["is_anomaly"] = False
            txn["anomaly_reason"] = None

    logger.info(f"Anomaly detection complete: {anomaly_count}/{len(transactions)} flagged")
    return transactions
