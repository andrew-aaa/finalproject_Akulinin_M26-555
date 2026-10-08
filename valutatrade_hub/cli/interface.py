"""Командный интерфейс ValutaTrade Hub"""

import shlex

from prettytable import PrettyTable

from valutatrade_hub.core import usecases

HELP = """
Доступные команды:

register --username <имя> --password <пароль>
login --username <имя> --password <пароль>
show-portfolio [--base <валюта>]
buy --currency <валюта> --amount <количество>
sell --currency <валюта> --amount <количество>
get-rate --from <валюта> --to <валюта>
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

    reverse_rate, _ = usecases.get_rate(to_currency, from_currency)

    print(
        f"Обратный курс "
        f"{to_currency.upper()}→"
        f"{from_currency.upper()}: "
        f"{reverse_rate:.8f}"
    )


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

    if command_name == "exit":
        return None

    raise ValueError(f"Неизвестная команда: {command_name}")


def main() -> None:
    """Запускает CLI"""

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

        except (ValueError, TypeError, KeyError) as error:
            print(f"Ошибка: {error}")
        except KeyboardInterrupt:
            print("\nДо свидания!")
            break
