from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .config import SQLITE_PATH

DEFAULT_PAGE_SIZE = 10
MAX_PAGE_SIZE = 50

BOOK_SORT_FIELDS = {
    "scraped_at": "bs.scraped_at",
    "title": "bs.title",
    "category": "bs.category",
    "rating": "bs.rating",
    "price_gbp": "bs.price_gbp",
    "price_rub": "bs.price_rub",
}

RUN_SORT_FIELDS = {
    "scraped_at": "scraped_at",
    "total_books": "total_books",
    "total_pages": "total_pages",
    "exchange_rate_gbp_rub": "exchange_rate_gbp_rub",
}

CATEGORY_SORT_FIELDS = {
    "category": "category",
    "total_books": "total_books",
    "avg_price_gbp": "avg_price_gbp",
    "avg_price_rub": "avg_price_rub",
    "avg_rating": "avg_rating",
    "in_stock_share": "in_stock_share",
}


class QueryServiceError(RuntimeError):
    """Base error for read-only API queries."""


class DataNotReadyError(QueryServiceError):
    """Raised when the database does not exist or has no rows yet."""


class ResourceNotFoundError(QueryServiceError):
    """Raised when a specific run/book cannot be found."""


@dataclass(slots=True, frozen=True)
class BooksQuery:
    run_id: str | None = None
    category: str | None = None
    min_rating: int | None = None
    max_price_rub: float | None = None
    in_stock: bool | None = None
    title_query: str | None = None
    limit: int = DEFAULT_PAGE_SIZE
    offset: int = 0
    sort_by: str = "scraped_at"
    sort_order: str = "desc"


@dataclass(slots=True, frozen=True)
class RunsQuery:
    limit: int = DEFAULT_PAGE_SIZE
    offset: int = 0
    sort_by: str = "scraped_at"
    sort_order: str = "desc"


@dataclass(slots=True, frozen=True)
class CategoriesQuery:
    run_id: str | None = None
    limit: int = DEFAULT_PAGE_SIZE
    offset: int = 0
    sort_by: str = "avg_price_rub"
    sort_order: str = "desc"


