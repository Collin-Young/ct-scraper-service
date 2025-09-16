"""CLI entrypoint to send daily digest emails."""
from __future__ import annotations

import datetime as dt
import logging

import typer

from ct_scraper.config import get_settings
from ct_scraper.emailer import render_digest, render_text_fallback, send_email
from ct_scraper.pipeline import active_subscribers, get_new_cases_for_digest, record_digest_send

app = typer.Typer(help="Send subscriber digest emails")
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("send_digest")


@app.command()
def run(hours: int = typer.Option(24, help="Look back window for new cases"),
        override_subject: str | None = typer.Option(None, help="Custom email subject")) -> None:
    settings = get_settings()
    cutoff = dt.datetime.utcnow() - dt.timedelta(hours=hours)
    cases = get_new_cases_for_digest(cutoff)
    if not cases:
        logger.info("No new cases to include in digest")
        return

    subscribers = active_subscribers()
    if not subscribers:
        logger.info("No active subscribers found")
        return

    subject = override_subject or f"CT Leads Digest – {dt.datetime.utcnow():%Y-%m-%d}"
    for subscriber in subscribers:
        body_html = render_digest(subscriber, cases, dt.datetime.utcnow())
        body_text = render_text_fallback(cases, dt.datetime.utcnow())
        send_email(subscriber.email, subject, body_html, body_text)
        record_digest_send(subscriber.id, len(cases))
        logger.info("Sent digest to %s with %d cases", subscriber.email, len(cases))


if __name__ == "__main__":
    app()
