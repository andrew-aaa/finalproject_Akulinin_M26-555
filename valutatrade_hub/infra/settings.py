"""Singleton SettingsLoader (конфигурация)"""

import json
from pathlib import Path


class SettingsLoader:
    """Загрузчик настроек с использованием Singleton"""

    _instance = None
    _settings = None

    def __new__(cls, *args, **kwargs):
        # __new__ выбран для простой реализации Singleton без метакласса.

        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self, settings_path=None):
        if self._settings is not None:
            return

        if settings_path is None:
            project_root = Path(__file__).resolve().parents[2]
            settings_path = project_root / "config.json"

        self.settings_path = Path(settings_path)

        if self.settings_path.exists():
            with self.settings_path.open("r", encoding="utf-8") as file:
                self._settings = json.load(file)
        else:
            self._settings = {}

    def get(self, key, default=None):
        """Возвращает настройку или значение по умолчанию"""

        return self._settings.get(key, default)

    def all(self):
        """Возвращает все настройки"""

        return self._settings.copy()
