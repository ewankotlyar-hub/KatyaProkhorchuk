"""
Менеджер файловой системы (CLI)
Использование: python cli.py <команда> [аргументы]

Команды:
  copy <файл> [назначение]      Копировать файл (по умолчанию: текущая папка)
  delete <путь>                 Удалить файл или папку
  count <папка>                 Подсчитать все файлы в папке (включая вложенные)
  find <папка> <шаблон>         Найти файлы по регулярному выражению (включая вложенные)
  rename_date <путь>            Добавить дату создания к имени файла(ов)
                                --recursive   Обработать все уровни вложенности

Запуск тестов:
  python -m unittest cli
"""

import argparse
import logging
import os
import re
import shutil
import sys
import time
import unittest

# ---------------------------------------------------------------------------
# Настройка логирования
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="[%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Основной функционал
# ---------------------------------------------------------------------------


def copy_file(src: str, dest: str = ".") -> str:
    """Копировать файл *src* в *dest* (папку или путь). Возвращает путь назначения."""
    if not os.path.isfile(src):
        raise FileNotFoundError(f"Исходный файл не найден: {src}")
    # Если назначение — папка, сохраняем файл с тем же именем внутри неё
    if os.path.isdir(dest):
        dest = os.path.join(dest, os.path.basename(src))
    shutil.copy2(src, dest)
    logger.info("Скопировано '%s' -> '%s'", src, dest)
    return dest


def delete_path(path: str) -> None:
    """Удалить файл или папку (рекурсивно)."""
    if not os.path.exists(path):
        raise FileNotFoundError(f"Путь не найден: {path}")
    if os.path.isfile(path):
        os.remove(path)
        logger.info("Удалён файл: '%s'", path)
    else:
        # Удаляем папку со всем содержимым
        shutil.rmtree(path)
        logger.info("Удалена папка: '%s'", path)


def count_files(folder: str) -> int:
    """Подсчитать все файлы в *folder*, включая вложенные подпапки."""
    if not os.path.isdir(folder):
        raise NotADirectoryError(f"Не является папкой: {folder}")
    total = 0
    for _, _, files in os.walk(folder):
        total += len(files)
    logger.info("Всего файлов в '%s': %d", folder, total)
    return total


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


def _get_creation_date_str(filepath: str) -> str:
    """Вернуть дату создания файла в формате ГГГГ-ММ-ДД.
    На Linux используется дата последнего изменения (st_mtime),
    так как st_birthtime недоступен."""
    stat = os.stat(filepath)
    # st_birthtime доступен на macOS/Windows; на Linux — откат к st_mtime
    ts = getattr(stat, "st_birthtime", stat.st_mtime)
    return time.strftime("%Y-%m-%d", time.localtime(ts))


def _rename_single_file(filepath: str) -> str:
    """Добавить дату создания в начало имени одного файла. Возвращает новый путь."""
    folder = os.path.dirname(filepath) or "."
    name = os.path.basename(filepath)
    date_str = _get_creation_date_str(filepath)
    # Пропускаем, если дата уже добавлена
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
            # Обходим все вложенные папки
            for root, _, files in os.walk(path):
                for name in files:
                    renamed.append(_rename_single_file(os.path.join(root, name)))
        else:
            # Только файлы верхнего уровня указанной папки
            for name in os.listdir(path):
                full = os.path.join(path, name)
                if os.path.isfile(full):
                    renamed.append(_rename_single_file(full))
    else:
        raise FileNotFoundError(f"Путь не найден: {path}")
    return renamed


