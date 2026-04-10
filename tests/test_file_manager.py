import os
import re
import shutil
import tempfile
import unittest

from filemanager import FileManager


class TestFileManager(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.mkdtemp()
        self.manager = FileManager()

    def tearDown(self) -> None:
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _mkfile(self, rel_path: str, content: str = "x") -> str:
        path = os.path.join(self.tmp, rel_path)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as file_handle:
            file_handle.write(content)
        return path

    def test_copy_file_to_dir(self) -> None:
        src = self._mkfile("a.txt")
        dest_dir = os.path.join(self.tmp, "dest")
        os.makedirs(dest_dir)
        copied_path = self.manager.copy_file(src, dest_dir)
        self.assertTrue(os.path.isfile(copied_path))
        self.assertEqual(os.path.basename(copied_path), "a.txt")

    def test_copy_file_not_found(self) -> None:
        with self.assertRaises(FileNotFoundError):
            self.manager.copy_file(os.path.join(self.tmp, "nonexistent.txt"))

    def test_delete_file(self) -> None:
        file_path = self._mkfile("delete.txt")
        self.manager.delete_path(file_path)
        self.assertFalse(os.path.exists(file_path))

    def test_delete_folder(self) -> None:
        folder = os.path.join(self.tmp, "subfolder")
        os.makedirs(folder)
        self._mkfile("subfolder/file.txt")
        self.manager.delete_path(folder)
        self.assertFalse(os.path.exists(folder))

    def test_delete_not_found(self) -> None:
        with self.assertRaises(FileNotFoundError):
            self.manager.delete_path(os.path.join(self.tmp, "ghost"))

    def test_count_files(self) -> None:
        self._mkfile("f1.txt")
        self._mkfile("f2.txt")
        self._mkfile("sub/f3.txt")
        self.assertEqual(self.manager.count_files(self.tmp), 3)

    def test_count_not_a_dir(self) -> None:
        file_path = self._mkfile("single.txt")
        with self.assertRaises(NotADirectoryError):
            self.manager.count_files(file_path)

    def test_find_files_by_extension(self) -> None:
        self._mkfile("a.py")
        self._mkfile("b.txt")
        self._mkfile("sub/c.py")
        results = self.manager.find_files(self.tmp, r"\.py$")
        names = [os.path.basename(path) for path in results]
        self.assertIn("a.py", names)
        self.assertIn("c.py", names)
        self.assertNotIn("b.txt", names)

    def test_find_files_no_match(self) -> None:
        self._mkfile("readme.md")
        self.assertEqual(self.manager.find_files(self.tmp, r"\.py$"), [])

    def test_rename_single_file(self) -> None:
        file_path = self._mkfile("photo.jpg")
        new_paths = self.manager.rename_with_date(file_path)
        self.assertEqual(len(new_paths), 1)
        self.assertFalse(os.path.exists(file_path))
        self.assertTrue(os.path.exists(new_paths[0]))
        self.assertRegex(os.path.basename(new_paths[0]), r"^\d{4}-\d{2}-\d{2}_photo\.jpg$")

    def test_rename_folder_non_recursive(self) -> None:
        self._mkfile("img.png")
        self._mkfile("nested/deep.png")
        self.manager.rename_with_date(self.tmp, recursive=False)
        top_files = os.listdir(self.tmp)
        renamed_top = [name for name in top_files if re.match(r"\d{4}-\d{2}-\d{2}_img\.png", name)]
        self.assertTrue(len(renamed_top) > 0)
        self.assertTrue(os.path.exists(os.path.join(self.tmp, "nested", "deep.png")))

    def test_rename_folder_recursive(self) -> None:
        self._mkfile("img.png")
        self._mkfile("nested/deep.png")
        self.manager.rename_with_date(self.tmp, recursive=True)
        nested_files = os.listdir(os.path.join(self.tmp, "nested"))
        renamed_nested = [name for name in nested_files if re.match(r"\d{4}-\d{2}-\d{2}_deep\.png", name)]
        self.assertTrue(len(renamed_nested) > 0)
