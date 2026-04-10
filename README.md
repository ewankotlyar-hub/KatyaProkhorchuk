# CLI File Manager

Небольшой CLI-проект для работы с файлами и папками.

## Структура

- `cli.py` — запуск CLI и разбор аргументов.
- `filemanager/manager.py` — бизнес-логика (`FileManager`).
- `tests/test_file_manager.py` — юнит-тесты логики.
- `tests/test_cli.py` — юнит-тесты командного интерфейса.
- `CLIProject_new.py` — совместимый entrypoint (прокси к `cli.py`).

## Требования

- Python 3.10+

Зависимости:

```bash
pip install -r requirements.txt
```

## Команды приложения

Формат запуска:

```bash
python cli.py <command> [arguments]
```

### 1) Копирование файла

```bash
python cli.py copy "C:\path\from\file.txt" "C:\path\to\folder"
python cli.py copy "./file.txt"
```

### 2) Удаление файла или папки

```bash
python cli.py delete "C:\path\to\file.txt"
python cli.py delete "C:\path\to\folder"
```

### 3) Подсчёт файлов в папке (включая вложенные)

```bash
python cli.py count "C:\path\to\folder"
```

### 4) Поиск файлов по регулярному выражению

```bash
python cli.py find "C:\path\to\folder" "\.py$"
python cli.py find "./project" "report.*\.txt$"
```

### 5) Добавление даты к имени файла(ов)

```bash
python cli.py rename_date "C:\path\to\file.jpg"
python cli.py rename_date "C:\path\to\folder"
python cli.py rename_date --recursive "C:\path\to\folder"
```

## Запуск тестов

```bash
python -m unittest discover -s tests -p "test_*.py"
```
