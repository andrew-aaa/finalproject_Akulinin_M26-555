"""Бизнес-логика приложения ValutaTrade Hub"""

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

from valutatrade_hub.core.currencies import get_currency
from valutatrade_hub.core.exceptions import (
    ApiRequestError,
    InsufficientFundsError,
)
from valutatrade_hub.core.models import (
    EXCHANGE_RATES,
    Portfolio,
    User,
    Wallet,
    create_user,
)
from valutatrade_hub.core.utils import (
    datetime_to_str,
    str_to_datetime,
)
from valutatrade_hub.decorators import log_action
from valutatrade_hub.infra.database import DatabaseManager
from valutatrade_hub.infra.settings import SettingsLoader

db = DatabaseManager()

USERS_FILE = db.get_path("users_file")
PORTFOLIOS_FILE = db.get_path("portfolios_file")
RATES_FILE = db.get_path("rates_file")

DATA_DIR = USERS_FILE.parent


def _ensure_data_files() -> None:
    """Создаёт папку data и JSON-файлы, если их ещё нет"""

    DATA_DIR.mkdir(parents=True, exist_ok=True)

    for file_path in (USERS_FILE, PORTFOLIOS_FILE, RATES_FILE):
        if not file_path.exists():
            if file_path in (USERS_FILE, PORTFOLIOS_FILE):
                file_path.write_text("[]", encoding="utf-8")
            else:
                file_path.write_text("{}", encoding="utf-8")


def _read_json(file_path: Path) -> list | dict:
    """Читает данные из JSON-файла через DatabaseManager"""

    _ensure_data_files()

    if file_path == USERS_FILE:
        key = "users_file"
        default = []
    elif file_path == PORTFOLIOS_FILE:
        key = "portfolios_file"
        default = []
    elif file_path == RATES_FILE:
        key = "rates_file"
        default = {}
    else:
        raise ValueError(f"Неизвестный файл данных: {file_path}")

    try:
        return db.load_json(key, default)
    except json.JSONDecodeError:
        return default


def _write_json(file_path: Path, data: list | dict) -> None:
    """Записывает данные в JSON-файл через DatabaseManager"""

    if file_path == USERS_FILE:
        key = "users_file"
    elif file_path == PORTFOLIOS_FILE:
        key = "portfolios_file"
    elif file_path == RATES_FILE:
        key = "rates_file"
    else:
        raise ValueError(f"Неизвестный файл данных: {file_path}")

    db.save_json(key, data)


def _normalize_currency(currency_code: str) -> str:
    """Проверяет и приводит код валюты к верхнему регистру"""

    if not isinstance(currency_code, str):
        raise TypeError("Код валюты должен быть строкой")

    currency_code = currency_code.strip().upper()
    if not currency_code:
        raise ValueError("Код валюты не может быть пустым")

    return currency_code


def _validate_amount(amount: float) -> float:
    """Проверяет сумму операции"""

    if isinstance(amount, bool):
        raise TypeError("Сумма должна быть числом")

    try:
        amount = float(amount)
    except (TypeError, ValueError):
        raise TypeError("Сумма должна быть числом")

    if amount <= 0:
        raise ValueError("Сумма должна быть положительной")

    return amount


def _serialize_user(user: User) -> dict:
    """Преобразует пользователя в словарь для JSON"""

    return {
        "user_id": user.user_id,
        "username": user.username,
        "hashed_password": user.hashed_password,
        "salt": user.salt,
        "registration_date": datetime_to_str(user.registration_date),
    }


def _deserialize_user(data: dict) -> User:
    """Создаёт объект User из данных JSON"""

    return User(
        user_id=data["user_id"],
        username=data["username"],
        hashed_password=data["hashed_password"],
        salt=data["salt"],
        registration_date=str_to_datetime(data["registration_date"]),
    )


def _serialize_portfolio(portfolio: Portfolio) -> dict:
    """Преобразует портфель в словарь для JSON"""

    wallets = {}

    for currency_code, wallet in portfolio.wallets.items():
        wallets[currency_code] = {
            "currency_code": wallet.currency_code,
            "balance": wallet.balance,
        }

    return {
        "user_id": portfolio.user_id,
        "wallets": wallets,
    }


