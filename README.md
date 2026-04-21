# Books to Scrape Monitor

Проект для непрерывного скрапинга `books.toscrape.com` с накоплением данных в SQLite/CSV, последующим анализом запусков и web-интерфейсом на `FastAPI` для выборки данных из базы.

## Идея проекта

`books.toscrape.com` почти не меняет сам каталог книг, поэтому в качестве непрерывно меняющейся метрики используется цена в рублях:

- цена книги в фунтах берется с сайта;
- курс `GBP -> RUB` подтягивается с внешнего API при каждом запуске;
- итоговая цена в рублях сохраняется вместе с меткой времени запуска.

За счет этого можно анализировать динамику средней стоимости книг в рублях по разным датам запусков, даже если сам каталог книг остается стабильным.

## Что собирается

Для каждой книги сохраняются:

- `title` - название;
- `category` - категория книги;
- `upc` - уникальный идентификатор книги;
- `rating` - рейтинг от 1 до 5;
- `price_gbp` - цена в фунтах;
- `exchange_rate_gbp_rub` - курс фунта к рублю на момент запуска;
- `price_rub` - цена в рублях;
- `availability` - текст о наличии;
- `is_in_stock` - наличие в виде `True/False`;
- `scraped_at` - время запуска;
- `run_id` - идентификатор конкретного запуска.

## Структура проекта

```text
.
├── main.py
├── requirements.txt
├── README.md
├── data/
│   ├── books.sqlite
│   └── raw/
│       └── book_snapshots.csv
├── artifacts/
│   ├── latest_snapshot.csv
│   ├── run_summary.csv
│   ├── category_summary_latest.csv
│   ├── analysis_summary.json
│   ├── avg_price_rub_by_run.png
│   └── category_avg_price_latest.png
└── src/
    └── books_monitor/
        ├── analysis.py
        ├── api/
        │   ├── app.py
        │   ├── schemas.py
        │   └── __init__.py
        ├── config.py
        ├── flow.py
        ├── models.py
        ├── query_service.py
        ├── scraper.py
        └── storage.py
```

## Установка

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Точка входа

Основная точка входа: `main.py`

### 1. Запустить скрапер один раз

```bash
python3 main.py scrape
```

Команда:

- собирает книги со всех страниц каталога;
- сохраняет данные в `data/books.sqlite`;
- дублирует сырые данные в `data/raw/book_snapshots.csv`;
- обновляет артефакты анализа в папке `artifacts/`.

### 2. Пересобрать только анализ

```bash
python3 main.py analyze
```

### 3. Прогнать Prefect flow один раз

```bash
python3 main.py pipeline
```

### 4. Поднять непрерывный запуск через Prefect

Ниже пример локального запуска каждые 6 часов:

```bash
python3 main.py serve --interval-hours 6
```

После этого flow будет запускаться по cron-расписанию `0 */6 * * *`.

### 5. Запустить web API

```bash
python3 main.py api --host 127.0.0.1 --port 8000
```

После запуска будут доступны:

- Swagger UI: `http://127.0.0.1:8000/docs`
- ReDoc: `http://127.0.0.1:8000/redoc`
- OpenAPI JSON: `http://127.0.0.1:8000/openapi.json`

## Полезные параметры

Для тестового прогона можно ограничить объем:

```bash
python3 main.py scrape --limit-pages 2 --max-books 20
```

Или пропустить пересчет артефактов:

```bash
python3 main.py scrape --skip-analysis
```

Практически это удобно комбинировать так:

```bash
python3 main.py scrape --limit-pages 2 --max-books 20 --skip-analysis
```

Итоговый анализ в `artifacts/` строится по полным прогонам каталога, чтобы тестовые укороченные запуски не искажали графики и сводки.

## Web API

API отдает только небольшие срезы данных. Для всех списковых эндпоинтов включены:

- пагинация через `limit` и `offset`;
- ограничение `limit <= 50`;
- фильтрация;
- сортировка;
- валидация входных параметров через FastAPI/Pydantic.

### Доступные эндпоинты

#### `GET /api/v1/health`

Краткая информация о состоянии базы:

- путь к SQLite;
- количество запусков;
- количество сохраненных снимков;
- идентификатор последнего запуска.

#### `GET /api/v1/runs`

Список запусков скрапера с пагинацией и сортировкой.

Пример:

```bash
curl "http://127.0.0.1:8000/api/v1/runs?limit=5&sort_by=scraped_at&sort_order=desc"
```

#### `GET /api/v1/books`

Основной эндпоинт выборки книг из последнего или указанного запуска.

Поддерживаемые параметры:

- `run_id` - выбрать конкретный запуск;
- `category` - фильтр по категории;
- `min_rating` - минимальный рейтинг;
- `max_price_rub` - верхняя граница цены в рублях;
- `in_stock` - только книги в наличии / не в наличии;
- `title_query` - поиск по фрагменту названия;
- `sort_by` - `scraped_at`, `title`, `category`, `rating`, `price_gbp`, `price_rub`;
- `sort_order` - `asc` или `desc`;
- `limit`, `offset` - пагинация.

Пример:

```bash
curl "http://127.0.0.1:8000/api/v1/books?category=Poetry&min_rating=3&in_stock=true&sort_by=price_rub&sort_order=asc&limit=10"
```

#### `GET /api/v1/books/{upc}/history`

История одной книги по `UPC` между разными запусками.

Пример:

```bash
curl "http://127.0.0.1:8000/api/v1/books/a897fe39b1053632/history?limit=10"
```

#### `GET /api/v1/categories`

Агрегированная сводка по категориям для выбранного запуска.

Пример:

```bash
curl "http://127.0.0.1:8000/api/v1/categories?sort_by=avg_price_rub&sort_order=desc&limit=10"
```

## Где смотреть результаты

Сырые данные:

- `data/books.sqlite`
- `data/raw/book_snapshots.csv`

Проанализированные результаты запусков:

- `artifacts/run_summary.csv` - сводка по запускам;
- `artifacts/category_summary_latest.csv` - сводка по категориям для последнего запуска;
- `artifacts/analysis_summary.json` - краткая итоговая сводка;
- `artifacts/avg_price_rub_by_run.png` - график средней цены в рублях по запускам;
- `artifacts/category_avg_price_latest.png` - график средней цены по категориям.

Артефакты API:

- `artifacts/api_examples/openapi.json` - сохраненная OpenAPI-схема;
- `artifacts/api_examples/health_response.json` - пример ответа healthcheck;
- `artifacts/api_examples/runs_response.json` - пример списка запусков;
- `artifacts/api_examples/books_filtered_response.json` - пример фильтрованной выборки книг;
- `artifacts/api_examples/categories_response.json` - пример агрегатов по категориям;
- `artifacts/api_examples/book_history_response.json` - пример истории книги по `UPC`.

## Тесты

Запуск:

```bash
python3 -m pytest
```

Покрыты базовые сценарии API:

- healthcheck;
- выборка книг по последнему запуску;
- фильтры и сортировка;
- агрегаты по категориям;
- история книги по `UPC`;
- ошибка валидации при слишком большом `limit`.
