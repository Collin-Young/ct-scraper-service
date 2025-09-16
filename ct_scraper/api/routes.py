"""API routes for the CT Scraper service."""
from __future__ import annotations

import datetime as dt
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, or_
from sqlalchemy.orm import Session, selectinload

from .. import schemas
from ..database import get_session
from ..counties import TOWN_TO_COUNTY
from ..models import Case, Party, Subscriber

router = APIRouter()


@router.get("/health", response_model=schemas.HealthOut)
def health() -> schemas.HealthOut:
    return schemas.HealthOut(status="ok", timestamp=dt.datetime.utcnow())


@router.get("/cases", response_model=list[schemas.CaseOut])
def list_cases(
    limit: int = Query(100, ge=1, le=1000),
    since_hours: Optional[int] = Query(None, ge=1, le=720),
    search: Optional[str] = Query(None, min_length=1, max_length=120),
    session: Session = Depends(get_session),
):
    stmt = select(Case).options(selectinload(Case.parties)).order_by(Case.created_at.desc())

    if since_hours:
        cutoff = dt.datetime.utcnow() - dt.timedelta(hours=since_hours)
        stmt = stmt.where(Case.created_at >= cutoff)

    if search:
        pattern = f"%{search.strip()}%"
        stmt = stmt.where(
            or_(
                Case.docket_no.ilike(pattern),
                Case.town.ilike(pattern),
                Case.property_address.ilike(pattern),
            )
        )

    stmt = stmt.limit(limit)
    cases = session.scalars(stmt).all()

    return [
        schemas.CaseOut(
            docket_no=case.docket_no,
            case_url=f"https://civilinquiry.jud.ct.gov/CaseDetail.aspx?DocketNo={case.docket_no}",
            town=case.town,
            county=TOWN_TO_COUNTY.get(case.town, ""),
            case_type=case.case_type,
            court_location=case.court_location,
            property_address=case.property_address,
            list_type=case.list_type,
            trial_list_claim=case.trial_list_claim,
            last_action_date=case.last_action_date,
            latitude=case.latitude,
            longitude=case.longitude,
            created_at=case.created_at,
            parties=[
                schemas.PartyOut(
                    role=party.role,
                    name=party.name,
                    attorney=party.attorney,
                    attorney_address=party.attorney_address,
                    file_date=party.file_date,
                )
                for party in case.parties
            ],
        )
        for case in cases
    ]


@router.post("/subscribers", response_model=schemas.SubscriberOut, status_code=201)
def create_subscriber(
    payload: schemas.SubscriberCreate,
    session: Session = Depends(get_session),
):
    existing = session.scalar(select(Subscriber).where(Subscriber.email == payload.email))
    if existing:
        raise HTTPException(status_code=409, detail="Subscriber already exists")
    subscriber = Subscriber(email=payload.email, is_active=True)
    session.add(subscriber)
    session.commit()
    session.refresh(subscriber)
    return subscriber


@router.get("/subscribers", response_model=list[schemas.SubscriberOut])
def list_subscribers(session: Session = Depends(get_session)):
    stmt = select(Subscriber).order_by(Subscriber.created_at.desc())
    return list(session.scalars(stmt))
