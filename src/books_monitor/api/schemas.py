from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

BookSortField = Literal["scraped_at", "title", "category", "rating", "price_gbp", "price_rub"]
CategorySortField = Literal[
    "category",
    "total_books",
    "avg_price_gbp",
    "avg_price_rub",
    "avg_rating",
    "in_stock_share",
]
RunSortField = Literal["scraped_at", "total_books", "total_pages", "exchange_rate_gbp_rub"]
SortOrder = Literal["asc", "desc"]


class PaginationMeta(BaseModel):
    total: int = Field(..., ge=0)
    limit: int = Field(..., ge=1)
    offset: int = Field(..., ge=0)
    returned: int = Field(..., ge=0)


class DatabaseOverview(BaseModel):
    database_path: str
    total_runs: int = Field(..., ge=0)
    total_snapshots: int = Field(..., ge=0)
    latest_run_id: str | None = None
    latest_scraped_at: str | None = None


class HealthResponse(BaseModel):
    status: Literal["ok"]
    overview: DatabaseOverview


class RunItem(BaseModel):
    run_id: str
    scraped_at: str
    total_books: int = Field(..., ge=0)
    total_pages: int = Field(..., ge=0)
    exchange_rate_gbp_rub: float = Field(..., ge=0)
    exchange_provider: str
    exchange_published_at: str | None = None
    exchange_source_url: str


class RunsResponse(BaseModel):
    meta: PaginationMeta
    sort_by: RunSortField
    sort_order: SortOrder
    items: list[RunItem]


class BookItem(BaseModel):
    run_id: str
    scraped_at: str
    page_number: int = Field(..., ge=1)
    book_url: str
    title: str
    category: str
    upc: str
    rating: int | None = Field(default=None, ge=1, le=5)
    price_gbp: float = Field(..., ge=0)
    exchange_rate_gbp_rub: float = Field(..., ge=0)
    price_rub: float = Field(..., ge=0)
    availability: str
    is_in_stock: bool


class BooksFilters(BaseModel):
    run_id: str | None = None
    category: str | None = None
    min_rating: int | None = Field(default=None, ge=1, le=5)
    max_price_rub: float | None = Field(default=None, ge=0)
    in_stock: bool | None = None
    title_query: str | None = None
    sort_by: BookSortField
    sort_order: SortOrder


class BooksResponse(BaseModel):
    selected_run_id: str
    meta: PaginationMeta
    filters: BooksFilters
    items: list[BookItem]


class CategoryItem(BaseModel):
    category: str
    total_books: int = Field(..., ge=0)
    avg_price_gbp: float = Field(..., ge=0)
    avg_price_rub: float = Field(..., ge=0)
    avg_rating: float | None = Field(default=None, ge=0)
    in_stock_share: float = Field(..., ge=0, le=1)


class CategoriesResponse(BaseModel):
    selected_run_id: str
    meta: PaginationMeta
    sort_by: CategorySortField
    sort_order: SortOrder
    items: list[CategoryItem]


class BookHistoryResponse(BaseModel):
    upc: str
    meta: PaginationMeta
    items: list[BookItem]
