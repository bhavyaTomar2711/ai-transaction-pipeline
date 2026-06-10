"""
LLM Summarizer — generates a narrative summary of processed transactions.

Produces:
- Total spend by currency (INR, USD)
- Top 3 merchants by spend
- Anomaly count
- 2-3 sentence spending narrative
- Risk level (low/medium/high)
- Category breakdown
"""
import json
import time
import logging
import re
from typing import List, Dict, Optional
from decimal import Decimal
from collections import defaultdict

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


def _compute_stats(transactions: List[Dict]) -> Dict:
    """Compute spending statistics from cleaned transactions."""
    total_inr = Decimal("0")
    total_usd = Decimal("0")
    merchant_totals = defaultdict(lambda: Decimal("0"))
    category_totals = defaultdict(lambda: Decimal("0"))
    anomaly_count = 0

    for txn in transactions:
        amount = txn.get("amount")
        if amount is None:
            continue

        amount = Decimal(str(amount))
        currency = txn.get("currency", "INR").upper()

        if currency == "USD":
            total_usd += amount
        else:
            total_inr += amount

        merchant = txn.get("merchant", "Unknown")
        merchant_totals[merchant] += amount

        category = txn.get("category", "Uncategorised")
        category_totals[category] += amount

        if txn.get("is_anomaly"):
            anomaly_count += 1

    # Top 3 merchants
    sorted_merchants = sorted(
        merchant_totals.items(), key=lambda x: x[1], reverse=True
    )[:3]
    top_merchants = [
        {"name": name, "total": float(total)}
        for name, total in sorted_merchants
    ]

    # Category breakdown
    category_breakdown = {
        cat: float(total)
        for cat, total in sorted(category_totals.items(), key=lambda x: x[1], reverse=True)
    }

    # Risk level
    total_txns = len(transactions)
    anomaly_ratio = anomaly_count / total_txns if total_txns > 0 else 0
    if anomaly_ratio > 0.2:
        risk_level = "high"
    elif anomaly_ratio > 0.1:
        risk_level = "medium"
    else:
        risk_level = "low"

    return {
        "total_spend_inr": float(total_inr),
        "total_spend_usd": float(total_usd),
        "top_merchants": top_merchants,
        "anomaly_count": anomaly_count,
        "category_breakdown": category_breakdown,
        "risk_level": risk_level,
        "total_transactions": total_txns,
    }


def _generate_fallback_narrative(stats: Dict) -> str:
    """Generate a narrative summary without LLM."""
    parts = []
    parts.append(
        f"Analysis of {stats['total_transactions']} transactions reveals "
        f"total spending of ₹{stats['total_spend_inr']:,.2f} INR"
    )
    if stats['total_spend_usd'] > 0:
        parts[0] += f" and ${stats['total_spend_usd']:,.2f} USD"
    parts[0] += "."

    if stats['top_merchants']:
        top_names = [m['name'] for m in stats['top_merchants'][:3]]
        parts.append(
            f"Top merchants by spend are {', '.join(top_names)}."
        )

    if stats['anomaly_count'] > 0:
        parts.append(
            f"{stats['anomaly_count']} transactions were flagged as anomalous, "
            f"resulting in a {stats['risk_level']} risk assessment."
        )
    else:
        parts.append("No anomalies were detected; overall risk is low.")

    return " ".join(parts)


def _build_summary_prompt(stats: Dict, transactions: List[Dict]) -> str:
    """Build prompt for LLM narrative summary."""
    anomaly_examples = [
        f"- {t.get('merchant', '?')}: {t.get('amount', 0)} {t.get('currency', '?')} — {t.get('anomaly_reason', '')}"
        for t in transactions if t.get("is_anomaly")
    ][:5]  # Limit to 5 examples

    return f"""You are a financial analyst. Generate a JSON summary for these transaction statistics.

Stats:
- Total INR spend: ₹{stats['total_spend_inr']:,.2f}
- Total USD spend: ${stats['total_spend_usd']:,.2f}
- Total transactions: {stats['total_transactions']}
- Anomalies detected: {stats['anomaly_count']}
- Top merchants: {json.dumps(stats['top_merchants'])}
- Category breakdown: {json.dumps(stats['category_breakdown'])}

Sample anomalies:
{chr(10).join(anomaly_examples) if anomaly_examples else "None"}

Respond with ONLY a JSON object with these fields:
- "narrative": A 2-3 sentence professional spending narrative
- "risk_level": "low", "medium", or "high"

No markdown, no explanation, just the JSON object."""


def generate_summary(transactions: List[Dict]) -> Dict:
    """
    Generate a complete job summary with statistics and narrative.
    Uses LLM for narrative if available, otherwise generates locally.
    """
    stats = _compute_stats(transactions)

    # Try LLM for narrative
    narrative = None
    risk_level = stats["risk_level"]

    if settings.GEMINI_API_KEY:
        try:
            import google.generativeai as genai
            genai.configure(api_key=settings.GEMINI_API_KEY)
            model = genai.GenerativeModel("gemini-1.5-flash")

            prompt = _build_summary_prompt(stats, transactions)

            for attempt in range(settings.LLM_MAX_RETRIES):
                try:
                    response = model.generate_content(prompt)
                    raw_text = response.text

                    # Parse JSON from response
                    json_match = re.search(r'\{.*\}', raw_text, re.DOTALL)
                    if json_match:
                        result = json.loads(json_match.group())
                        narrative = result.get("narrative")
                        llm_risk = result.get("risk_level", "").lower()
                        if llm_risk in ("low", "medium", "high"):
                            risk_level = llm_risk
                        break

                except Exception as e:
                    delay = settings.LLM_RETRY_BASE_DELAY * (2 ** attempt)
                    logger.warning(
                        f"LLM summary call failed (attempt {attempt+1}): {e}. "
                        f"Retrying in {delay}s..."
                    )
                    time.sleep(delay)

        except Exception as e:
            logger.error(f"Failed to initialize Gemini for summary: {e}")

    # Fallback narrative
    if not narrative:
        narrative = _generate_fallback_narrative(stats)

    return {
        "total_spend_inr": stats["total_spend_inr"],
        "total_spend_usd": stats["total_spend_usd"],
        "top_merchants": stats["top_merchants"],
        "anomaly_count": stats["anomaly_count"],
        "narrative": narrative,
        "risk_level": risk_level,
        "category_breakdown": stats["category_breakdown"],
    }
