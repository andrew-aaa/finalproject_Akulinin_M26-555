import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import ClassVar

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[2]

load_dotenv(PROJECT_ROOT / ".env")


@dataclass(frozen=True)
class ParserConfig:
    """Настройки API-клиентов и хранения курсов"""

    EXCHANGERATE_API_KEY: str | None = field(
        default_factory=lambda: os.getenv("EXCHANGERATE_API_KEY")
    )
    COINGECKO_URL: ClassVar[str] = "https://api.coingecko.com/api/v3/simple/price"
    EXCHANGERATE_API_URL: ClassVar[str] = "https://v6.exchangerate-api.com/v6"

    BASE_CURRENCY: ClassVar[str] = "USD"
    FIAT_CURRENCIES: ClassVar[tuple[str, ...]] = ("EUR", "GBP", "RUB")
    CRYPTO_CURRENCIES: ClassVar[tuple[str, ...]] = ("BTC", "ETH", "SOL")

    CRYPTO_ID_MAP: ClassVar[dict[str, str]] = {
        "BTC": "bitcoin",
        "ETH": "ethereum",
        "SOL": "solana",
    }

    RATES_FILE_PATH: Path = field(
        default_factory=lambda: PROJECT_ROOT / "data" / "rates.json"
    )
    HISTORY_FILE_PATH: Path = field(
        default_factory=lambda: PROJECT_ROOT / "data" / "exchange_rates.json"
    )

    REQUEST_TIMEOUT: ClassVar[int] = 10
