from __future__ import annotations

import logging
import re
from datetime import datetime, timezone
from typing import Iterator
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from .config import BOOKS_BASE_URL, CATALOGUE_PAGE_URL, DEFAULT_USER_AGENT, EXCHANGE_RATE_URL
from .models import BookSnapshot, ExchangeRate, ScrapeResult, ScrapeRun

logger = logging.getLogger(__name__)

RATING_MAP = {
    "One": 1,
    "Two": 2,
    "Three": 3,
    "Four": 4,
    "Five": 5,
}


def build_session() -> requests.Session:
    session = requests.Session()
    session.headers.update({"User-Agent": DEFAULT_USER_AGENT})
    retry = Retry(
        total=3,
        backoff_factor=1,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=frozenset({"GET"}),
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    return session


def fetch_exchange_rate(session: requests.Session) -> ExchangeRate:
    response = session.get(EXCHANGE_RATE_URL, timeout=20)
    response.raise_for_status()
    payload = response.json()
    rate = payload["rates"]["RUB"]
    return ExchangeRate(
        rate=float(rate),
        provider=payload.get("provider", "open.er-api.com"),
        published_at=payload.get("time_last_update_utc"),
        source_url=EXCHANGE_RATE_URL,
    )


def iterate_catalogue_pages(
    session: requests.Session,
    limit_pages: int | None = None,
) -> Iterator[tuple[int, str, BeautifulSoup]]:
    page_number = 1
    while True:
        if limit_pages is not None and page_number > limit_pages:
            break
        page_url = CATALOGUE_PAGE_URL.format(page_number)
        response = session.get(page_url, timeout=20)
        if response.status_code == 404:
            break
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")
        items = soup.select("article.product_pod")
        if not items:
            break
        yield page_number, page_url, soup
        page_number += 1


def parse_price_gbp(price_text: str) -> float:
    normalized = re.sub(r"[^0-9.]", "", price_text)
    return float(normalized)


def parse_book_detail(session: requests.Session, detail_url: str) -> dict[str, str | bool]:
    response = session.get(detail_url, timeout=20)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")

    breadcrumb_links = soup.select("ul.breadcrumb li a")
    category = breadcrumb_links[-1].get_text(strip=True) if breadcrumb_links else "Unknown"

    availability_node = soup.select_one("p.instock.availability")
    availability = availability_node.get_text(" ", strip=True) if availability_node else "Unknown"

    table_data = {
        row.th.get_text(strip=True): row.td.get_text(strip=True)
        for row in soup.select("table.table.table-striped tr")
    }

    return {
        "category": category,
        "availability": availability,
        "is_in_stock": "In stock" in availability,
        "upc": table_data.get("UPC", ""),
    }


def scrape_catalog(
    limit_pages: int | None = None,
    max_books: int | None = None,
) -> ScrapeResult:
    session = build_session()
    exchange_rate = fetch_exchange_rate(session)
    started_at = datetime.now(timezone.utc)
    run_id = started_at.strftime("%Y%m%dT%H%M%SZ")
    scraped_at = started_at.isoformat(timespec="seconds")

    books: list[BookSnapshot] = []
    processed_pages = 0

    for page_number, page_url, soup in iterate_catalogue_pages(session, limit_pages=limit_pages):
        processed_pages += 1
        for item in soup.select("article.product_pod"):
            title = item.select_one("h3 a")["title"]
            price_text = item.select_one("p.price_color").get_text(strip=True)
            rating_classes = item.select_one("p.star-rating").get("class", [])
            rating = RATING_MAP.get(rating_classes[1]) if len(rating_classes) > 1 else None

            relative_link = item.select_one("h3 a")["href"]
            detail_url = urljoin(page_url, relative_link)

            try:
                detail = parse_book_detail(session, detail_url)
            except requests.RequestException as exc:
                logger.warning("Could not load %s: %s", detail_url, exc)
                detail = {
                    "category": "Unknown",
                    "availability": "Unknown",
                    "is_in_stock": False,
                    "upc": "",
                }

            price_gbp = parse_price_gbp(price_text)
            price_rub = round(price_gbp * exchange_rate.rate, 2)

            books.append(
                BookSnapshot(
                    run_id=run_id,
                    scraped_at=scraped_at,
                    page_number=page_number,
                    book_url=detail_url,
                    title=title,
                    category=str(detail["category"]),
                    upc=str(detail["upc"]),
                    rating=rating,
                    price_gbp=price_gbp,
                    exchange_rate_gbp_rub=exchange_rate.rate,
                    price_rub=price_rub,
                    availability=str(detail["availability"]),
                    is_in_stock=bool(detail["is_in_stock"]),
                )
            )

            if max_books is not None and len(books) >= max_books:
                break

        if max_books is not None and len(books) >= max_books:
            break

    if not books:
        raise RuntimeError("The scraper did not collect any books.")

    return ScrapeResult(
        run=ScrapeRun(
            run_id=run_id,
            scraped_at=scraped_at,
            total_books=len(books),
            total_pages=processed_pages,
            exchange_rate_gbp_rub=exchange_rate.rate,
            exchange_provider=exchange_rate.provider,
            exchange_published_at=exchange_rate.published_at,
            exchange_source_url=exchange_rate.source_url,
        ),
        books=books,
    )
