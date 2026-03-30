from dataclasses import asdict, dataclass
from typing import Any


@dataclass(slots=True)
class ExchangeRate:
    rate: float
    provider: str
    published_at: str | None
    source_url: str


@dataclass(slots=True)
class BookSnapshot:
    run_id: str
    scraped_at: str
    page_number: int
    book_url: str
    title: str
    category: str
    upc: str
    rating: int | None
    price_gbp: float
    exchange_rate_gbp_rub: float
    price_rub: float
    availability: str
    is_in_stock: bool

    def asdict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class ScrapeRun:
    run_id: str
    scraped_at: str
    total_books: int
    total_pages: int
    exchange_rate_gbp_rub: float
    exchange_provider: str
    exchange_published_at: str | None
    exchange_source_url: str

    def asdict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class ScrapeResult:
    run: ScrapeRun
    books: list[BookSnapshot]
