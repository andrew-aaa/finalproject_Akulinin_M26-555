"""Singleton DatabaseManager (абстракция над JSON-хранилищем)"""

import json
from pathlib import Path

from valutatrade_hub.infra.settings import SettingsLoader


class DatabaseManager:
    """Менеджер JSON-файлов с использованием Singleton"""

    _instance = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if getattr(self, "_initialized", False):
            return

        self.settings = SettingsLoader()
        self.project_root = Path(__file__).resolve().parents[2]
        self._initialized = True

    def get_path(self, key):
        """Возвращает полный путь к файлу из настроек"""

        relative_path = self.settings.get(key)
        if relative_path is None:
            raise KeyError(f"Настройка пути '{key}' не найдена")

        return self.project_root / relative_path

    def load_json(self, key, default=None):
        """Читает JSON-файл. Если файла нет, возвращает default"""

        path = self.get_path(key)

        if not path.exists():
            return default

        with path.open("r", encoding="utf-8") as file:
            return json.load(file)

    def save_json(self, key, data):
        """Сохраняет данные в JSON-файл"""

        path = self.get_path(key)
        path.parent.mkdir(parents=True, exist_ok=True)

        with path.open("w", encoding="utf-8") as file:
            json.dump(data, file, ensure_ascii=False, indent=4)
