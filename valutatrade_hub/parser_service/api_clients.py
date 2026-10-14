"""Работа с внешними API"""

from abc import ABC, abstractmethod

import requests

from valutatrade_hub.core.exceptions import ApiRequestError
from valutatrade_hub.parser_service.config import ParserConfig


class BaseApiClient(ABC):
    """Базовый интерфейс клиента API"""

    def __init__(self, config: ParserConfig | None = None) -> None:
        self.config = config or ParserConfig()

    @abstractmethod
    def fetch_rates(self) -> dict[str, float]:
        """Получить курсы в формате PAIR: RATE"""

        raise NotImplementedError


class CoinGeckoClient(BaseApiClient):
    """Клиент API CoinGecko для получения курсов криптовалют"""

    SOURCE = "CoinGecko"

    def fetch_rates(self) -> dict[str, float]:
        crypto_ids = [
            self.config.CRYPTO_ID_MAP[code]
            for code in self.config.CRYPTO_CURRENCIES
            if code in self.config.CRYPTO_ID_MAP
        ]

        if not crypto_ids:
            return {}

        params = {
            "ids": ",".join(crypto_ids),
            "vs_currencies": self.config.BASE_CURRENCY.lower(),
        }

        try:
            response = requests.get(
                self.config.COINGECKO_URL,
                params=params,
                timeout=self.config.REQUEST_TIMEOUT,
            )
            response.raise_for_status()
            data = response.json()
        except requests.exceptions.RequestException as exc:
            raise ApiRequestError(f"{self.SOURCE}: ошибка запроса: {exc}") from exc
        except ValueError as exc:
            raise ApiRequestError(
                f"{self.SOURCE}: сервер вернул некорректный JSON"
            ) from exc

        if not isinstance(data, dict):
            raise ApiRequestError(f"{self.SOURCE}: неожиданный формат ответа")

        rates: dict[str, float] = {}

        for currency, raw_id in self.config.CRYPTO_ID_MAP.items():
            if raw_id not in data:
                continue

            quote = data[raw_id]
            base = self.config.BASE_CURRENCY

            if not isinstance(quote, dict):
                continue

            rate = quote.get(base.lower())

            if (
                isinstance(rate, (int, float))
                and not isinstance(rate, bool)
                and rate > 0
            ):
                rates[f"{currency}_{base}"] = float(rate)

        return rates


class ExchangeRateApiClient(BaseApiClient):
    """Клиент ExchangeRate-API для получения курсов фиатных валют"""

    SOURCE = "ExchangeRate-API"

    def fetch_rates(self) -> dict[str, float]:
        api_key = self.config.EXCHANGERATE_API_KEY

        if not api_key:
            raise ApiRequestError("ExchangeRate-API: не задан EXCHANGERATE_API_KEY")

        url = f"{self.config.EXCHANGERATE_API_URL}/{api_key}/latest/{self.config.BASE_CURRENCY}"

        try:
            response = requests.get(url, timeout=self.config.REQUEST_TIMEOUT)
            response.raise_for_status()
            data = response.json()
        except requests.exceptions.RequestException as exc:
            raise ApiRequestError(f"{self.SOURCE}: ошибка запроса: {exc}") from exc
        except ValueError as exc:
            raise ApiRequestError(
                f"{self.SOURCE}: сервер вернул некорректный JSON"
            ) from exc

        if not isinstance(data, dict):
            raise ApiRequestError(f"{self.SOURCE}: неожиданный формат ответа")

        if data.get("result") != "success":
            error_type = data.get("error-type", "неизвестная ошибка")
            raise ApiRequestError(f"{self.SOURCE}: API вернул ошибку: {error_type}")

        raw_rates = data.get("conversion_rates", data.get("rates"))

        if not isinstance(raw_rates, dict):
            raise ApiRequestError(f"{self.SOURCE}: в ответе отсутствует словарь курсов")

        base = self.config.BASE_CURRENCY
        rates: dict[str, float] = {}

        for currency in self.config.FIAT_CURRENCIES:
            rate = raw_rates.get(currency)

            if (
                isinstance(rate, (int, float))
                and not isinstance(rate, bool)
                and rate > 0
            ):
                rates[f"{currency}_{base}"] = float(rate)

        return rates
