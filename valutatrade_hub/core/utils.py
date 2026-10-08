"""Вспомогательные функции проекта"""

from datetime import datetime
from functools import wraps
from time import monotonic


def datetime_to_str(value: datetime) -> str:
    """Преобразует datetime в ISO-строку для JSON"""

    return value.isoformat()


def str_to_datetime(value: str) -> datetime:
    """Преобразует ISO-строку из JSON в datetime"""

    return datetime.fromisoformat(value)


def log_action(func):
    """Декоратор для логирования вызова функции"""

    @wraps(func)
    def wrapper(*args, **kwargs):
        print(f"[LOG] Вызов функции: {func.__name__}")
        result = func(*args, **kwargs)
        print(f"[LOG] Функция {func.__name__} выполнена")
        return result

    return wrapper


def cache_with_ttl(ttl_seconds: int):
    """Создаёт декоратор с кэшем на заданное время"""

    cache = {}

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            key = (args, tuple(sorted(kwargs.items())))
            current_time = monotonic()

            if key in cache:
                result, saved_time = cache[key]

                if current_time - saved_time < ttl_seconds:
                    return result

            result = func(*args, **kwargs)
            cache[key] = (result, current_time)

            return result

        return wrapper

    return decorator
