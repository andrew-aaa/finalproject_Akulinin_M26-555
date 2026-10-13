"""Вспомогательные функции проекта"""

from datetime import datetime


def datetime_to_str(value: datetime) -> str:
    """Преобразует datetime в ISO-строку для JSON"""

    return value.isoformat()


def str_to_datetime(value: str) -> datetime:
    """Преобразует ISO-строку из JSON в datetime"""

    return datetime.fromisoformat(value)
