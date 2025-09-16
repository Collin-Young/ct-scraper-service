"""CLI entrypoint for the daily scrape run."""
from __future__ import annotations

import datetime as dt
import logging
from typing import List

import typer

from ct_scraper.config import get_settings
from ct_scraper.pipeline import init_db, save_cases
from ct_scraper.scrape_cases import CaseScraper
from ct_scraper.towns import TOWNS

app = typer.Typer(help="Run daily CT civil inquiry scrape")
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("scrape_daily")


@app.command()
def run(headless: bool = typer.Option(True, help="Run Chrome in headless mode"),
        limit: int | None = typer.Option(None, help="Limit towns processed for testing")) -> None:
    settings = get_settings()
    logger.info("Starting scrape. headless=%s", headless)
    init_db()
    towns: List[str] = settings.allowed_towns or TOWNS
    if limit:
        towns = towns[:limit]

    with CaseScraper(headless=headless) as scraper:
        rows = list(scraper.scrape_towns(towns))
    inserted = save_cases(rows)
    logger.info("Scrape finished. towns=%d inserted_cases=%d", len(towns), inserted)


@app.command()
def dry_run(limit: int = typer.Option(3, help="Number of towns to fetch")) -> None:
    with CaseScraper(headless=True) as scraper:
        towns = TOWNS[:limit]
        for row in scraper.scrape_towns(towns):
            logger.info("%s | %s | %s", row.town, row.case_type, row.property_address)
            break


if __name__ == "__main__":
    app()
