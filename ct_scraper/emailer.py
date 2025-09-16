"""Email digest rendering and delivery helpers."""
from __future__ import annotations

import datetime as dt
import logging
from typing import Iterable, List

try:
    import boto3
except ImportError:  # optional dependency
    boto3 = None  # type: ignore

from jinja2 import Environment, PackageLoader, select_autoescape

from .config import get_settings
from .models import Case, Subscriber

logger = logging.getLogger(__name__)

env = Environment(
    loader=PackageLoader("ct_scraper", "templates"),
    autoescape=select_autoescape(["html", "xml"]),
)

settings = get_settings()


def render_digest(subscriber: Subscriber, cases: Iterable[Case], as_of: dt.datetime) -> str:
    template = env.get_template("digest.html")
    return template.render(subscriber=subscriber, cases=list(cases), generated_at=as_of)


def send_email(recipient: str, subject: str, body_html: str, body_text: str | None = None) -> None:
    provider = settings.email_provider.lower()
    if provider == "ses":
        _send_ses(recipient, subject, body_html, body_text)
    else:
        logger.info("Email send skipped (provider=%s) -> %s", provider, recipient)


def _send_ses(recipient: str, subject: str, body_html: str, body_text: str | None) -> None:
    if boto3 is None:
        raise RuntimeError("boto3 not installed; install optional email extras")
    client = boto3.client("ses", region_name=settings.aws_region)
    message = {
        "Subject": {"Data": subject, "Charset": "UTF-8"},
        "Body": {"Html": {"Data": body_html, "Charset": "UTF-8"}},
    }
    if body_text:
        message["Body"]["Text"] = {"Data": body_text, "Charset": "UTF-8"}
    client.send_email(Source=settings.email_from, Destination={"ToAddresses": [recipient]}, Message=message)


def render_text_fallback(cases: Iterable[Case], as_of: dt.datetime) -> str:
    lines: List[str] = [f"CT Leads Digest – {as_of:%Y-%m-%d %H:%M ET}", ""]
    for case in cases:
        lines.append(f"{case.docket_no} – {case.town} – {case.property_address}")
    return "\n".join(lines)
