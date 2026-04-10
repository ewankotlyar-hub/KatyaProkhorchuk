import os
import re
import shutil
import time


class FileManager:
    """Business logic for file-system operations."""

    def copy_file(self, src: str, dest: str = ".") -> str:
        if not os.path.isfile(src):
            raise FileNotFoundError(f"Исходный файл не найден: {src}")
        if os.path.isdir(dest):
            dest = os.path.join(dest, os.path.basename(src))
        shutil.copy2(src, dest)
        return dest

    def delete_path(self, path: str) -> None:
        if not os.path.exists(path):
            raise FileNotFoundError(f"Путь не найден: {path}")
        if os.path.isfile(path):
            os.remove(path)
            return
        shutil.rmtree(path)

    def count_files(self, folder: str) -> int:
        if not os.path.isdir(folder):
            raise NotADirectoryError(f"Не является папкой: {folder}")
        total = 0
        for _, _, files in os.walk(folder):
            total += len(files)
        return total

    def find_files(self, folder: str, pattern: str) -> list[str]:
        if not os.path.isdir(folder):
            raise NotADirectoryError(f"Не является папкой: {folder}")
        regex = re.compile(pattern)
        matches: list[str] = []
        for root, _, files in os.walk(folder):
            for name in files:
                if regex.search(name):
                    matches.append(os.path.join(root, name))
        return matches

    def rename_with_date(self, path: str, recursive: bool = False) -> list[str]:
        renamed: list[str] = []
        if os.path.isfile(path):
            renamed.append(self._rename_single_file(path))
            return renamed
        if not os.path.isdir(path):
            raise FileNotFoundError(f"Путь не найден: {path}")
        if recursive:
            for root, _, files in os.walk(path):
                for name in files:
                    renamed.append(self._rename_single_file(os.path.join(root, name)))
            return renamed
        for name in os.listdir(path):
            full_path = os.path.join(path, name)
            if os.path.isfile(full_path):
                renamed.append(self._rename_single_file(full_path))
        return renamed

    def _rename_single_file(self, filepath: str) -> str:
        folder = os.path.dirname(filepath) or "."
        name = os.path.basename(filepath)
        date_prefix = self._get_creation_date(filepath)
        if name.startswith(date_prefix):
            return filepath
        new_name = f"{date_prefix}_{name}"
        new_path = os.path.join(folder, new_name)
        os.rename(filepath, new_path)
        return new_path

    @staticmethod
    def _get_creation_date(filepath: str) -> str:
        stats = os.stat(filepath)
        timestamp = getattr(stats, "st_birthtime", stats.st_mtime)
        return time.strftime("%Y-%m-%d", time.localtime(timestamp))
