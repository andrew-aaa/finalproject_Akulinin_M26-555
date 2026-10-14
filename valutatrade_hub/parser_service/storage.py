"""Операции чтения/записи exchange_rates.json"""

import json
import logging
import os
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from valutatrade_hub.infra.settings import SettingsLoader
from valutatrade_hub.parser_service.config import ParserConfig

logger = logging.getLogger("valutatrade_hub.parser")


class RatesStorage:
    """Читает и атомарно сохраняет историю и текущие курсы"""

    def __init__(self, config: ParserConfig | None = None) -> None:
        self.config = config or ParserConfig()

    @staticmethod
    def _now() -> datetime:
        """Возвращает текущее время в UTC"""

        return datetime.now(UTC)

    @staticmethod
    def _read_json(path: Path, default: Any) -> Any:
        """Читает JSON-файл; возвращает default, если файла ещё нет"""

        if not path.exists():
            return default

        try:
            with path.open("r", encoding="utf-8") as file:
                return json.load(file)
        except (json.JSONDecodeError, OSError) as exc:
            raise ValueError(f"Не удалось прочитать {path}: {exc}") from exc

    @staticmethod
    def _atomic_write_json(path: Path, data: Any) -> None:
        """Записывает JSON во временный файл и атомарно заменяет целевой"""

        path.parent.mkdir(parents=True, exist_ok=True)
        temp_path = None

        try:
            with tempfile.NamedTemporaryFile(
                mode="w",
                encoding="utf-8",
                dir=path.parent,
                suffix=".tmp",
                delete=False,
            ) as file:
                temp_path = Path(file.name)
                json.dump(data, file, ensure_ascii=False, indent=2)
                file.write("\n")
                file.flush()
                os.fsync(file.fileno())

            temp_path.replace(path)
        finally:
            if temp_path is not None and temp_path.exists():
                temp_path.unlink()

    @staticmethod
    def _validate_pair(pair: str) -> tuple[str, str]:
        """Проверяет пару вида BTC_USD"""

        parts = pair.upper().split("_")

        if len(parts) != 2 or any(
            not part.isalpha() or not 2 <= len(part) <= 5 for part in parts
        ):
            raise ValueError(f"Некорректная валютная пара: {pair}")

        return parts[0], parts[1]

    def save_rates(
        self,
        rates: dict[str, float],
        sources: dict[str, str],
        updated_at: datetime | None = None,
    ) -> int:
        """
        Сохраняет измерения в историю и обновляет актуальный кэш
        Возвращает количество пар, переданных на сохранение
        """

        if not isinstance(rates, dict):
            raise TypeError("rates должен быть словарём")

        timestamp = updated_at or self._now()

        if timestamp.tzinfo is None:
            raise ValueError("updated_at должен содержать часовой пояс")

        timestamp = timestamp.astimezone(UTC)
        timestamp_text = timestamp.isoformat(timespec="microseconds").replace(
            "+00:00", "Z"
        )

        history_path = self.config.HISTORY_FILE_PATH
        cache_path = self.config.RATES_FILE_PATH

        history = self._read_json(history_path, [])
        if not isinstance(history, list):
            raise TypeError("История курсов должна быть JSON-массивом")

        cache = self._read_json(cache_path, {"pairs": {}, "last_refresh": None})

        if not isinstance(cache, dict):
            raise TypeError("Некорректный формат кэша курсов")

        if "pairs" not in cache:
            cache = {"pairs": cache, "last_refresh": None}

        if not isinstance(cache.get("pairs"), dict):
            raise TypeError("Некорректный формат кэша курсов")

        cache = {"pairs": cache["pairs"], "last_refresh": cache.get("last_refresh")}

        history_ids = {item.get("id") for item in history if isinstance(item, dict)}
        saved_count = 0
        for raw_pair, raw_rate in rates.items():
            pair = raw_pair.upper()
            from_currency, to_currency = self._validate_pair(pair)

            if (
                not isinstance(raw_rate, (int, float))
                or isinstance(raw_rate, bool)
                or raw_rate <= 0
            ):
                logger.warning("Пропущен некорректный курс для %s", pair)
                continue

            source = next(
                (value for key, value in sources.items() if key.upper() == pair),
                "unknown",
            )
            record_id = f"{from_currency}_{to_currency}_{timestamp_text}"

            record = {
                "id": record_id,
                "from_currency": from_currency,
                "to_currency": to_currency,
                "rate": float(raw_rate),
                "timestamp": timestamp_text,
                "source": source,
                "meta": {},
            }

            if record_id not in history_ids:
                history.append(record)
                history_ids.add(record_id)

            current = cache["pairs"].get(pair)
            current_timestamp = None

            if isinstance(current, dict):
                current_updated_at = current.get("updated_at")

                if isinstance(current_updated_at, str):
                    try:
                        current_timestamp = datetime.fromisoformat(current_updated_at)
                        if current_timestamp.tzinfo is None:
                            current_timestamp = current_timestamp.replace(tzinfo=UTC)
                        current_timestamp = current_timestamp.astimezone(UTC)
                    except ValueError:
                        logger.warning("Некорректная дата обновления курса %s", pair)

            if current_timestamp is None or current_timestamp < timestamp:
                cache["pairs"][pair] = {
                    "rate": float(raw_rate),
                    "updated_at": timestamp_text,
                    "source": source,
                }

            saved_count += 1

        cache["last_refresh"] = (
            self._now().isoformat(timespec="seconds").replace("+00:00", "Z")
        )

        self._atomic_write_json(history_path, history)
        self._atomic_write_json(cache_path, cache)

        logger.info("Сохранено курсов: %s", saved_count)
        return saved_count

    def get_rates(self) -> dict[str, Any]:
        """Возвращает актуальный кэш курсов"""

        cache = self._read_json(
            self.config.RATES_FILE_PATH, {"pairs": {}, "last_refresh": None}
        )

        if not isinstance(cache, dict):
            raise TypeError("Некорректный формат кэша курсов")

        if "pairs" not in cache:
            return {"pairs": cache, "last_refresh": None}

        pairs = cache.get("pairs")
        if not isinstance(pairs, dict):
            raise TypeError("Некорректный формат пар в кэше")

        now = self._now()
        ttl_seconds = SettingsLoader().get("rate_cache_ttl", 300)
        valid_pairs = {}

        for pair, item in pairs.items():
            if not isinstance(item, dict):
                continue

            updated_at = item.get("updated_at")
            if not isinstance(updated_at, str):
                continue

            try:
                timestamp = datetime.fromisoformat(updated_at)
            except ValueError:
                logger.warning("Некорректная дата обновления курса %s", pair)
                continue

            if timestamp.tzinfo is None:
                timestamp = timestamp.replace(tzinfo=UTC)

            age_seconds = (now - timestamp.astimezone(UTC)).total_seconds()
            if 0 <= age_seconds <= ttl_seconds:
                valid_pairs[pair] = item

        cache["pairs"] = valid_pairs
        return cache

    def get_history(self) -> list[dict[str, Any]]:
        """Возвращает историю измерений курсов"""

        history = self._read_json(self.config.HISTORY_FILE_PATH, [])

        if not isinstance(history, list):
            raise TypeError("История курсов должна быть JSON-массивом")

        return history