def _deserialize_portfolio(data: dict, user: User | None = None) -> Portfolio:
    """Создаёт объект Portfolio из данных JSON"""

    wallets = {}

    for currency_code, wallet_data in data.get("wallets", {}).items():
        wallet = Wallet(
            currency_code=wallet_data["currency_code"],
            balance=wallet_data["balance"],
        )
        wallets[currency_code] = wallet

    if user is not None:
        portfolio_user = user
    else:
        portfolio_user = data["user_id"]

    return Portfolio(
        user=portfolio_user,
        wallets=wallets,
    )


def _find_user_by_username(username: str) -> User | None:
    """Находит пользователя по имени"""

    users_data = _read_json(USERS_FILE)

    for user_data in users_data:
        if user_data["username"] == username:
            return _deserialize_user(user_data)

    return None


@log_action("REGISTER")
def register_user(username: str, password: str) -> User:
    """Регистрирует нового пользователя"""

    username = username.strip()

    if not username:
        raise ValueError("Имя пользователя не может быть пустым")

    if _find_user_by_username(username) is not None:
        raise ValueError("Пользователь с таким именем уже существует")

    users_data = _read_json(USERS_FILE)
    if users_data:
        user_id = max(user["user_id"] for user in users_data) + 1
    else:
        user_id = 1

    user = create_user(
        user_id=user_id,
        username=username,
        password=password,
    )

    users_data.append(_serialize_user(user))

    _write_json(USERS_FILE, users_data)

    portfolio = Portfolio(user)
    portfolio.add_currency("USD")

    save_portfolio(portfolio)

    return user


@log_action("LOGIN")
def login_user(username: str, password: str) -> User:
    """Проверяет логин и пароль пользователя"""

    user = _find_user_by_username(username.strip())
    if user is None:
        raise ValueError("Неверное имя пользователя или пароль")

    if not user.verify_password(password):
        raise ValueError("Неверное имя пользователя или пароль")

    return user


def load_portfolio(user: User) -> Portfolio:
    """Загружает портфель пользователя"""

    portfolios_data = _read_json(PORTFOLIOS_FILE)

    for portfolio_data in portfolios_data:
        if portfolio_data["user_id"] == user.user_id:
            return _deserialize_portfolio(
                portfolio_data,
                user,
            )

    portfolio = Portfolio(user)
    portfolio.add_currency("USD")
    return portfolio


def save_portfolio(portfolio: Portfolio) -> None:
    """Сохраняет портфель пользователя"""

    portfolios_data = _read_json(PORTFOLIOS_FILE)
    portfolio_data = _serialize_portfolio(portfolio)

    for index, saved_portfolio in enumerate(portfolios_data):
        if saved_portfolio["user_id"] == portfolio.user_id:
            portfolios_data[index] = portfolio_data
            break
    else:
        portfolios_data.append(portfolio_data)

    _write_json(PORTFOLIOS_FILE, portfolios_data)


def _get_cached_rate(base_currency: str, quote_currency: str) -> float | None:
    """Возвращает курс из кеша, если он ещё не устарел"""

    rates_data = _read_json(RATES_FILE)
    key = f"{base_currency}_{quote_currency}"
    rate_data = rates_data.get(key)

    if rate_data is None:
        return None

    try:
        updated_at = str_to_datetime(rate_data["updated_at"])
        rate = float(rate_data["rate"])
    except (KeyError, TypeError, ValueError):
        return None

    ttl = SettingsLoader().get("rate_cache_ttl", 300)

    if datetime.now(UTC) - updated_at > timedelta(seconds=ttl):
        return None

    return rate


def _save_rate(base_currency: str, quote_currency: str, rate: float) -> None:
    """Сохраняет курс в кеш"""

    rates_data = _read_json(RATES_FILE)

    key = f"{base_currency}_{quote_currency}"

    rates_data[key] = {
        "rate": rate,
        "updated_at": datetime_to_str(datetime.now(UTC)),
    }

    _write_json(RATES_FILE, rates_data)


