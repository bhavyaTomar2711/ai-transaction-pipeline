from pydantic_settings import BaseSettings
from functools import lru_cache
from typing import List


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    DATABASE_URL: str = "postgresql://postgres:postgres@postgres:5432/transactions_db"
    REDIS_URL: str = "redis://redis:6379/0"
    GROQ_API_KEY: str = ""

    UPLOAD_DIR: str = "uploads"

    # LLM settings
    LLM_BATCH_SIZE: int = 10
    LLM_MAX_RETRIES: int = 3
    LLM_RETRY_BASE_DELAY: float = 2.0  # seconds, exponential backoff base

    # Anomaly detection
    ANOMALY_MULTIPLIER: float = 3.0
    DOMESTIC_MERCHANTS: List[str] = [
        "Swiggy", "Ola", "IRCTC", "Flipkart", "Jio Recharge",
        "HDFC ATM", "Zomato", "PhonePe", "Paytm", "BigBasket",
        "Dunzo", "Myntra", "Nykaa", "Cred"
    ]

    # Valid LLM categories
    VALID_CATEGORIES: List[str] = [
        "Food", "Shopping", "Travel", "Transport", "Utilities",
        "Cash Withdrawal", "Entertainment", "Other"
    ]

    class Config:
        env_file = ".env"
        extra = "allow"


@lru_cache()
def get_settings() -> Settings:
    return Settings()
