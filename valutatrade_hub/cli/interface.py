"""Командный интерфейс ValutaTrade Hub"""

import shlex

from prettytable import PrettyTable

from valutatrade_hub.core import usecases
from valutatrade_hub.core.exceptions import (
    ApiRequestError,
    CurrencyNotFoundError,
    InsufficientFundsError,
)
from valutatrade_hub.logging_config import setup_logging
from valutatrade_hub.parser_service.storage import RatesStorage
from valutatrade_hub.parser_service.updater import RatesUpdater

HELP = """
Доступные команды:

register --username <имя> --password <пароль>
login --username <имя> --password <пароль>
show-portfolio [--base <валюта>]
buy --currency <валюта> --amount <количество>
sell --currency <валюта> --amount <количество>
get-rate --from <валюта> --to <валюта>
update-rates [--source <coingecko|exchangerate>]
show-rates [--currency <код>] [--top <число>] [--base <код>]
help
exit
"""


def _parse_arguments(args: list[str]) -> dict[str, str]:
    """Преобразует аргументы вида --key value в словарь"""

    result = {}
    index = 0
    while index < len(args):
        argument = args[index]

        if not argument.startswith("--"):
            raise ValueError(f"Некорректный аргумент: {argument}")

        if index + 1 >= len(args):
            raise ValueError(f"Не указано значение для {argument}")

        key = argument[2:]
        result[key] = args[index + 1]

        index += 2

    return result


def _require_login(current_user):
    """Проверяет, что пользователь вошёл в систему"""

    if current_user is None:
        raise ValueError("Сначала выполните login")


def _show_portfolio(current_user, arguments: dict[str, str]) -> None:
    """Выводит портфель пользователя"""
    _require_login(current_user)
    base_currency = arguments.get("base", "USD")
    portfolio = usecases.show_portfolio(current_user, base_currency)

    print(
        f"\nПортфель пользователя '{portfolio['username']}' (база: {portfolio['base_currency']}):"
    )

    if not portfolio["wallets"]:
        print("Портфель пуст.")
        return

    table = PrettyTable()
    table.field_names = [
        "Валюта",
        "Баланс",
        f"Стоимость ({portfolio['base_currency']})",
    ]

    for wallet in portfolio["wallets"]:
        table.add_row(
            [
                wallet["currency_code"],
                f"{wallet['balance']:.4f}",
                f"{wallet['value']:.2f}",
            ]
        )

    print(table)
    print(f"ИТОГО: {portfolio['total_value']:,.2f} {portfolio['base_currency']}")


def _buy_currency(current_user, arguments: dict[str, str]) -> None:
    """Покупает валюту"""

    _require_login(current_user)

    if "currency" not in arguments:
        raise ValueError("Не указан параметр --currency")

    if "amount" not in arguments:
        raise ValueError("Не указан параметр --amount")

    result = usecases.buy_currency(
        current_user, arguments["currency"], arguments["amount"]
    )

    print(
        f"Покупка выполнена: "
        f"{result['amount']:.4f} "
        f"{result['currency_code']} "
        f"по курсу "
        f"{result['rate']:.2f} USD/"
        f"{result['currency_code']}"
    )

    print(f"Стоимость покупки: {result['cost_usd']:,.2f} USD")


def _sell_currency(current_user, arguments: dict[str, str]) -> None:
    """Продаёт валюту"""

    _require_login(current_user)

    if "currency" not in arguments:
        raise ValueError("Не указан параметр --currency")

    if "amount" not in arguments:
        raise ValueError("Не указан параметр --amount")

    result = usecases.sell_currency(
        current_user, arguments["currency"], arguments["amount"]
    )

    print(
        f"Продажа выполнена: "
        f"{result['amount']:.4f} "
        f"{result['currency_code']} "
        f"по курсу "
        f"{result['rate']:.2f} USD/"
        f"{result['currency_code']}"
    )

    print(f"Выручка: {result['received_usd']:,.2f} USD")


def _get_rate(arguments: dict[str, str]) -> None:
    """Показывает курс одной валюты к другой"""

    if "from" not in arguments:
        raise ValueError("Не указан параметр --from")

    if "to" not in arguments:
        raise ValueError("Не указан параметр --to")

    from_currency = arguments["from"]
    to_currency = arguments["to"]

    rate, timestamp = usecases.get_rate(from_currency, to_currency)

    print(
        f"Курс {from_currency.upper()}→"
        f"{to_currency.upper()}: "
        f"{rate:.8f} "
        f"(обновлено: "
        f"{timestamp.strftime('%Y-%m-%d %H:%M:%S')})"
    )

    reverse_rate = 1 / rate

    print(
        f"Обратный курс "
        f"{to_currency.upper()}→"
        f"{from_currency.upper()}: "
        f"{reverse_rate:.8f}"
    )


def _update_rates(arguments: dict[str, str]) -> None:
    """Получает актуальные курсы через внешние API"""

    source = arguments.get("source")
    result = RatesUpdater().update(source=source)

    print(f"Обновление завершено. Сохранено курсов: {result['updated']}")
    print(f"Время обновления: {result['timestamp']}")

    if result["errors"]:
        print("Предупреждения:")
        for error in result["errors"]:
            print(f"- {error}")


