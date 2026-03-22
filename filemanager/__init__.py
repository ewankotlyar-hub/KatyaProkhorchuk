"""Менеджер файловой системы — пакет с утилитами для работы с файлами."""

from filemanager.copy import copy_file
from filemanager.delete import delete_path
from filemanager.count import count_files
from filemanager.find import find_files
from filemanager.rename import rename_with_date

__all__ = [
    "copy_file",
    "delete_path",
    "count_files",
    "find_files",
    "rename_with_date",
]
