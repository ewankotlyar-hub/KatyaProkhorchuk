from __future__ import annotations

from pathlib import Path

import httpx
import pytest

from books_monitor.api import create_app
from books_monitor.models import BookSnapshot, ScrapeResult, ScrapeRun
from books_monitor.storage import save_scrape_result


def build_result(run_id: str, scraped_at: str, exchange_rate: float, books: list[dict]) -> ScrapeResult:
    snapshots = [
        BookSnapshot(
            run_id=run_id,
            scraped_at=scraped_at,
            page_number=book["page_number"],
            book_url=book["book_url"],
            title=book["title"],
            category=book["category"],
            upc=book["upc"],
            rating=book["rating"],
            price_gbp=book["price_gbp"],
            exchange_rate_gbp_rub=exchange_rate,
            price_rub=book["price_rub"],
            availability=book["availability"],
            is_in_stock=book["is_in_stock"],
        )
        for book in books
    ]
    return ScrapeResult(
        run=ScrapeRun(
            run_id=run_id,
            scraped_at=scraped_at,
            total_books=len(snapshots),
            total_pages=max(book.page_number for book in snapshots),
            exchange_rate_gbp_rub=exchange_rate,
            exchange_provider="test-suite",
            exchange_published_at=scraped_at,
            exchange_source_url="https://example.com/rate",
        ),
        books=snapshots,
    )


def build_app(tmp_path: Path):
    db_path = tmp_path / "books.sqlite"
    csv_path = tmp_path / "book_snapshots.csv"

    run_one = build_result(
        run_id="20260301T100000Z",
        scraped_at="2026-03-01T10:00:00+00:00",
        exchange_rate=111.2,
        books=[
            {
                "page_number": 1,
                "book_url": "https://example.com/books/a",
                "title": "Alpha Poetry",
                "category": "Poetry",
                "upc": "alpha-001",
                "rating": 4,
                "price_gbp": 10.0,
                "price_rub": 1112.0,
                "availability": "In stock",
                "is_in_stock": True,
            },
            {
                "page_number": 1,
                "book_url": "https://example.com/books/b",
                "title": "Beta Science",
                "category": "Science",
                "upc": "beta-001",
                "rating": 2,
                "price_gbp": 14.0,
                "price_rub": 1556.8,
                "availability": "Out of stock",
                "is_in_stock": False,
            },
        ],
    )
    run_two = build_result(
        run_id="20260315T100000Z",
        scraped_at="2026-03-15T10:00:00+00:00",
        exchange_rate=113.5,
        books=[
            {
                "page_number": 1,
                "book_url": "https://example.com/books/a",
                "title": "Alpha Poetry",
                "category": "Poetry",
                "upc": "alpha-001",
                "rating": 5,
                "price_gbp": 10.0,
                "price_rub": 1135.0,
                "availability": "In stock",
                "is_in_stock": True,
            },
            {
                "page_number": 1,
                "book_url": "https://example.com/books/c",
                "title": "Gamma Travel",
                "category": "Travel",
                "upc": "gamma-001",
                "rating": 3,
                "price_gbp": 8.0,
                "price_rub": 908.0,
                "availability": "In stock",
                "is_in_stock": True,
            },
        ],
    )

    save_scrape_result(run_one, db_path=db_path, csv_path=csv_path)
    save_scrape_result(run_two, db_path=db_path, csv_path=csv_path)

    return create_app(db_path=db_path)


async def api_get(app, path: str, params: dict | None = None) -> httpx.Response:
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        return await client.get(path, params=params)


pytestmark = pytest.mark.anyio


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


async def test_healthcheck_returns_database_overview(tmp_path: Path) -> None:
    app = build_app(tmp_path)

    response = await api_get(app, "/api/v1/health")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["overview"]["total_runs"] == 2
    assert payload["overview"]["total_snapshots"] == 4
    assert payload["overview"]["latest_run_id"] == "20260315T100000Z"


async def test_root_returns_catalog_page(tmp_path: Path) -> None:
    app = build_app(tmp_path)

    response = await api_get(app, "/")

    assert response.status_code == 200
    assert "BookScope" in response.text
    assert "/static/js/catalog.js" in response.text


async def test_books_endpoint_uses_latest_run_by_default(tmp_path: Path) -> None:
    app = build_app(tmp_path)

    response = await api_get(app, "/api/v1/books", params={"limit": 1})

    assert response.status_code == 200
    payload = response.json()
    assert payload["selected_run_id"] == "20260315T100000Z"
    assert payload["meta"]["total"] == 2
    assert payload["meta"]["returned"] == 1
    assert len(payload["items"]) == 1


async def test_books_filters_and_sorting_work(tmp_path: Path) -> None:
    app = build_app(tmp_path)

    response = await api_get(
        app,
        "/api/v1/books",
        params={
            "category": "Poetry",
            "in_stock": "true",
            "min_rating": 4,
            "sort_by": "price_rub",
            "sort_order": "asc",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["meta"]["total"] == 1
    assert payload["items"][0]["title"] == "Alpha Poetry"
    assert payload["items"][0]["price_rub"] == 1135.0


async def test_categories_endpoint_returns_aggregates(tmp_path: Path) -> None:
    app = build_app(tmp_path)

    response = await api_get(
        app,
        "/api/v1/categories",
        params={"sort_by": "category", "sort_order": "asc"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["selected_run_id"] == "20260315T100000Z"
    assert payload["meta"]["total"] == 2
    assert payload["items"][0]["category"] == "Poetry"


async def test_book_history_returns_multiple_runs(tmp_path: Path) -> None:
    app = build_app(tmp_path)

    response = await api_get(app, "/api/v1/books/alpha-001/history")

    assert response.status_code == 200
    payload = response.json()
    assert payload["meta"]["total"] == 2
    assert payload["items"][0]["run_id"] == "20260315T100000Z"
    assert payload["items"][1]["run_id"] == "20260301T100000Z"


async def test_books_limit_is_validated(tmp_path: Path) -> None:
    app = build_app(tmp_path)

    response = await api_get(app, "/api/v1/books", params={"limit": 1000})

    assert response.status_code == 422
