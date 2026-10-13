"""Базовый класс Currency и наследники Fiat/Crypto"""

import math
from abc import ABC, abstractmethod


class Currency(ABC):
    """Базовый класс валюты"""

    def __init__(self, name: str, code: str):
        if not isinstance(name, str) or not name.strip():
            raise ValueError("Название валюты не должно быть пустым")

        if (
            not isinstance(code, str)
            or not 2 <= len(code) <= 5
            or not code.isascii()
            or not code.isalpha()
            or code != code.upper()
        ):
            raise ValueError(
                "Код валюты должен содержать от 2 до 5 букв латинского алфавита в верхнем регистре"
            )

        self.name = name
        self.code = code

    @abstractmethod
    def get_display_info(self) -> str:
        """Возвращает информацию о валюте"""

        return {
            "code": self.code,
            "name": self.name,
            "sign": self.sign,
        }


class FiatCurrency(Currency):
    """Фиатная валюта"""

    def __init__(self, name: str, code: str, issuing_country: str):
        super().__init__(name, code)

        if not isinstance(issuing_country, str) or not issuing_country.strip():
            raise ValueError("Страна или зона эмиссии не должна быть пустой")

        self.issuing_country = issuing_country

    def get_display_info(self) -> str:
        return f"[FIAT] {self.code} — {self.name} (Issuing: {self.issuing_country})"


class CryptoCurrency(Currency):
    """Криптовалюта"""

    def __init__(self, name: str, code: str, algorithm: str, market_cap: float):
        super().__init__(name, code)

        if not isinstance(algorithm, str) or not algorithm.strip():
            raise ValueError("Алгоритм не должен быть пустым")

        if (
            isinstance(market_cap, bool)
            or not isinstance(market_cap, (int, float))
            or not math.isfinite(market_cap)
            or market_cap < 0
        ):
            raise ValueError("Капитализация должна быть неотрицательным числом")

        self.algorithm = algorithm
        self.market_cap = float(market_cap)

    def get_display_info(self) -> str:
        return f"[CRYPTO] {self.code} — {self.name} (Algo: {self.algorithm}, MCAP: {self.market_cap:.2e})"


_CURRENCIES = {
    "USD": FiatCurrency("US Dollar", "USD", "United States"),
    "EUR": FiatCurrency("Euro", "EUR", "Eurozone"),
    "GBP": FiatCurrency("British Pound", "GBP", "United Kingdom"),
    "JPY": FiatCurrency("Japanese Yen", "JPY", "Japan"),
    "RUB": FiatCurrency("Russian Ruble", "RUB", "Russia"),
    "BTC": CryptoCurrency("Bitcoin", "BTC", "SHA-256", 1.12e12),
    "ETH": CryptoCurrency("Ethereum", "ETH", "Ethash", 4.4e11),
}


def get_currency(code: str) -> Currency:
    """Возвращает валюту по коду"""

    if not isinstance(code, str):
        raise TypeError("Код валюты должен быть строкой")

    normalized_code = code.strip().upper()

    try:
        return _CURRENCIES[normalized_code]
    except KeyError:
        from valutatrade_hub.core.exceptions import CurrencyNotFoundError

        raise CurrencyNotFoundError(normalized_code) from None
