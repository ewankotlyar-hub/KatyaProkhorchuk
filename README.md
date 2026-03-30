# Books to Scrape Monitor

Проект для непрерывного скрапинга `books.toscrape.com` с накоплением данных в SQLite/CSV и последующим анализом запусков.

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
        ├── config.py
        ├── flow.py
        ├── models.py
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
