"""Вспомогательные функции проекта"""

from datetime import datetime


def datetime_to_str(value: datetime) -> str:
    """Преобразует объект datetime в строку формата ISO 8601 для сериализации в JSON.

    Args:
        value (datetime): Объект даты и времени.

    Returns:
        str: Строка с датой и временем в формате ISO.
    """

    return value.isoformat()


def str_to_datetime(value: str) -> datetime:
    """Преобразует строку формата ISO 8601 из JSON обратно в объект datetime.

    Args:
        value (str): Строковое представление даты и времени.

    Returns:
        datetime: Десериализованный объект datetime.
    """

    return datetime.fromisoformat(value)
