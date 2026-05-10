from __future__ import annotations

from pathlib import Path
from typing import Annotated

from fastapi import FastAPI, HTTPException, Query
from fastapi.staticfiles import StaticFiles

from books_monitor.config import SQLITE_PATH, STATIC_DIR
from books_monitor.query_service import (
    MAX_PAGE_SIZE,
    BooksQuery,
    BooksQueryService,
    CategoriesQuery,
    DataNotReadyError,
    ResourceNotFoundError,
    RunsQuery,
)
from books_monitor.web import WebRouterFactory

from .schemas import (
    BookHistoryResponse,
    BooksResponse,
    BookSortField,
    CategoriesResponse,
    CategorySortField,
    HealthResponse,
    RunsResponse,
    RunSortField,
    SortOrder,
)


def create_app(db_path: Path = SQLITE_PATH) -> FastAPI:
    app = FastAPI(
        title="Books Monitor API",
        version="1.0.0",
        summary="API для выборок по данным скрапера books.toscrape.com",
        description=(
            "API отдает небольшие срезы данных из SQLite-базы, собранной скрапером. "
            "Полная выгрузка базы через один запрос запрещена: все списковые эндпоинты "
            "имеют пагинацию и ограничение `limit <= 50`."
        ),
    )
    service = BooksQueryService(db_path=db_path)
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
    app.include_router(WebRouterFactory().create_router())

    @app.get("/api/v1/health", response_model=HealthResponse, tags=["system"])
    async def healthcheck() -> HealthResponse:
        overview = _handle_service_errors(service.fetch_overview)
        return HealthResponse(status="ok", overview=overview)

    @app.get("/api/v1/runs", response_model=RunsResponse, tags=["runs"])
    async def get_runs(
        limit: Annotated[int, Query(ge=1, le=MAX_PAGE_SIZE)] = 10,
        offset: Annotated[int, Query(ge=0)] = 0,
        sort_by: Annotated[RunSortField, Query()] = "scraped_at",
        sort_order: Annotated[SortOrder, Query()] = "desc",
    ) -> RunsResponse:
        items, total = _handle_service_errors(
            service.list_runs,
            RunsQuery(limit=limit, offset=offset, sort_by=sort_by, sort_order=sort_order),
        )
        return RunsResponse(
            meta={
                "total": total,
                "limit": limit,
                "offset": offset,
                "returned": len(items),
            },
            sort_by=sort_by,
            sort_order=sort_order,
            items=items,
        )

    @app.get("/api/v1/books", response_model=BooksResponse, tags=["books"])
    async def get_books(
        limit: Annotated[int, Query(ge=1, le=MAX_PAGE_SIZE)] = 10,
        offset: Annotated[int, Query(ge=0)] = 0,
        run_id: Annotated[str | None, Query(min_length=6, max_length=32)] = None,
        category: Annotated[str | None, Query(min_length=1, max_length=80)] = None,
        min_rating: Annotated[int | None, Query(ge=1, le=5)] = None,
        max_price_rub: Annotated[float | None, Query(ge=0)] = None,
        in_stock: bool | None = None,
        title_query: Annotated[str | None, Query(min_length=1, max_length=100)] = None,
        sort_by: Annotated[BookSortField, Query()] = "scraped_at",
        sort_order: Annotated[SortOrder, Query()] = "desc",
    ) -> BooksResponse:
        items, total, selected_run_id = _handle_service_errors(
            service.list_books,
            BooksQuery(
                run_id=run_id,
                category=category,
                min_rating=min_rating,
                max_price_rub=max_price_rub,
                in_stock=in_stock,
                title_query=title_query,
                limit=limit,
                offset=offset,
                sort_by=sort_by,
                sort_order=sort_order,
            ),
        )
        return BooksResponse(
            selected_run_id=selected_run_id,
            meta={
                "total": total,
                "limit": limit,
                "offset": offset,
                "returned": len(items),
            },
            filters={
                "run_id": run_id,
                "category": category,
                "min_rating": min_rating,
                "max_price_rub": max_price_rub,
                "in_stock": in_stock,
                "title_query": title_query,
                "sort_by": sort_by,
                "sort_order": sort_order,
            },
            items=items,
        )

    @app.get("/api/v1/books/{upc}/history", response_model=BookHistoryResponse, tags=["books"])
    async def get_book_history(
        upc: str,
        limit: Annotated[int, Query(ge=1, le=MAX_PAGE_SIZE)] = 10,
    ) -> BookHistoryResponse:
        items = _handle_service_errors(service.get_book_history, upc, limit)
        return BookHistoryResponse(
            upc=upc,
            meta={
                "total": len(items),
                "limit": limit,
                "offset": 0,
                "returned": len(items),
            },
            items=items,
        )

    @app.get("/api/v1/categories", response_model=CategoriesResponse, tags=["categories"])
    async def get_categories(
        limit: Annotated[int, Query(ge=1, le=MAX_PAGE_SIZE)] = 10,
        offset: Annotated[int, Query(ge=0)] = 0,
        run_id: Annotated[str | None, Query(min_length=6, max_length=32)] = None,
        sort_by: Annotated[CategorySortField, Query()] = "avg_price_rub",
        sort_order: Annotated[SortOrder, Query()] = "desc",
    ) -> CategoriesResponse:
        items, total, selected_run_id = _handle_service_errors(
            service.list_categories,
            CategoriesQuery(
                run_id=run_id,
                limit=limit,
                offset=offset,
                sort_by=sort_by,
                sort_order=sort_order,
            ),
        )
        return CategoriesResponse(
            selected_run_id=selected_run_id,
            meta={
                "total": total,
                "limit": limit,
                "offset": offset,
                "returned": len(items),
            },
            sort_by=sort_by,
            sort_order=sort_order,
            items=items,
        )

    return app


def _handle_service_errors(func, *args):
    try:
        return func(*args)
    except ResourceNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except DataNotReadyError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


app = create_app()