def _show_rates(arguments: dict[str, str]) -> None:
    """Выводит актуальные курсы из локального кэша"""

    storage = RatesStorage()
    data = storage.get_rates()
    pairs = data["pairs"]

    if not pairs:
        print(
            "Локальный кеш курсов пуст. Выполните 'update-rates', чтобы загрузить данные"
        )
        return

    base = arguments.get("base")
    if base:
        base = base.strip().upper()
        if not base:
            raise ValueError("Параметр --base не может быть пустым")

    currency = arguments.get("currency")
    if currency:
        currency = currency.strip().upper()
        if not currency:
            raise ValueError("Параметр --currency не может быть пустым")

    top = None
    if "top" in arguments:
        try:
            top = int(arguments["top"])
        except ValueError:
            raise ValueError("Параметр --top должен быть целым числом")

        if top <= 0:
            raise ValueError("Параметр --top должен быть больше нуля")

    filtered_pairs = {}

    if base:
        base_to_usd = None

        if base == "USD":
            base_to_usd = 1.0
        else:
            base_pair = pairs.get(f"{base}_USD")
            if isinstance(base_pair, dict):
                try:
                    base_to_usd = float(base_pair["rate"])
                except (KeyError, TypeError, ValueError):
                    base_to_usd = None

        if base_to_usd is None or base_to_usd <= 0:
            print(f"Не удалось найти курс {base}_USD для пересчёта")
            return

        for pair, item in pairs.items():
            if not isinstance(item, dict) or "rate" not in item:
                continue

            from_currency, separator, to_currency = pair.partition("_")
            if not separator or to_currency != "USD":
                continue

            try:
                rate = float(item["rate"])
            except (KeyError, TypeError, ValueError):
                continue

            if rate <= 0:
                continue

            if currency and currency != from_currency:
                continue

            filtered_pairs[f"{from_currency}_{base}"] = {
                **item,
                "rate": rate / base_to_usd,
            }
    else:
        for pair, item in pairs.items():
            if not isinstance(item, dict) or "rate" not in item:
                continue

            from_currency, separator, to_currency = pair.partition("_")
            if not separator:
                continue

            if (
                top is not None
                and currency
                and currency not in (from_currency, to_currency)
            ):
                if from_currency not in ("BTC", "ETH", "SOL"):
                    continue
            elif (
                top is None
                and currency
                and currency not in (from_currency, to_currency)
            ):
                continue

            filtered_pairs[pair] = item

    if currency and not filtered_pairs:
        print(f"Курс для '{currency}' не найден в кеше")
        return

    if top is not None:
        crypto_pairs = {
            pair: item
            for pair, item in filtered_pairs.items()
            if pair.split("_", maxsplit=1)[0] in ("BTC", "ETH", "SOL")
        }
        filtered_pairs = dict(
            sorted(
                crypto_pairs.items(),
                key=lambda entry: float(entry[1]["rate"]),
                reverse=True,
            )[:top]
        )
    else:
        filtered_pairs = dict(sorted(filtered_pairs.items()))

    if not filtered_pairs:
        print("Подходящие курсы в кеше отсутствуют")
        return

    table = PrettyTable()
    table.field_names = ["Пара", "Курс", "Источник", "Обновлено"]

    for pair, item in filtered_pairs.items():
        table.add_row(
            [
                pair,
                f"{item['rate']:.8f}",
                item.get("source", "unknown"),
                item.get("updated_at", "неизвестно"),
            ]
        )

    print("Курсы из локального кеша:")
    print(table)
    print(f"Последнее обновление кэша: {data.get('last_refresh') or 'нет данных'}")


def execute(command: str, current_user=None):
    """Выполняет одну CLI-команду"""

    parts = shlex.split(command)
    if not parts:
        return current_user

    command_name = parts[0]
    arguments = _parse_arguments(parts[1:])

    if command_name == "help":
        print(HELP)
        return current_user

    if command_name == "register":
        if "username" not in arguments:
            raise ValueError("Не указан параметр --username")

        if "password" not in arguments:
            raise ValueError("Не указан параметр --password")

        user = usecases.register_user(arguments["username"], arguments["password"])

        print(
            f"Пользователь '{user.username}' "
            f"зарегистрирован "
            f"(id={user.user_id}). "
            f"Войдите: login "
            f"--username {user.username} "
            f"--password ****"
        )

        return current_user

    if command_name == "login":
        if "username" not in arguments:
            raise ValueError("Не указан параметр --username")

        if "password" not in arguments:
            raise ValueError("Не указан параметр --password")

        user = usecases.login_user(arguments["username"], arguments["password"])

        print(f"Вы вошли как '{user.username}'")
        return user

    if command_name == "show-portfolio":
        _show_portfolio(current_user, arguments)
        return current_user

    if command_name == "buy":
        _buy_currency(current_user, arguments)
        return current_user

    if command_name == "sell":
        _sell_currency(current_user, arguments)
        return current_user

    if command_name == "get-rate":
        _get_rate(arguments)
        return current_user

    if command_name == "update-rates":
        _update_rates(arguments)
        return current_user

    if command_name == "show-rates":
        _show_rates(arguments)
        return current_user

    if command_name == "exit":
        return None

    raise ValueError(f"Неизвестная команда: {command_name}")


def main() -> None:
    """Запускает CLI"""

    setup_logging()

    current_user = None
    print("ValutaTrade Hub. Введите 'help' для списка команд.")

    while True:
        try:
            command = input("> ").strip()

            if not command:
                continue

            if command == "exit":
                print("До свидания!")
                break

            current_user = execute(command, current_user)
        except CurrencyNotFoundError as e:
            print(f"Ошибка: {e}. Проверьте код валюты и команду help")
        except ApiRequestError as e:
            print(f"Ошибка: {e}. Попробуйте повторить запрос позже")
        except (
            ValueError,
            TypeError,
            KeyError,
            InsufficientFundsError,
        ) as e:
            print(f"Ошибка: {e}")
        except KeyboardInterrupt:
            print("\nДо свидания!")
            break
