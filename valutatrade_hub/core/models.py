"""Основные модели платформы"""

import hashlib
import os
from datetime import UTC, datetime

EXCHANGE_RATES = {
    "USD": 1.0,
    "EUR": 1.08,
    "GBP": 1.27,
    "JPY": 0.0067,
    "RUB": 0.01016,
    "BTC": 59337.21,
    "ETH": 3720.00,
}


class User:
    """Пользователь системы"""

    def __init__(
        self,
        user_id: int,
        username: str,
        hashed_password: str,
        salt: str,
        registration_date: datetime,
    ) -> None:
        self.user_id = user_id
        self.username = username
        self._hashed_password = hashed_password
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

    def get_user_info(self) -> dict:
        """Возвращает информацию о пользователе"""

        return {
            "user_id": self.user_id,
            "username": self.username,
            "registration_date": self.registration_date.isoformat(),
        }

    def change_password(self, new_password: str) -> None:
        """Изменяет пароль пользователя"""

        self._validate_password(new_password)
        self._hashed_password = self._hash_password(new_password, self.salt)

    def verify_password(self, password: str) -> bool:
        """Проверяет введённый пароль"""

        if not isinstance(password, str):
            return False

        password_hash = self._hash_password(password, self.salt)
        return password_hash == self.hashed_password


class Wallet:
    """Кошелёк пользователя для одной валюты"""

    def __init__(
        self,
        currency_code: str,
        balance: float = 0.0,
    ) -> None:
        self.currency_code = currency_code
        self.balance = balance

    @staticmethod
    def _validate_currency_code(value: str) -> None:
        if not isinstance(value, str):
            raise TypeError("Код валюты должен быть строкой")

        if not value.strip():
            raise ValueError("Код валюты не может быть пустым")

    @staticmethod
    def _validate_amount(value: float) -> None:
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise TypeError("amount должен быть числом")

        if value <= 0:
            raise ValueError("amount должен быть положительным")

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
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise TypeError("balance должен быть числом")

        if value < 0:
            raise ValueError("Баланс не может быть отрицательным")

        self._balance = float(value)

    def deposit(self, amount: float) -> None:
        """Пополняет кошелёк"""

        self._validate_amount(amount)
        self.balance += float(amount)

    def withdraw(self, amount: float) -> None:
        """Снимает средства с кошелька"""

        self._validate_amount(amount)

        if amount > self.balance:
            raise ValueError("Недостаточно средств на кошельке")

        self.balance -= float(amount)

    def get_balance_info(self) -> dict:
        """Возвращает информацию о балансе"""

        return {
            "currency_code": self.currency_code,
            "balance": self.balance,
        }


class Portfolio:
    """Портфель пользователя, содержащий кошельки разных валют"""

    def __init__(
        self,
        user: User | int,
        wallets: dict[str, Wallet] | None = None,
    ) -> None:
        if isinstance(user, User):
            self._user = user
            self._user_id = user.user_id
        elif isinstance(user, int):
            self._user = None
            self._user_id = user
        else:
            raise TypeError("Пользователь должен быть User или целым ID")

        self._wallets: dict[str, Wallet] = {}

        if wallets is not None:
            for wallet in wallets.values():
                self._wallets[wallet.currency_code] = wallet

    @property
    def user(self) -> User | None:
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

        if not isinstance(currency_code, str):
            raise TypeError("Код валюты должен быть строкой")

        currency_code = currency_code.strip().upper()

        if not currency_code:
            raise ValueError("Код валюты не может быть пустым")

        if currency_code in self._wallets:
            return self._wallets[currency_code]

        wallet = Wallet(currency_code)
        self._wallets[currency_code] = wallet

        return wallet

    def get_total_value(self, base_currency: str = "USD") -> float:
        """Возвращает общую стоимость портфеля в базовой валюте"""

        base_currency = base_currency.strip().upper()

        if base_currency not in EXCHANGE_RATES:
            raise ValueError(f"Неизвестная базовая валюта: {base_currency}")

        total = 0.0

        for wallet in self._wallets.values():
            currency = wallet.currency_code

            if currency not in EXCHANGE_RATES:
                raise ValueError(f"Нет курса для валюты: {currency}")

            amount_in_usd = wallet.balance * EXCHANGE_RATES[currency]

            total += amount_in_usd

        if base_currency == "USD":
            return total

        return total / EXCHANGE_RATES[base_currency]

    def get_wallet(self, currency_code: str) -> Wallet:
        """Возвращает кошелёк указанной валюты"""

        currency_code = currency_code.strip().upper()

        if currency_code not in self._wallets:
            raise KeyError(currency_code)

        return self._wallets[currency_code]


def create_user(
    user_id: int,
    username: str,
    password: str,
    registration_date: datetime | None = None,
    salt: str | None = None,
) -> User:
    """Создаёт пользователя"""

    User._validate_password(password)

    actual_salt = salt if salt is not None else os.urandom(16).hex()

    hashed_password = User._hash_password(password, actual_salt)

    return User(
        user_id=user_id,
        username=username,
        hashed_password=hashed_password,
        salt=actual_salt,
        registration_date=registration_date or datetime.now(UTC),
    )
