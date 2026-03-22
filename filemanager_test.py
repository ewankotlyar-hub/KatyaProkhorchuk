"""Тесты для менеджера файловой системы."""

import os
import re
import shutil
import tempfile
import unittest

from filemanager import copy_file, delete_path, count_files, find_files, rename_with_date
from CLIProject import build_parser, run_cli


class TestFilesystem(unittest.TestCase):
    """Тесты для основного функционала работы с файловой системой."""

    def setUp(self):
        """Создать временную папку перед каждым тестом."""
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
        renamed_top = [f for f in top_files if re.match(r"\d{4}-\d{2}-\d{2}_img\.png", f)]
        self.assertTrue(len(renamed_top) > 0)
        deep = os.path.join(self.tmp, "nested", "deep.png")
        self.assertTrue(os.path.exists(deep))

    def test_rename_folder_recursive(self):
        """С флагом --recursive все вложенные файлы должны быть переименованы."""
        self._mkfile("img.png")
        self._mkfile("nested/deep.png")
        rename_with_date(self.tmp, recursive=True)
        deep_dir = os.path.join(self.tmp, "nested")
        deep_files = os.listdir(deep_dir)
        renamed_deep = [f for f in deep_files if re.match(r"\d{4}-\d{2}-\d{2}_deep\.png", f)]
        self.assertTrue(len(renamed_deep) > 0)


class TestCLI(unittest.TestCase):
    """Тесты для CLI-интерфейса (разбор аргументов и вызов функций)."""

    def setUp(self):
        """Создать временную папку перед каждым тестом."""
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


if __name__ == "__main__":
    unittest.main()
