"""
LLM Classifier — uses Groq API to classify uncategorized transactions.

Features:
- Batch processing (10 transactions per call)
- Exponential backoff retry (up to 3 attempts)
- Graceful fallback to rule-based classification when no API key
"""
import json
import time
import logging
import re
from typing import List, Dict, Optional

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

# Rule-based fallback mappings
MERCHANT_CATEGORY_MAP = {
    "swiggy": "Food", "zomato": "Food", "starbucks": "Food",
    "mcdonald's": "Food", "mcdonald": "Food", "bigbasket": "Food",
    "dunzo": "Food",
    "amazon": "Shopping", "flipkart": "Shopping", "myntra": "Shopping",
    "nykaa": "Shopping",
    "makemytrip": "Travel", "irctc": "Travel",
    "uber": "Transport", "ola": "Transport",
    "jio recharge": "Utilities", "phonepe": "Utilities",
    "paytm": "Utilities", "cred": "Utilities",
    "netflix": "Entertainment", "spotify": "Entertainment",
    "hdfc atm": "Cash Withdrawal",
}


def _classify_with_rules(transactions: List[Dict]) -> List[Dict]:
    """
    Fallback rule-based classification using merchant name mapping.
    """
    for txn in transactions:
        if txn.get("category") in (None, "", "Uncategorised"):
            merchant = (txn.get("merchant") or "").lower().strip()
            category = None
            for key, cat in MERCHANT_CATEGORY_MAP.items():
                if key in merchant:
                    category = cat
                    break
            txn["llm_category"] = category or "Other"
            txn["category"] = txn["llm_category"]
            txn["llm_failed"] = False
    return transactions


def _build_classification_prompt(transactions: List[Dict]) -> str:
    """Build the prompt for batch transaction classification."""
    txn_lines = []
    for i, txn in enumerate(transactions):
        txn_lines.append(
            f"{i+1}. merchant=\"{txn.get('merchant', 'Unknown')}\", "
            f"amount={txn.get('amount', 0)}, "
            f"notes=\"{txn.get('notes', '')}\""
        )

    return f"""Classify each transaction into exactly ONE of these categories:
Food, Shopping, Travel, Transport, Utilities, Cash Withdrawal, Entertainment, Other

Transactions:
{chr(10).join(txn_lines)}

Respond with ONLY a JSON array of objects, each with "index" (1-based) and "category".
Example: [{{"index": 1, "category": "Food"}}, {{"index": 2, "category": "Shopping"}}]
No markdown, no explanation, just the JSON array."""


def _parse_llm_response(response_text: str, count: int) -> Optional[List[Dict]]:
    """Parse the LLM response JSON, handling various formatting issues."""
    try:
        # Try to extract JSON from potential markdown code blocks
        json_match = re.search(r'\[.*\]', response_text, re.DOTALL)
        if json_match:
            results = json.loads(json_match.group())
            if isinstance(results, list) and len(results) > 0:
                return results
    except (json.JSONDecodeError, ValueError) as e:
        logger.warning(f"Failed to parse LLM response: {e}")

    return None


def classify_transactions(transactions: List[Dict]) -> List[Dict]:
    """
    Classify uncategorized transactions using LLM or fallback rules.
    Processes in batches with retry logic.
    """
    # Find transactions needing classification
    needs_classification = [
        (i, txn) for i, txn in enumerate(transactions)
        if txn.get("category") in (None, "", "Uncategorised")
    ]

    if not needs_classification:
        logger.info("No transactions need classification")
        return transactions

    logger.info(f"{len(needs_classification)} transactions need classification")

    # Check if Groq API key is available
    if not settings.GROQ_API_KEY:
        logger.info("No Groq API key — using rule-based fallback classification")
        return _classify_with_rules(transactions)

    # Use Groq for classification
    try:
        from groq import Groq
        client = Groq(api_key=settings.GROQ_API_KEY)
    except Exception as e:
        logger.error(f"Failed to initialize Groq: {e}")
        return _classify_with_rules(transactions)

    batch_size = settings.LLM_BATCH_SIZE
    valid_categories = set(settings.VALID_CATEGORIES)

    for batch_start in range(0, len(needs_classification), batch_size):
        batch = needs_classification[batch_start:batch_start + batch_size]
        batch_txns = [txn for _, txn in batch]
        batch_indices = [idx for idx, _ in batch]

        prompt = _build_classification_prompt(batch_txns)
        success = False

        for attempt in range(settings.LLM_MAX_RETRIES):
            try:
                response = client.chat.completions.create(
                    model="llama-3.1-8b-instant",
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.3,
                    max_tokens=1024
                )
                raw_response = response.choices[0].message.content
                parsed = _parse_llm_response(raw_response, len(batch_txns))

                if parsed:
                    # Apply classifications
                    for result in parsed:
                        idx_in_batch = result.get("index", 0) - 1
                        category = result.get("category", "Other")

                        if 0 <= idx_in_batch < len(batch_indices):
                            original_idx = batch_indices[idx_in_batch]
                            if category in valid_categories:
                                transactions[original_idx]["llm_category"] = category
                                transactions[original_idx]["category"] = category
                            else:
                                transactions[original_idx]["llm_category"] = "Other"
                                transactions[original_idx]["category"] = "Other"
                            transactions[original_idx]["llm_raw_response"] = raw_response
                            transactions[original_idx]["llm_failed"] = False

                    success = True
                    break

            except Exception as e:
                delay = settings.LLM_RETRY_BASE_DELAY * (2 ** attempt)
                logger.warning(
                    f"LLM call failed (attempt {attempt+1}/{settings.LLM_MAX_RETRIES}): "
                    f"{e}. Retrying in {delay}s..."
                )
                time.sleep(delay)

        if not success:
            # Mark batch as LLM failed, use rule-based fallback
            logger.error(f"All LLM retries failed for batch starting at {batch_start}")
            for idx in batch_indices:
                merchant = (transactions[idx].get("merchant") or "").lower()
                fallback_cat = "Other"
                for key, cat in MERCHANT_CATEGORY_MAP.items():
                    if key in merchant:
                        fallback_cat = cat
                        break
                transactions[idx]["llm_category"] = fallback_cat
                transactions[idx]["category"] = fallback_cat
                transactions[idx]["llm_failed"] = True

    classified_count = sum(
        1 for _, txn in needs_classification
        if txn.get("llm_category") is not None
    )
    logger.info(f"Classification complete: {classified_count}/{len(needs_classification)} classified")

    return transactions
