from __future__ import annotations

import argparse
import importlib.util
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from books_monitor.analysis import build_artifacts
from books_monitor.config import SQLITE_PATH
from books_monitor.scraper import scrape_catalog
from books_monitor.storage import save_scrape_result


def ensure_prefect_dependencies() -> str | None:
    required_modules = [
        "prefect",
        "pydantic",
        "anyio",
        "sqlalchemy",
    ]
    for module_name in required_modules:
        if importlib.util.find_spec(module_name) is None:
            return module_name
    return None


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Continuous scraper for books.toscrape.com",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    scrape_parser = subparsers.add_parser("scrape", help="Run one scraping cycle")
    scrape_parser.add_argument("--limit-pages", type=int, default=None, help="Limit catalogue pages")
    scrape_parser.add_argument("--max-books", type=int, default=None, help="Limit number of books")
    scrape_parser.add_argument(
        "--skip-analysis",
        action="store_true",
        help="Skip artifact generation after scraping",
    )

    analyze_parser = subparsers.add_parser("analyze", help="Build analysis artifacts from the database")
    analyze_parser.add_argument("--db-path", default=None, help="Optional custom SQLite database path")

    pipeline_parser = subparsers.add_parser("pipeline", help="Run the Prefect flow once")
    pipeline_parser.add_argument("--limit-pages", type=int, default=None, help="Limit catalogue pages")
    pipeline_parser.add_argument("--max-books", type=int, default=None, help="Limit number of books")
    pipeline_parser.add_argument(
        "--skip-analysis",
        action="store_true",
        help="Skip artifact generation inside the Prefect flow",
    )

    serve_parser = subparsers.add_parser("serve", help="Serve the Prefect flow on a cron schedule")
    serve_parser.add_argument(
        "--interval-hours",
        type=int,
        default=6,
        help="Run the flow every N hours",
    )

    return parser


def run_scrape(args: argparse.Namespace) -> int:
    result = scrape_catalog(limit_pages=args.limit_pages, max_books=args.max_books)
    save_scrape_result(result)
    print(f"Run ID: {result.run.run_id}")
    print(f"Books collected: {len(result.books)}")
    print(f"Pages collected: {result.run.total_pages}")
    print(f"GBP/RUB rate: {result.run.exchange_rate_gbp_rub:.4f}")

    if not args.skip_analysis:
        artifacts = build_artifacts()
        print("Artifacts updated:")
        for name, path in artifacts.items():
            print(f"  {name}: {path}")
    return 0


def run_analysis(args: argparse.Namespace) -> int:
    db_path = Path(args.db_path) if args.db_path else SQLITE_PATH
    artifacts = build_artifacts(db_path=db_path)
    print("Artifacts updated:")
    for name, path in artifacts.items():
        print(f"  {name}: {path}")
    return 0


def run_pipeline(args: argparse.Namespace) -> int:
    missing_module = ensure_prefect_dependencies()
    if missing_module is not None:
        print("Prefect is not available in the current environment.")
        print("Install dependencies from requirements.txt and try again.")
        print(f"Missing module: {missing_module}")
        return 1

    try:
        from books_monitor.flow import books_pipeline
    except ImportError as exc:
        print("Prefect is not available in the current environment.")
        print("Install dependencies from requirements.txt and try again.")
        print(f"Original import error: {exc}")
        return 1

    result = books_pipeline(
        limit_pages=args.limit_pages,
        max_books=args.max_books,
        run_analysis=not args.skip_analysis,
    )
    print(result)
    return 0


def run_serve(args: argparse.Namespace) -> int:
    missing_module = ensure_prefect_dependencies()
    if missing_module is not None:
        print("Prefect is not available in the current environment.")
        print("Install dependencies from requirements.txt and try again.")
        print(f"Missing module: {missing_module}")
        return 1

    try:
        from books_monitor.flow import serve_pipeline
    except ImportError as exc:
        print("Prefect is not available in the current environment.")
        print("Install dependencies from requirements.txt and try again.")
        print(f"Original import error: {exc}")
        return 1

    serve_pipeline(interval_hours=args.interval_hours)
    return 0


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    if args.command == "scrape":
        return run_scrape(args)
    if args.command == "analyze":
        return run_analysis(args)
    if args.command == "pipeline":
        return run_pipeline(args)
    if args.command == "serve":
        return run_serve(args)

    parser.error(f"Unknown command: {args.command}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
