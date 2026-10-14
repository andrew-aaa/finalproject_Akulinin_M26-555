"""Планировщик периодического обновления"""

import logging
import time

from valutatrade_hub.parser_service.updater import RatesUpdater

logger = logging.getLogger("valutatrade_hub.parser")


class RatesSchedular:
    """Запускает обновление курсов с заданным интервалом"""

    def __init__(
        self,
        updater: RatesUpdater | None = None,
        interval_seconds: int = 300,
    ) -> None:
        if interval_seconds <= 0:
            raise ValueError("Интервал должен быть больше нуля")

        self.updater = updater or RatesUpdater()
        self.interval_seconds = interval_seconds

    def run_once(self) -> dict[str, object]:
        """Выполняет одно обновление"""

        return self.updater.update()

    def run_forever(self) -> None:
        """Обновляет курсы до остановки процесса"""

        logger.info("Планировщик запущен. Интервал: %s сек.", self.interval_seconds)

        try:
            while True:
                try:
                    result = self.run_once()
                    logger.info("Результат обновления: %s", result)
                except Exception:
                    logger.exception("Ошибка при обновлении курсов")

                time.sleep(self.interval_seconds)
        except KeyboardInterrupt:
            logger.info("Планировщик остановлен пользователем")
