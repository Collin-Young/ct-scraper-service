"""Data pipeline utilities for storing cases and preparing digests."""
from __future__ import annotations

import datetime as dt
import re
import sqlite3
from pathlib import Path
from typing import Iterable, List

from sqlalchemy import select

from .config import get_settings
from .database import engine, session_scope
from .geocode import geocode_address
from .models import Base, Case, DigestSend, Party, Subscriber
from .scrape_cases import CaseRow

HYPERLINK_RE = re.compile(r"DocketNo=([A-Z0-9]+)")


def init_db() -> None:
    settings = get_settings()
    db_path: Path | None = None
    if settings.database_url.startswith("sqlite"):
        raw_path = settings.database_url.replace("sqlite:///", "", 1)
        if raw_path:
            db_path = Path(raw_path)
            if not db_path.parent.exists():
                db_path.parent.mkdir(parents=True, exist_ok=True)
    Base.metadata.create_all(bind=engine)

    if db_path and db_path.exists():
        with sqlite3.connect(db_path) as conn:
            columns = {row[1] for row in conn.execute("PRAGMA table_info(cases)")}
            if "latitude" not in columns:
                conn.execute("ALTER TABLE cases ADD COLUMN latitude REAL")
            if "longitude" not in columns:
                conn.execute("ALTER TABLE cases ADD COLUMN longitude REAL")
            if "defendants_json" not in columns:
                conn.execute("ALTER TABLE cases ADD COLUMN defendants_json TEXT")


def save_cases(rows: Iterable[CaseRow]) -> int:
    inserted = 0
    with session_scope() as session:
        for row in rows:
            docket = _extract_docket(row.docket_link)
            if not docket:
                continue
            existing = session.scalar(select(Case).where(Case.docket_no == docket))
            if existing:
                continue
            coords = geocode_address(row.property_address, row.town)
            case = Case(
                docket_no=docket,
                town=row.town,
                case_type=row.case_type,
                court_location=row.court_location,
                property_address=row.property_address,
                list_type=row.list_type,
                trial_list_claim=row.trial_list_claim,
                last_action_date=row.last_action_date,
                latitude=coords[0] if coords else None,
                longitude=coords[1] if coords else None,
            )
            session.add(case)
            session.flush()
            for party in row.parties:
                session.add(
                    Party(
                        case_id=case.id,
                        role=party.get("role", ""),
                        name=party.get("name", ""),
                        attorney=party.get("attorney", ""),
                        attorney_address=party.get("address", ""),
                        file_date=party.get("file_date", ""),
                    )
                )
            inserted += 1
    return inserted


def get_new_cases_for_digest(since: dt.datetime) -> List[Case]:
    with session_scope() as session:
        stmt = select(Case).where(Case.created_at >= since).order_by(Case.created_at.desc())
        return list(session.scalars(stmt))


def record_digest_send(subscriber_id: int, count: int) -> None:
    with session_scope() as session:
        session.add(DigestSend(subscriber_id=subscriber_id, cases_sent=count))


def active_subscribers(as_of: dt.datetime | None = None) -> List[Subscriber]:
    now = as_of or dt.datetime.utcnow()
    with session_scope() as session:
        stmt = select(Subscriber).where(Subscriber.is_active.is_(True))
        users = list(session.scalars(stmt))
    return [s for s in users if s.active_until is None or s.active_until >= now]


def _extract_docket(link: str) -> str:
    if not link:
        return ""
    match = HYPERLINK_RE.search(link)
    if match:
        return match.group(1)
    return link.strip().strip('"')
