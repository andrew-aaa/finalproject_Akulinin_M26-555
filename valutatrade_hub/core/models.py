"""Основные модели платформы"""

import hashlib
import hmac
import os
from datetime import datetime
from numbers import Real
from typing import Any


class User:
    """Пользователь системы"""

    def __init__(
        self,
        user_id: int,
        username: str,
        hased_password: str,
        salt: str,
        registration_date: datetime         
    ) -> None:
        self.user_id = user_id
        self.username = username
        self._hased_password = hased_password
        self._salt = salt
        self.registration_date = registration_date

    @staticmethod
    def _validate_user_id(value: int) -> None:
        if isinstance(value, bool) or not isinstance(value, int):
            raise TypeError("user_id должен быть целым числом")
        if value <= 0:
            raise ValueError("user_id должен быть положительным")

    @staticmethod
    def _validate_username(value: str) -> None:
        if not isinstance(value, str):
            raise TypeError("Имя пользователя должно быть строкой")
        if not value.strip():
            raise ValueError("Имя пользователя не может быть пустым")

    @staticmethod
    def _validate_password(value: str) -> None:
        if not isinstance(value, str):
            raise TypeError("Пароль должен быть строкой")
        if len(value) < 4:
            raise ValueError("Пароль должен быть не короче 4 символов")

    @staticmethod
    def _validate_datetime(value: datetime) -> None:
        if not isinstance(value, datetime):
            raise TypeError("registration_date должен быть объектом datetime")

    @staticmethod
    def _hash_password(password: str, salt: str) -> str:
        return hashlib.sha256((password + salt).encode("utf-8")).hexdigest()

    @property
    def user_id(self) -> int:
        return self._user_id

    @user_id.setter
    def user_id(self, value: int) -> None:
        self._validate_user_id(value)
        self._user_id = value

    @property
    def username(self) -> str:
        return self._username

    @username.setter
    def username(self, value: str) -> None:
        self._validate_username(value)
        self._username = value.strip()

    @property
    def hashed_password(self) -> str:
        return self._hashed_password

    @property
    def salt(self) -> str:
        return self._salt

    @property
    def registration_date(self) -> datetime:
        return self._registration_date

    @registration_date.setter
    def registration_date(self, value: datetime) -> None:
        self._validate_datetime(value)
        self._registration_date = value

    def get_user_info(self) -> dict[str, Any]:
        """Возвращает информацию о пользователе без пароля и соли"""
        
        return {
            "user_id": self.user_id,
            "username": self.username,
            "registration_date": self.registration_date.isoformat(),
        }

    def change_password(self, new_password: str) -> None:
        """Изменяет пароль, сохраняя только его односторонний хеш"""

        self._validate_password(new_password)
        self._hashed_password = self._hash_password(new_password, self.salt)

    def verify_password(self, password: str) -> bool:
        """Проверяет пароль пользователя."""

        if not isinstance(password, str):
            return False

        password_hash = self._hash_password(password, self.salt)
        return hmac.compare_digest(password_hash, self.hashed_password)

    def __repr__(self) -> str:
        return f"User(user_id={self.user_id!r}, username={self.username!r})"


class Wallet:
    """Кошелёк пользователя для одной валюты"""

    def __init__(self, currency_code: str, balance: float = 0.0) -> None:
        self.currency_code = currency_code
        self.balance = balance

    @staticmethod
    def _validate_currency_code(value: str) -> None:
        if not isinstance(value, str):
            raise TypeError("Код валюты должен быть строкой")
        if not value.strip():
            raise ValueError("Код валюты не может быть пустым")

    @staticmethod
    def _validate_amount(value: float, field_name: str = "amount") -> None:
        if isinstance(value, bool) or not isinstance(value, Real):
            raise TypeError(f"{field_name} должен быть числом")
        if value <= 0:
            raise ValueError(f"{field_name} должен быть положительным")

    @property
    def currency_code(self) -> str:
        return self._currency_code

    @currency_code.setter
    def currency_code(self, value: str) -> None:
        self._validate_currency_code(value)
        self._currency_code = value.strip().upper()

    @property
    def balance(self) -> float:
        return self._balance

    @balance.setter
    def balance(self, value: float) -> None:
        if isinstance(value, bool) or not isinstance(value, Real):
            raise TypeError("balance должен быть числом")
        if value < 0:
            raise ValueError("Баланс не может быть отрицательным")

        self._balance = float(value)

    def deposit(self, amount: float) -> None:
        """Пополняет кошелёк на указанную положительную сумму"""

        self._validate_amount(amount)
        self.balance += float(amount)

    def withdraw(self, amount: float) -> None:
        """Снимает сумму, если на кошельке достаточно средств"""
    
        self._validate_amount(amount)
        if amount > self.balance:
            raise ValueError("Недостаточно средств на кошельке")

        self.balance -= float(amount)

    def get_balance_info(self) -> dict[str, float | str]:
        """Возвращает код валюты и текущий баланс"""

        return {
            "currency_code": self.currency_code,
            "balance": self.balance,
        }

    def __repr__(self) -> str:
        return f"Wallet(currency_code={self.currency_code!r}, balance={self.balance!r})"


