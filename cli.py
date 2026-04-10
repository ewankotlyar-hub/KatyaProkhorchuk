import argparse
import logging

from filemanager import FileManager

logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


class FileManagerCLI:
    """Coordinator for command parsing and command execution."""

    def __init__(self, manager: FileManager | None = None) -> None:
        self._manager = manager or FileManager()

    def build_parser(self) -> argparse.ArgumentParser:
        parser = argparse.ArgumentParser(
            prog="cli.py",
            description="Простой менеджер файловой системы.",
        )
        sub = parser.add_subparsers(dest="command", metavar="команда")
        sub.required = True

        p_copy = sub.add_parser("copy", help="Копировать файл в указанное место")
        p_copy.add_argument("file", help="Путь к исходному файлу")
        p_copy.add_argument("dest", nargs="?", default=".", help="Путь назначения")

        p_del = sub.add_parser("delete", help="Удалить файл или папку")
        p_del.add_argument("path", help="Путь к файлу или папке")

        p_count = sub.add_parser("count", help="Подсчитать файлы в папке")
        p_count.add_argument("folder", help="Целевая папка")

        p_find = sub.add_parser("find", help="Найти файлы по регулярному выражению")
        p_find.add_argument("folder", help="Целевая папка")
        p_find.add_argument("pattern", help="Регулярное выражение для имён файлов")

        p_rename = sub.add_parser("rename_date", help="Добавить дату создания к имени файла(ов)")
        p_rename.add_argument("path", help="Путь к файлу или папке")
        p_rename.add_argument("--recursive", action="store_true", help="Обработать вложенные папки")

        return parser

    def run(self, args: list[str] | None = None) -> None:
        parser = self.build_parser()
        ns = parser.parse_args(args)

        if ns.command == "copy":
            result = self._manager.copy_file(ns.file, ns.dest)
            print(f"Файл успешно скопирован: {result}")
            return
        if ns.command == "delete":
            self._manager.delete_path(ns.path)
            print(f"Успешно удалено: {ns.path}")
            return
        if ns.command == "count":
            count = self._manager.count_files(ns.folder)
            print(f"Количество файлов в папке: {count}")
            return
        if ns.command == "find":
            results = self._manager.find_files(ns.folder, ns.pattern)
            if not results:
                print("Файлы по заданному шаблону не найдены.")
                return
            print(f"Найдено файлов: {len(results)}")
            for result in results:
                print(f"  {result}")
            return
        renamed = self._manager.rename_with_date(ns.path, recursive=ns.recursive)
        print(f"Переименовано файлов: {len(renamed)}")


def run_cli(args: list[str] | None = None) -> None:
    FileManagerCLI().run(args)


if __name__ == "__main__":
    run_cli()
