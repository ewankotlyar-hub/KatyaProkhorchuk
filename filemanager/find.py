"""Модуль поиска файлов по регулярному выражению."""

import logging
import os
import re

logger = logging.getLogger(__name__)


def find_files(folder: str, pattern: str) -> list[str]:
    """Найти файлы в *folder*, чьи имена совпадают с регулярным выражением *pattern*."""
    if not os.path.isdir(folder):
        raise NotADirectoryError(f"Не является папкой: {folder}")
    regex = re.compile(pattern)
    matches: list[str] = []
    for root, _, files in os.walk(folder):
        for name in files:
            if regex.search(name):
                matches.append(os.path.join(root, name))
    logger.info(
        "Найдено %d файл(ов) по шаблону '%s' в '%s'",
        len(matches), pattern, folder,
    )
    return matches