class Portfolio:
    """Портфель пользователя, содержащий кошельки разных валют."""

    exchange_rates: dict[str, float] = {
        "USD": 1.0,
        "EUR": 1.08,
        "GBP": 1.27,
        "RUB": 0.011,
        "BTC": 60000.0,
        "ETH": 2500.0,
    }

    def __init__(
        self,
        user_id: int | User,
        wallets: dict[str, Wallet] | None = None,
    ) -> None:
        self._user: User | None = user_id if isinstance(user_id, User) else None
        self._user_id = user_id.user_id if isinstance(user_id, User) else self._validate_user_id(user_id)
        self._wallets: dict[str, Wallet] = {}

        if wallets is not None:
            if not isinstance(wallets, dict):
                raise TypeError("wallets должен быть словарём")
            for currency_code, wallet in wallets.items():
                if not isinstance(wallet, Wallet):
                    raise TypeError("Все значения wallets должны быть объектами Wallet")
                if currency_code.upper() != wallet.currency_code:
                    raise ValueError("Ключ кошелька должен совпадать с currency_code")
                self._wallets[wallet.currency_code] = wallet

    @staticmethod
    def _validate_user_id(value: int) -> int:
        if isinstance(value, bool) or not isinstance(value, int):
            raise TypeError("user_id должен быть целым числом")
        if value <= 0:
            raise ValueError("user_id должен быть положительным")

        return value

    @property
    def user(self) -> User | None:
        """Возвращает связанный объект User, если он был передан в конструктор"""

        return self._user

    @property
    def user_id(self) -> int:
        return self._user_id

    @property
    def wallets(self) -> dict[str, Wallet]:
        """Возвращает копию словаря кошельков"""

        return self._wallets.copy()

    def add_currency(self, currency_code: str) -> Wallet:
        """Добавляет кошелёк новой валюты"""

        self._validate_currency_code(currency_code)
        code = currency_code.strip().upper()
        if code in self._wallets:
            raise ValueError(f"Кошелёк {code} уже существует")

        wallet = Wallet(code)
        self._wallets[code] = wallet
        return wallet

    @staticmethod
    def _validate_currency_code(value: str) -> None:
        if not isinstance(value, str):
            raise TypeError("Код валюты должен быть строкой")
        if not value.strip():
            raise ValueError("Код валюты не может быть пустым")

    def get_wallet(self, currency_code: str) -> Wallet:
        """Возвращает кошелёк по коду валюты"""

        self._validate_currency_code(currency_code)
        code = currency_code.strip().upper()
        try:
            return self._wallets[code]
        except KeyError as exc:
            raise KeyError(f"Кошелёк {code} не найден") from exc

    def get_total_value(self, base_currency: str = "USD") -> float:
        """Возвращает стоимость портфеля в указанной базовой валюте"""

        self._validate_currency_code(base_currency)
        base = base_currency.strip().upper()
        if base not in self.exchange_rates:
            raise ValueError(f"Нет курса для валюты {base}")

        base_rate = self.exchange_rates[base]
        total = 0.0
        for wallet in self._wallets.values():
            currency = wallet.currency_code
            if currency not in self.exchange_rates:
                raise ValueError(f"Нет курса для валюты {currency}")
            total += wallet.balance * self.exchange_rates[currency] / base_rate
        return total

    def __repr__(self) -> str:
        return f"Portfolio(user_id={self.user_id!r}, wallets={self._wallets!r})"


def create_user(
    user_id: int,
    username: str,
    password: str,
    registration_date: datetime | None = None,
    salt: str | None = None,
) -> User:
    """Вспомогательная функция создания User из обычного пароля"""

    User._validate_password(password)
    actual_salt = salt if salt is not None else os.urandom(16).hex()
    hashed_password = User._hash_password(password, actual_salt)

    return User(
        user_id=user_id,
        username=username,
        hashed_password=hashed_password,
        salt=actual_salt,
        registration_date=registration_date or datetime.now(),
    )
