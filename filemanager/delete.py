"""Модуль удаления файлов и папок."""

import logging
import os
import shutil

logger = logging.getLogger(__name__)


def delete_path(path: str) -> None:
    """Удалить файл или папку (рекурсивно)."""
    if not os.path.exists(path):
        raise FileNotFoundError(f"Путь не найден: {path}")
    if os.path.isfile(path):
        os.remove(path)
        logger.info("Удалён файл: '%s'", path)
    else:
        shutil.rmtree(path)
        logger.info("Удалена папка: '%s'", path)
