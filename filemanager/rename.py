"""Модуль переименования файлов с добавлением даты создания."""

import logging
import os
import time

logger = logging.getLogger(__name__)


def _get_creation_date_str(filepath: str) -> str:
    """Вернуть дату создания файла в формате ГГГГ-ММ-ДД.
    На Linux используется дата последнего изменения (st_mtime),
    так как st_birthtime недоступен."""
    stat = os.stat(filepath)
    ts = getattr(stat, "st_birthtime", stat.st_mtime)
    return time.strftime("%Y-%m-%d", time.localtime(ts))


def _rename_single_file(filepath: str) -> str:
    """Добавить дату создания в начало имени одного файла. Возвращает новый путь."""
    folder = os.path.dirname(filepath) or "."
    name = os.path.basename(filepath)
    date_str = _get_creation_date_str(filepath)
    if name.startswith(date_str):
        logger.info("Файл уже переименован, пропуск: '%s'", filepath)
        return filepath
    new_name = f"{date_str}_{name}"
    new_path = os.path.join(folder, new_name)
    os.rename(filepath, new_path)
    logger.info("Переименован '%s' -> '%s'", filepath, new_path)
    return new_path


def rename_with_date(path: str, recursive: bool = False) -> list[str]:
    """
    Добавить дату создания к имени файла(ов).
    - Если *path* — файл: переименовать его.
    - Если *path* — папка: переименовать все файлы внутри.
    - Если *recursive* = True: обработать все уровни вложенности.
    Возвращает список новых путей.
    """
    renamed: list[str] = []
    if os.path.isfile(path):
        renamed.append(_rename_single_file(path))
    elif os.path.isdir(path):
        if recursive:
            for root, _, files in os.walk(path):
                for name in files:
                    renamed.append(_rename_single_file(os.path.join(root, name)))
        else:
            for name in os.listdir(path):
                full = os.path.join(path, name)
                if os.path.isfile(full):
                    renamed.append(_rename_single_file(full))
    else:
        raise FileNotFoundError(f"Путь не найден: {path}")
    return renamed
