"""Pydantic response/request models."""
from __future__ import annotations

import datetime as dt
from typing import List, Optional

from pydantic import BaseModel, EmailStr, Field


class PartyOut(BaseModel):
    role: str
    name: str
    attorney: str
    attorney_address: str
    file_date: str


class CaseOut(BaseModel):
    docket_no: str
    case_url: str
    town: str
    county: str
    case_type: str
    court_location: str
    property_address: str
    list_type: str
    trial_list_claim: str
    last_action_date: str
    latitude: float | None
    longitude: float | None
    created_at: dt.datetime
    parties: List[PartyOut] = Field(default_factory=list)

    class Config:
        orm_mode = True


class SubscriberCreate(BaseModel):
    email: EmailStr


class SubscriberOut(BaseModel):
    id: int
    email: EmailStr
    is_active: bool
    active_until: Optional[dt.datetime]

    class Config:
        orm_mode = True


class HealthOut(BaseModel):
    status: str = "ok"
    timestamp: dt.datetime
