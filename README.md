# Simple File Manager (CLI + GUI)

Базовый учебный проект с файловыми операциями.

## Что умеет

- `copy` - копирование файла
- `delete` - удаление файла или папки
- `count` - подсчёт файлов в папке (включая вложенные)
- `find` - поиск файлов по regex-шаблону
- `rename_date` - добавление даты создания к имени файла

## Установка

```bash
python -m pip install -r requirements.txt
```

## Запуск GUI

```bash
cd python
python gui.py
```

В GUI:
- выберите вкладку нужной операции
- укажите пути через кнопки выбора (или вручную)
- нажмите кнопку выполнения

## Запуск CLI

```bash
cd python
python cli.py copy <file> [dest]
python cli.py delete <path>
python cli.py count <folder>
python cli.py find <folder> <pattern>
python cli.py rename_date <path> [--recursive]
```

## Тесты

```bash
cd python
python -m pytest filemanager_test.py
```