@log_action("get_rate")
def get_rate(base_currency: str, quote_currency: str) -> tuple[float, datetime]:
    """Возвращает курс валют и время его обновления"""

    base_currency = _normalize_currency(base_currency)
    quote_currency = _normalize_currency(quote_currency)

    get_currency(base_currency)
    get_currency(quote_currency)

    if base_currency == quote_currency:
        return 1.0, datetime.now(UTC)

    cached_rate = _get_cached_rate(base_currency, quote_currency)

    if cached_rate is not None:
        rates_data = _read_json(RATES_FILE)
        key = f"{base_currency}_{quote_currency}"
        updated_at = str_to_datetime(rates_data[key]["updated_at"])
        return cached_rate, updated_at

    if base_currency in EXCHANGE_RATES and quote_currency in EXCHANGE_RATES:
        rate = EXCHANGE_RATES[base_currency] / EXCHANGE_RATES[quote_currency]
    else:
        raise ApiRequestError(
            f"Курс для пары {base_currency}/{quote_currency} недоступен"
        )

    timestamp = datetime.now(UTC)
    _save_rate(base_currency, quote_currency, rate)

    return rate, timestamp


def show_portfolio(user: User, base_currency: str = "USD") -> dict:
    """Возвращает информацию о портфеле"""

    base_currency = _normalize_currency(base_currency)

    portfolio = load_portfolio(user)

    wallets = []
    for wallet in portfolio.wallets.values():
        rate, _ = get_rate(wallet.currency_code, base_currency)
        value = wallet.balance * rate

        wallets.append(
            {
                "currency_code": wallet.currency_code,
                "balance": wallet.balance,
                "value": value,
            }
        )

    total_value = sum(wallet["value"] for wallet in wallets)

    return {
        "username": user.username,
        "base_currency": base_currency,
        "wallets": wallets,
        "total_value": total_value,
    }


@log_action("BUY", verbose=True)
def buy_currency(user: User, currency_code: str, amount: float) -> dict:
    """Покупает валюту за USD"""

    currency_code = _normalize_currency(currency_code)
    amount = _validate_amount(amount)

    get_currency(currency_code)

    if currency_code == "USD":
        raise ValueError("Нельзя покупать USD за USD")

    portfolio = load_portfolio(user)
    usd_wallet = portfolio.get_wallet("USD")
    rate, _ = get_rate(currency_code, "USD")

    cost = amount * rate

    if cost > usd_wallet.balance:
        raise InsufficientFundsError(
            available=usd_wallet.balance, required=cost, code="USD"
        )

    target_wallet = portfolio.add_currency(currency_code)
    balance_before = target_wallet.balance

    usd_wallet.withdraw(cost)
    target_wallet.deposit(amount)

    save_portfolio(portfolio)

    return {
        "currency_code": currency_code,
        "amount": amount,
        "rate": rate,
        "cost_usd": cost,
        "balance_before": balance_before,
        "balance_after": target_wallet.balance,
    }


@log_action("SELL", verbose=True)
def sell_currency(user: User, currency_code: str, amount: float) -> dict:
    """Продаёт валюту и получает USD"""

    currency_code = _normalize_currency(currency_code)
    amount = _validate_amount(amount)

    get_currency(currency_code)

    if currency_code == "USD":
        raise ValueError("Нельзя продавать USD за USD")

    portfolio = load_portfolio(user)

    try:
        wallet = portfolio.get_wallet(currency_code)
    except KeyError:
        raise ValueError(f"Кошелёк {currency_code} отсутствует в портфеле")

    rate, _ = get_rate(currency_code, "USD")
    balance_before = wallet.balance

    usd_amount = amount * rate

    wallet.withdraw(amount)

    usd_wallet = portfolio.get_wallet("USD")
    usd_wallet.deposit(usd_amount)

    save_portfolio(portfolio)

    return {
        "currency_code": currency_code,
        "amount": amount,
        "rate": rate,
        "received_usd": usd_amount,
        "balance_before": balance_before,
        "balance_after": wallet.balance,
    }
