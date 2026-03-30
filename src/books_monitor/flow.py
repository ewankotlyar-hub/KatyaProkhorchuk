from __future__ import annotations

from prefect import flow, get_run_logger

from .analysis import build_artifacts
from .scraper import scrape_catalog
from .storage import save_scrape_result


@flow(name="books-to-scrape-monitor", log_prints=True)
def books_pipeline(
    limit_pages: int | None = None,
    max_books: int | None = None,
    run_analysis: bool = True,
) -> dict[str, object]:
    logger = get_run_logger()
    result = scrape_catalog(limit_pages=limit_pages, max_books=max_books)
    save_scrape_result(result)
    logger.info("Saved %s books for run %s", len(result.books), result.run.run_id)

    artifacts: dict[str, str] = {}
    if run_analysis:
        artifacts = {
            key: str(path)
            for key, path in build_artifacts().items()
        }
        logger.info("Artifacts updated: %s", ", ".join(sorted(artifacts)))

    return {
        "run_id": result.run.run_id,
        "total_books": len(result.books),
        "total_pages": result.run.total_pages,
        "artifacts": artifacts,
    }


def serve_pipeline(interval_hours: int = 6) -> None:
    books_pipeline.serve(
        name="books-to-scrape-monitor",
        cron=f"0 */{interval_hours} * * *",
    )
