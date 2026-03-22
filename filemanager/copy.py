"""Модуль копирования файлов."""

import logging
import os
import shutil

logger = logging.getLogger(__name__)


def copy_file(src: str, dest: str = ".") -> str:
    """Копировать файл *src* в *dest* (папку или путь). Возвращает путь назначения."""
    if not os.path.isfile(src):
        raise FileNotFoundError(f"Исходный файл не найден: {src}")
    if os.path.isdir(dest):
        dest = os.path.join(dest, os.path.basename(src))
    shutil.copy2(src, dest)
    logger.info("Скопировано '%s' -> '%s'", src, dest)
    return dest
