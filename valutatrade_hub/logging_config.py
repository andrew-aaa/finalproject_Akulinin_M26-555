"""Настройка логов (формат, уровень, ротация)"""

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

from valutatrade_hub.infra.settings import SettingsLoader


def setup_logging():
    """Настраивает вывод логов в консоль и файл с ротацией"""

    settings = SettingsLoader()

    project_root = Path(__file__).resolve().parents[1]
    logs_dir = project_root / settings.get("logs_dir", "logs")
    logs_dir.mkdir(parents=True, exist_ok=True)

    log_level_name = settings.get("log_level", "INFO").upper()
    log_level = getattr(logging, log_level_name, logging.INFO)
    log_format = settings.get(
        "log_format",
        "%(asctime)s - %(levelname)s - %(message)s",
    )

    formatter = logging.Formatter(log_format)

    logger = logging.getLogger("valutatrade_hub")
    logger.setLevel(log_level)
    logger.propagate = False

    if logger.handlers:
        return logger

    file_handler = RotatingFileHandler(
        logs_dir / "valutatrade_hub.log",
        maxBytes=1_000_000,
        backupCount=3,
        encoding="utf-8",
    )
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    return logger
