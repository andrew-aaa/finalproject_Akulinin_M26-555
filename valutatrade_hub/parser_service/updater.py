"""Основной модуль обновления курсов"""

import logging
from datetime import UTC, datetime

from valutatrade_hub.core.exceptions import ApiRequestError
from valutatrade_hub.parser_service.api_clients import (
    CoinGeckoClient,
    ExchangeRateApiClient,
)
from valutatrade_hub.parser_service.config import ParserConfig
from valutatrade_hub.parser_service.storage import RatesStorage

logger = logging.getLogger("valutatrade_hub.parser")


class RatesUpdater:
    """Получает курсы из API и сохраняет их в хранилище"""

    def __init__(
        self,
        config: ParserConfig | None = None,
        storage: RatesStorage | None = None,
    ) -> None:
        self.config = config or ParserConfig()
        self.storage = storage or RatesStorage(self.config)
        self.clients = (
            CoinGeckoClient(self.config),
            ExchangeRateApiClient(self.config),
        )

    def update(self, source: str | None = None) -> dict[str, object]:
        """Обновляет доступные курсы и возвращает результат"""

        available_clients = {
            "coingecko": CoinGeckoClient(self.config),
            "exchangerate": ExchangeRateApiClient(self.config),
        }

        if source is not None:
            source = source.strip().lower()
            if source not in available_clients:
                raise ValueError(
                    "Неизвестный источник. Допустимые значения: coingecko, exchangerate"
                )
            clients = (available_clients[source],)
        else:
            clients = tuple(available_clients.values())

        rates: dict[str, float] = {}
        sources: dict[str, str] = {}
        errors = []

        logger.info("Начато обновление курсов")

        for client in clients:
            try:
                client_rates = client.fetch_rates()
            except ApiRequestError as exc:
                message = str(exc)
                errors.append(message)
                logger.warning("Не удалось получить курсы: %s", message)
                continue

            for pair, rate in client_rates.items():
                rates[pair] = rate
                sources[pair] = client.SOURCE

        updated_at = datetime.now(UTC)

        if rates:
            saved_count = self.storage.save_rates(
                rates=rates,
                sources=sources,
                updated_at=updated_at,
            )
            logger.info("Сохранено курсов: %s", saved_count)
        else:
            saved_count = 0
            logger.warning("Не получено ни одного курса для сохранения")

        return {
            "updated": saved_count,
            "timestamp": updated_at.isoformat(timespec="seconds").replace(
                "+00:00", "Z"
            ),
            "errors": errors,
        }
