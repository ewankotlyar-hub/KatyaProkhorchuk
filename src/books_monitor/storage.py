from __future__ import annotations

import csv
import sqlite3
from pathlib import Path

from .config import RAW_CSV_PATH, SQLITE_PATH
from .models import ScrapeResult

SCHEMA = """
CREATE TABLE IF NOT EXISTS scrape_runs (
    run_id TEXT PRIMARY KEY,
    scraped_at TEXT NOT NULL,
    total_books INTEGER NOT NULL,
    total_pages INTEGER NOT NULL,
    exchange_rate_gbp_rub REAL NOT NULL,
    exchange_provider TEXT NOT NULL,
    exchange_published_at TEXT,
    exchange_source_url TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS book_snapshots (
    run_id TEXT NOT NULL,
    scraped_at TEXT NOT NULL,
    page_number INTEGER NOT NULL,
    book_url TEXT NOT NULL,
    title TEXT NOT NULL,
    category TEXT NOT NULL,
    upc TEXT NOT NULL,
    rating INTEGER,
    price_gbp REAL NOT NULL,
    exchange_rate_gbp_rub REAL NOT NULL,
    price_rub REAL NOT NULL,
    availability TEXT NOT NULL,
    is_in_stock INTEGER NOT NULL,
    PRIMARY KEY (run_id, book_url),
    FOREIGN KEY (run_id) REFERENCES scrape_runs(run_id)
);

CREATE INDEX IF NOT EXISTS idx_book_snapshots_run_id ON book_snapshots(run_id);
CREATE INDEX IF NOT EXISTS idx_book_snapshots_upc ON book_snapshots(upc);
CREATE INDEX IF NOT EXISTS idx_book_snapshots_scraped_at ON book_snapshots(scraped_at);
"""


def ensure_storage(db_path: Path = SQLITE_PATH, csv_path: Path = RAW_CSV_PATH) -> None:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    csv_path.parent.mkdir(parents=True, exist_ok=True)

    with sqlite3.connect(db_path) as connection:
        connection.executescript(SCHEMA)
        connection.commit()


def save_scrape_result(
    result: ScrapeResult,
    db_path: Path = SQLITE_PATH,
    csv_path: Path = RAW_CSV_PATH,
) -> None:
    ensure_storage(db_path=db_path, csv_path=csv_path)

    with sqlite3.connect(db_path) as connection:
        connection.execute(
            """
            INSERT OR REPLACE INTO scrape_runs (
                run_id,
                scraped_at,
                total_books,
                total_pages,
                exchange_rate_gbp_rub,
                exchange_provider,
                exchange_published_at,
                exchange_source_url
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                result.run.run_id,
                result.run.scraped_at,
                result.run.total_books,
                result.run.total_pages,
                result.run.exchange_rate_gbp_rub,
                result.run.exchange_provider,
                result.run.exchange_published_at,
                result.run.exchange_source_url,
            ),
        )

        connection.executemany(
            """
            INSERT OR REPLACE INTO book_snapshots (
                run_id,
                scraped_at,
                page_number,
                book_url,
                title,
                category,
                upc,
                rating,
                price_gbp,
                exchange_rate_gbp_rub,
                price_rub,
                availability,
                is_in_stock
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                (
                    book.run_id,
                    book.scraped_at,
                    book.page_number,
                    book.book_url,
                    book.title,
                    book.category,
                    book.upc,
                    book.rating,
                    book.price_gbp,
                    book.exchange_rate_gbp_rub,
                    book.price_rub,
                    book.availability,
                    int(book.is_in_stock),
                )
                for book in result.books
            ],
        )
        connection.commit()

    file_exists = csv_path.exists()
    with csv_path.open("a", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "run_id",
                "scraped_at",
                "page_number",
                "book_url",
                "title",
                "category",
                "upc",
                "rating",
                "price_gbp",
                "exchange_rate_gbp_rub",
                "price_rub",
                "availability",
                "is_in_stock",
            ],
        )
        if not file_exists:
            writer.writeheader()
        for book in result.books:
            writer.writerow(book.asdict())