# ---------------------------------------------------------------------------
# CLI — разбор аргументов командной строки
# ---------------------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    """Создать и вернуть парсер аргументов командной строки."""
    parser = argparse.ArgumentParser(
        prog="cli.py",
        description="Простой менеджер файловой системы.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    sub = parser.add_subparsers(dest="command", metavar="команда")
    sub.required = True

    # --- copy: копирование файла ---
    p_copy = sub.add_parser("copy", help="Копировать файл в указанное место")
    p_copy.add_argument("file", help="Путь к исходному файлу")
    p_copy.add_argument("dest", nargs="?", default=".", help="Путь назначения (по умолчанию: .)")

    # --- delete: удаление файла или папки ---
    p_del = sub.add_parser("delete", help="Удалить файл или папку")
    p_del.add_argument("path", help="Путь к файлу или папке")

    # --- count: подсчёт файлов ---
    p_count = sub.add_parser("count", help="Подсчитать файлы в папке (включая вложенные)")
    p_count.add_argument("folder", help="Целевая папка")

    # --- find: поиск файлов по шаблону ---
    p_find = sub.add_parser("find", help="Найти файлы по регулярному выражению")
    p_find.add_argument("folder", help="Целевая папка")
    p_find.add_argument("pattern", help="Регулярное выражение для имён файлов")

    # --- rename_date: добавить дату к имени ---
    p_rd = sub.add_parser(
        "rename_date",
        help="Добавить дату создания к имени файла(ов)",
    )
    p_rd.add_argument("path", help="Путь к файлу или папке")
    p_rd.add_argument(
        "--recursive",
        action="store_true",
        help="Обработать все уровни вложенности (только для папок)",
    )

    return parser


def run_cli(args: list[str] | None = None) -> None:
    """Разобрать аргументы и вызвать соответствующую функцию."""
    parser = build_parser()
    ns = parser.parse_args(args)

    if ns.command == "copy":
        result = copy_file(ns.file, ns.dest)
        print(f"Файл успешно скопирован: {result}")

    elif ns.command == "delete":
        delete_path(ns.path)
        print(f"Успешно удалено: {ns.path}")

    elif ns.command == "count":
        n = count_files(ns.folder)
        print(f"Количество файлов в папке: {n}")

    elif ns.command == "find":
        results = find_files(ns.folder, ns.pattern)
        if results:
            print(f"Найдено файлов: {len(results)}")
            for r in results:
                print(f"  {r}")
        else:
            print("Файлы по заданному шаблону не найдены.")

    elif ns.command == "rename_date":
        renamed = rename_with_date(ns.path, recursive=ns.recursive)
        print(f"Переименовано файлов: {len(renamed)}")


# ---------------------------------------------------------------------------
# Юнит-тесты
# ---------------------------------------------------------------------------


class TestFilesystem(unittest.TestCase):
    """Тесты для основного функционала работы с файловой системой."""

    def setUp(self):
        """Создать временную папку перед каждым тестом."""
        import tempfile
        self.tmp = tempfile.mkdtemp()

    def tearDown(self):
        """Удалить временную папку после каждого теста."""
        shutil.rmtree(self.tmp, ignore_errors=True)

    # --- Вспомогательный метод ---

    def _mkfile(self, rel_path: str, content: str = "x") -> str:
        """Создать файл по относительному пути внутри временной папки."""
        path = os.path.join(self.tmp, rel_path)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w") as f:
            f.write(content)
        return path

    # --- copy ---

    def test_copy_file_to_dir(self):
        """Файл должен скопироваться в указанную папку с сохранением имени."""
        src = self._mkfile("a.txt")
        dest_dir = os.path.join(self.tmp, "dest")
        os.makedirs(dest_dir)
        result = copy_file(src, dest_dir)
        self.assertTrue(os.path.isfile(result))
        self.assertEqual(os.path.basename(result), "a.txt")

    def test_copy_file_not_found(self):
        """Должно выбрасываться FileNotFoundError, если исходный файл не существует."""
        with self.assertRaises(FileNotFoundError):
            copy_file(os.path.join(self.tmp, "nonexistent.txt"))

    # --- delete ---

    def test_delete_file(self):
        """Файл должен быть удалён."""
        f = self._mkfile("del.txt")
        delete_path(f)
        self.assertFalse(os.path.exists(f))

    def test_delete_folder(self):
        """Папка со всем содержимым должна быть удалена."""
        folder = os.path.join(self.tmp, "sub")
        os.makedirs(folder)
        self._mkfile("sub/file.txt")
        delete_path(folder)
        self.assertFalse(os.path.exists(folder))

    def test_delete_not_found(self):
        """Должно выбрасываться FileNotFoundError, если путь не существует."""
        with self.assertRaises(FileNotFoundError):
            delete_path(os.path.join(self.tmp, "ghost"))

    # --- count ---

    def test_count_files(self):
        """Должны быть подсчитаны все файлы, включая вложенные."""
        self._mkfile("f1.txt")
        self._mkfile("f2.txt")
        self._mkfile("sub/f3.txt")
        self.assertEqual(count_files(self.tmp), 3)

    def test_count_not_a_dir(self):
        """Должно выбрасываться NotADirectoryError, если передан файл вместо папки."""
        f = self._mkfile("file.txt")
        with self.assertRaises(NotADirectoryError):
            count_files(f)

    # --- find ---

    def test_find_files_by_extension(self):
        """Должны быть найдены файлы с расширением .py, включая вложенные."""
        self._mkfile("a.py")
        self._mkfile("b.txt")
        self._mkfile("sub/c.py")
        results = find_files(self.tmp, r"\.py$")
        names = [os.path.basename(r) for r in results]
        self.assertIn("a.py", names)
        self.assertIn("c.py", names)
        self.assertNotIn("b.txt", names)

    def test_find_files_no_match(self):
        """Должен вернуться пустой список, если совпадений нет."""
        self._mkfile("readme.md")
        results = find_files(self.tmp, r"\.py$")
        self.assertEqual(results, [])

    # --- rename_date ---

    def test_rename_single_file(self):
        """Одиночный файл должен получить дату создания в начале имени."""
        f = self._mkfile("photo.jpg")
        new_paths = rename_with_date(f)
        self.assertEqual(len(new_paths), 1)
        self.assertFalse(os.path.exists(f))
        self.assertTrue(os.path.exists(new_paths[0]))
        self.assertRegex(os.path.basename(new_paths[0]), r"^\d{4}-\d{2}-\d{2}_photo\.jpg$")

    def test_rename_folder_non_recursive(self):
        """Без флага --recursive вложенные файлы не должны переименовываться."""
        self._mkfile("img.png")
        self._mkfile("nested/deep.png")
        rename_with_date(self.tmp, recursive=False)
        top_files = os.listdir(self.tmp)
        # Файл верхнего уровня должен быть переименован
        renamed_top = [f for f in top_files if re.match(r"\d{4}-\d{2}-\d{2}_img\.png", f)]
        self.assertTrue(len(renamed_top) > 0)
        # Файл во вложенной папке должен остаться без изменений
        deep = os.path.join(self.tmp, "nested", "deep.png")
        self.assertTrue(os.path.exists(deep))

    def test_rename_folder_recursive(self):
        """С флагом --recursive все вложенные файлы должны быть переименованы."""
        self._mkfile("img.png")
        self._mkfile("nested/deep.png")
        rename_with_date(self.tmp, recursive=True)
        deep_dir = os.path.join(self.tmp, "nested")
        deep_files = os.listdir(deep_dir)
        # Вложенный файл должен иметь дату в начале имени
        renamed_deep = [f for f in deep_files if re.match(r"\d{4}-\d{2}-\d{2}_deep\.png", f)]
        self.assertTrue(len(renamed_deep) > 0)


class TestCLI(unittest.TestCase):
    """Тесты для CLI-интерфейса (разбор аргументов и вызов функций)."""

    def setUp(self):
        """Создать временную папку перед каждым тестом."""
        import tempfile
        self.tmp = tempfile.mkdtemp()

    def tearDown(self):
        """Удалить временную папку после каждого теста."""
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _mkfile(self, rel_path: str) -> str:
        """Создать пустой файл по относительному пути во временной папке."""
        path = os.path.join(self.tmp, rel_path)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        open(path, "w").close()
        return path

    def test_cli_copy(self):
        """CLI copy должен скопировать файл в указанную папку."""
        src = self._mkfile("orig.txt")
        dest_dir = os.path.join(self.tmp, "out")
        os.makedirs(dest_dir)
        run_cli(["copy", src, dest_dir])
        self.assertTrue(os.path.isfile(os.path.join(dest_dir, "orig.txt")))

    def test_cli_delete(self):
        """CLI delete должен удалить указанный файл."""
        f = self._mkfile("bye.txt")
        run_cli(["delete", f])
        self.assertFalse(os.path.exists(f))

    def test_cli_count(self):
        """CLI count должен выполниться без ошибок."""
        self._mkfile("a.txt")
        self._mkfile("b.txt")
        run_cli(["count", self.tmp])

    def test_cli_find(self):
        """CLI find должен выполниться без ошибок."""
        self._mkfile("hello.py")
        run_cli(["find", self.tmp, r"\.py$"])

    def test_cli_rename_date(self):
        """CLI rename_date должен переименовать одиночный файл."""
        f = self._mkfile("snap.jpg")
        run_cli(["rename_date", f])
        self.assertFalse(os.path.exists(f))

    def test_cli_rename_date_recursive(self):
        """CLI rename_date --recursive должен переименовать файлы в подпапках."""
        self._mkfile("root.txt")
        self._mkfile("sub/child.txt")
        run_cli(["rename_date", "--recursive", self.tmp])
        sub_files = os.listdir(os.path.join(self.tmp, "sub"))
        self.assertTrue(any(f.endswith("_child.txt") for f in sub_files))

    def test_parser_unknown_command(self):
        """Неизвестная команда должна завершить программу с ошибкой (SystemExit)."""
        parser = build_parser()
        with self.assertRaises(SystemExit):
            parser.parse_args(["лететь"])


# ---------------------------------------------------------------------------
# Точка входа
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    run_cli()