class BooksQueryService:
    def __init__(self, db_path: Path = SQLITE_PATH) -> None:
        self.db_path = Path(db_path)

    def fetch_overview(self) -> dict[str, Any]:
        with self._connect() as connection:
            latest = connection.execute(
                """
                SELECT run_id, scraped_at
                FROM scrape_runs
                ORDER BY scraped_at DESC
                LIMIT 1
                """,
            ).fetchone()

            return {
                "database_path": str(self.db_path),
                "total_runs": connection.execute("SELECT COUNT(*) FROM scrape_runs").fetchone()[0],
                "total_snapshots": connection.execute("SELECT COUNT(*) FROM book_snapshots").fetchone()[0],
                "latest_run_id": latest["run_id"] if latest else None,
                "latest_scraped_at": latest["scraped_at"] if latest else None,
            }

    def list_runs(self, query: RunsQuery) -> tuple[list[dict[str, Any]], int]:
        sort_column = RUN_SORT_FIELDS[query.sort_by]
        direction = self._normalize_direction(query.sort_order)

        with self._connect() as connection:
            total = connection.execute("SELECT COUNT(*) FROM scrape_runs").fetchone()[0]
            rows = connection.execute(
                f"""
                SELECT
                    run_id,
                    scraped_at,
                    total_books,
                    total_pages,
                    exchange_rate_gbp_rub,
                    exchange_provider,
                    exchange_published_at,
                    exchange_source_url
                FROM scrape_runs
                ORDER BY {sort_column} {direction}, run_id DESC
                LIMIT ? OFFSET ?
                """,
                (query.limit, query.offset),
            ).fetchall()

        return [dict(row) for row in rows], int(total)

    def list_books(self, query: BooksQuery) -> tuple[list[dict[str, Any]], int, str]:
        sort_column = BOOK_SORT_FIELDS[query.sort_by]
        direction = self._normalize_direction(query.sort_order)

        with self._connect() as connection:
            selected_run_id = self._resolve_run_id(connection, query.run_id)
            filters, params = self._build_book_filters(selected_run_id, query)
            where_clause = " AND ".join(filters)

            total = connection.execute(
                f"SELECT COUNT(*) FROM book_snapshots bs WHERE {where_clause}",
                params,
            ).fetchone()[0]

            rows = connection.execute(
                f"""
                SELECT
                    bs.run_id,
                    bs.scraped_at,
                    bs.page_number,
                    bs.book_url,
                    bs.title,
                    bs.category,
                    bs.upc,
                    bs.rating,
                    bs.price_gbp,
                    bs.exchange_rate_gbp_rub,
                    bs.price_rub,
                    bs.availability,
                    bs.is_in_stock
                FROM book_snapshots bs
                WHERE {where_clause}
                ORDER BY {sort_column} {direction}, bs.title ASC, bs.book_url ASC
                LIMIT ? OFFSET ?
                """,
                (*params, query.limit, query.offset),
            ).fetchall()

        return [self._serialize_book_row(row) for row in rows], int(total), selected_run_id

    def list_categories(self, query: CategoriesQuery) -> tuple[list[dict[str, Any]], int, str]:
        sort_column = CATEGORY_SORT_FIELDS[query.sort_by]
        direction = self._normalize_direction(query.sort_order)

        with self._connect() as connection:
            selected_run_id = self._resolve_run_id(connection, query.run_id)
            total = connection.execute(
                "SELECT COUNT(DISTINCT category) FROM book_snapshots WHERE run_id = ?",
                (selected_run_id,),
            ).fetchone()[0]

            rows = connection.execute(
                f"""
                SELECT
                    category,
                    COUNT(*) AS total_books,
                    ROUND(AVG(price_gbp), 2) AS avg_price_gbp,
                    ROUND(AVG(price_rub), 2) AS avg_price_rub,
                    ROUND(AVG(rating), 2) AS avg_rating,
                    ROUND(AVG(is_in_stock), 4) AS in_stock_share
                FROM book_snapshots
                WHERE run_id = ?
                GROUP BY category
                ORDER BY {sort_column} {direction}, category ASC
                LIMIT ? OFFSET ?
                """,
                (selected_run_id, query.limit, query.offset),
            ).fetchall()

        return [dict(row) for row in rows], int(total), selected_run_id

    def get_book_history(self, upc: str, limit: int) -> list[dict[str, Any]]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT
                    bs.run_id,
                    bs.scraped_at,
                    bs.page_number,
                    bs.book_url,
                    bs.title,
                    bs.category,
                    bs.upc,
                    bs.rating,
                    bs.price_gbp,
                    bs.exchange_rate_gbp_rub,
                    bs.price_rub,
                    bs.availability,
                    bs.is_in_stock
                FROM book_snapshots bs
                WHERE bs.upc = ?
                ORDER BY bs.scraped_at DESC, bs.run_id DESC
                LIMIT ?
                """,
                (upc, limit),
            ).fetchall()

        if not rows:
            raise ResourceNotFoundError(f"Book with UPC '{upc}' was not found.")

        return [self._serialize_book_row(row) for row in rows]

    def _connect(self) -> sqlite3.Connection:
        if not self.db_path.exists():
            raise DataNotReadyError(
                f"Database file '{self.db_path}' was not found. Run the scraper first.",
            )

        connection = sqlite3.connect(self.db_path)
        connection.row_factory = sqlite3.Row

        try:
            self._validate_storage(connection)
        except Exception:
            connection.close()
            raise

        return connection

    @staticmethod
    def _validate_storage(connection: sqlite3.Connection) -> None:
        tables = {
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'",
            ).fetchall()
        }
        required_tables = {"scrape_runs", "book_snapshots"}
        if not required_tables.issubset(tables):
            raise DataNotReadyError("Database schema is incomplete. Run the scraper first.")

    @staticmethod
    def _normalize_direction(value: str) -> str:
        return "ASC" if value.lower() == "asc" else "DESC"

    @staticmethod
    def _serialize_book_row(row: sqlite3.Row) -> dict[str, Any]:
        payload = dict(row)
        payload["is_in_stock"] = bool(payload["is_in_stock"])
        return payload

    @staticmethod
    def _build_book_filters(selected_run_id: str, query: BooksQuery) -> tuple[list[str], list[Any]]:
        filters = ["bs.run_id = ?"]
        params: list[Any] = [selected_run_id]

        if query.category:
            filters.append("bs.category = ?")
            params.append(query.category)
        if query.min_rating is not None:
            filters.append("bs.rating >= ?")
            params.append(query.min_rating)
        if query.max_price_rub is not None:
            filters.append("bs.price_rub <= ?")
            params.append(query.max_price_rub)
        if query.in_stock is not None:
            filters.append("bs.is_in_stock = ?")
            params.append(int(query.in_stock))
        if query.title_query:
            filters.append("LOWER(bs.title) LIKE ?")
            params.append(f"%{query.title_query.strip().lower()}%")

        return filters, params

    def _resolve_run_id(self, connection: sqlite3.Connection, requested_run_id: str | None) -> str:
        if requested_run_id:
            existing = connection.execute(
                "SELECT 1 FROM scrape_runs WHERE run_id = ?",
                (requested_run_id,),
            ).fetchone()
            if existing is None:
                raise ResourceNotFoundError(f"Run '{requested_run_id}' was not found.")
            return requested_run_id

        latest = connection.execute(
            """
            SELECT run_id
            FROM scrape_runs
            ORDER BY scraped_at DESC
            LIMIT 1
            """,
        ).fetchone()
        if latest is None:
            raise DataNotReadyError("Database is empty. Run the scraper first.")
        return str(latest["run_id"])
