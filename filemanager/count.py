"""Модуль подсчёта файлов в папке."""

import logging
import os

logger = logging.getLogger(__name__)


def count_files(folder: str) -> int:
    """Подсчитать все файлы в *folder*, включая вложенные подпапки."""
    if not os.path.isdir(folder):
        raise NotADirectoryError(f"Не является папкой: {folder}")
    total = 0
    for _, _, files in os.walk(folder):
        total += len(files)
    logger.info("Всего файлов в '%s': %d", folder, total)
    return total
