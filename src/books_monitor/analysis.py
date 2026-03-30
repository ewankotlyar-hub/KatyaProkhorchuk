from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import pandas as pd

from .config import ARTIFACTS_DIR, SQLITE_PATH


def load_snapshots(db_path: Path = SQLITE_PATH) -> pd.DataFrame:
    with sqlite3.connect(db_path) as connection:
        frame = pd.read_sql_query("SELECT * FROM book_snapshots", connection)
    if frame.empty:
        raise ValueError("Database is empty. Run the scraper first.")
    frame["scraped_at"] = pd.to_datetime(frame["scraped_at"], utc=True)
    frame["is_in_stock"] = frame["is_in_stock"].astype(bool)
    return frame


def select_complete_runs(snapshots: pd.DataFrame) -> tuple[pd.DataFrame, int]:
    run_sizes = snapshots.groupby("run_id")["book_url"].nunique()
    complete_run_size = int(run_sizes.max())
    complete_run_ids = run_sizes[run_sizes == complete_run_size].index
    filtered = snapshots.loc[snapshots["run_id"].isin(complete_run_ids)].copy()
    return filtered, complete_run_size


def _save_average_price_chart(run_summary: pd.DataFrame, output_path: Path) -> None:
    figure, axis = plt.subplots(figsize=(10, 5))
    axis.set_title("Average book price in RUB by run")
    axis.set_ylabel("Average price, RUB")

    if len(run_summary) == 1:
        timestamp_label = run_summary["scraped_at"].dt.strftime("%Y-%m-%d %H:%M UTC").iloc[0]
        value = float(run_summary["avg_price_rub"].iloc[0])
        axis.bar([timestamp_label], [value], color="#2f6b7c", width=0.5)
        axis.scatter([timestamp_label], [value], color="#163d4d", zorder=3)
        axis.set_xlabel("Run timestamp")

        y_margin = max(value * 0.05, 100)
        axis.set_ylim(value - y_margin, value + y_margin)
        axis.text(timestamp_label, value + y_margin * 0.15, f"{value:.2f}", ha="center", va="bottom")
    else:
        axis.plot(run_summary["scraped_at"], run_summary["avg_price_rub"], marker="o", linewidth=2)
        axis.set_xlabel("Run timestamp (UTC)")
        figure.autofmt_xdate()

    axis.grid(alpha=0.3)
    figure.tight_layout()
    figure.savefig(output_path, dpi=150)
    plt.close(figure)


def _save_category_price_chart(category_summary: pd.DataFrame, output_path: Path) -> None:
    top_categories = category_summary.sort_values("avg_price_rub", ascending=False).head(10)
    figure, axis = plt.subplots(figsize=(10, 6))
    axis.barh(top_categories["category"], top_categories["avg_price_rub"], color="#2f6b7c")
    axis.set_title("Top 10 categories by average RUB price")
    axis.set_xlabel("Average price, RUB")
    axis.set_ylabel("Category")
    axis.invert_yaxis()
    figure.tight_layout()
    figure.savefig(output_path, dpi=150)
    plt.close(figure)


def build_artifacts(
    db_path: Path = SQLITE_PATH,
    artifacts_dir: Path = ARTIFACTS_DIR,
) -> dict[str, Path]:
    artifacts_dir.mkdir(parents=True, exist_ok=True)
    snapshots = load_snapshots(db_path=db_path)
    analysis_snapshots, complete_run_size = select_complete_runs(snapshots)

    latest_timestamp = analysis_snapshots["scraped_at"].max()
    latest_snapshot = analysis_snapshots.loc[analysis_snapshots["scraped_at"] == latest_timestamp].copy()
    latest_snapshot.sort_values(["category", "title"], inplace=True)

    run_summary = (
        analysis_snapshots.groupby(["run_id", "scraped_at"], as_index=False)
        .agg(
            total_books=("book_url", "nunique"),
            total_categories=("category", "nunique"),
            avg_price_gbp=("price_gbp", "mean"),
            avg_price_rub=("price_rub", "mean"),
            exchange_rate_gbp_rub=("exchange_rate_gbp_rub", "first"),
            in_stock_books=("is_in_stock", "sum"),
        )
        .sort_values("scraped_at")
    )

    category_summary = (
        latest_snapshot.groupby("category", as_index=False)
        .agg(
            total_books=("book_url", "nunique"),
            avg_price_gbp=("price_gbp", "mean"),
            avg_price_rub=("price_rub", "mean"),
            avg_rating=("rating", "mean"),
            in_stock_share=("is_in_stock", "mean"),
        )
        .sort_values("total_books", ascending=False)
    )

    for column in ["avg_price_gbp", "avg_price_rub", "avg_rating", "in_stock_share"]:
        if column in category_summary:
            category_summary[column] = category_summary[column].round(2)

    run_summary["avg_price_gbp"] = run_summary["avg_price_gbp"].round(2)
    run_summary["avg_price_rub"] = run_summary["avg_price_rub"].round(2)
    run_summary["exchange_rate_gbp_rub"] = run_summary["exchange_rate_gbp_rub"].round(4)

    latest_snapshot_path = artifacts_dir / "latest_snapshot.csv"
    run_summary_path = artifacts_dir / "run_summary.csv"
    category_summary_path = artifacts_dir / "category_summary_latest.csv"
    summary_json_path = artifacts_dir / "analysis_summary.json"
    average_price_chart_path = artifacts_dir / "avg_price_rub_by_run.png"
    category_price_chart_path = artifacts_dir / "category_avg_price_latest.png"

    latest_snapshot.to_csv(latest_snapshot_path, index=False)
    run_summary.to_csv(run_summary_path, index=False)
    category_summary.to_csv(category_summary_path, index=False)

    summary_payload = {
        "raw_total_runs": int(snapshots["run_id"].nunique()),
        "complete_runs_used_for_analysis": int(run_summary["run_id"].nunique()),
        "raw_total_books_collected": int(len(snapshots)),
        "books_per_complete_run": complete_run_size,
        "books_in_latest_run": int(len(latest_snapshot)),
        "latest_run_id": str(latest_snapshot["run_id"].iloc[0]),
        "latest_scraped_at_utc": latest_timestamp.isoformat(),
        "latest_average_price_gbp": float(latest_snapshot["price_gbp"].mean()),
        "latest_average_price_rub": float(latest_snapshot["price_rub"].mean()),
        "latest_exchange_rate_gbp_rub": float(latest_snapshot["exchange_rate_gbp_rub"].iloc[0]),
    }
    summary_json_path.write_text(
        json.dumps(summary_payload, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    _save_average_price_chart(run_summary, average_price_chart_path)
    _save_category_price_chart(category_summary, category_price_chart_path)

    return {
        "latest_snapshot_csv": latest_snapshot_path,
        "run_summary_csv": run_summary_path,
        "category_summary_csv": category_summary_path,
        "analysis_summary_json": summary_json_path,
        "average_price_chart": average_price_chart_path,
        "category_price_chart": category_price_chart_path,
    }
