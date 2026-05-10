from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_ROOT / "data"
RAW_DIR = DATA_DIR / "raw"
ARTIFACTS_DIR = PROJECT_ROOT / "artifacts"
WEB_DIR = PROJECT_ROOT / "web"
TEMPLATES_DIR = WEB_DIR / "templates"
STATIC_DIR = WEB_DIR / "static"

SQLITE_PATH = DATA_DIR / "books.sqlite"
RAW_CSV_PATH = RAW_DIR / "book_snapshots.csv"

BOOKS_BASE_URL = "https://books.toscrape.com/"
CATALOGUE_PAGE_URL = BOOKS_BASE_URL + "catalogue/page-{}.html"
EXCHANGE_RATE_URL = "https://open.er-api.com/v6/latest/GBP"

DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/123.0.0.0 Safari/537.36"
)
