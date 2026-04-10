import os
import shutil
import tempfile
import unittest

from cli import FileManagerCLI, run_cli


class TestCLI(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.mkdtemp()

    def tearDown(self) -> None:
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _mkfile(self, rel_path: str) -> str:
        path = os.path.join(self.tmp, rel_path)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8"):
            pass
        return path

    def test_cli_copy(self) -> None:
        src = self._mkfile("orig.txt")
        dest_dir = os.path.join(self.tmp, "out")
        os.makedirs(dest_dir)
        run_cli(["copy", src, dest_dir])
        self.assertTrue(os.path.isfile(os.path.join(dest_dir, "orig.txt")))

    def test_cli_delete(self) -> None:
        file_path = self._mkfile("bye.txt")
        run_cli(["delete", file_path])
        self.assertFalse(os.path.exists(file_path))

    def test_cli_count(self) -> None:
        self._mkfile("a.txt")
        self._mkfile("b.txt")
        run_cli(["count", self.tmp])

    def test_cli_find(self) -> None:
        self._mkfile("hello.py")
        run_cli(["find", self.tmp, r"\.py$"])

    def test_cli_rename_date(self) -> None:
        file_path = self._mkfile("snap.jpg")
        run_cli(["rename_date", file_path])
        self.assertFalse(os.path.exists(file_path))

    def test_cli_rename_date_recursive(self) -> None:
        self._mkfile("root.txt")
        self._mkfile("sub/child.txt")
        run_cli(["rename_date", "--recursive", self.tmp])
        sub_files = os.listdir(os.path.join(self.tmp, "sub"))
        self.assertTrue(any(name.endswith("_child.txt") for name in sub_files))

    def test_parser_unknown_command(self) -> None:
        parser = FileManagerCLI().build_parser()
        with self.assertRaises(SystemExit):
            parser.parse_args(["лететь"])
