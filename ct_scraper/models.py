"""Database models."""
from __future__ import annotations

import datetime as dt
from typing import List

from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import declarative_base, Mapped, mapped_column, relationship

Base = declarative_base()


class Case(Base):
    __tablename__ = "cases"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    docket_no: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    town: Mapped[str] = mapped_column(String(80))
    case_type: Mapped[str] = mapped_column(String(120))
    court_location: Mapped[str] = mapped_column(String(120))
    property_address: Mapped[str] = mapped_column(String(255))
    list_type: Mapped[str] = mapped_column(String(120))
    trial_list_claim: Mapped[str] = mapped_column(String(120))
    last_action_date: Mapped[str] = mapped_column(String(40))
    latitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    longitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=dt.datetime.utcnow)
    defendants_json: Mapped[str | None] = mapped_column(Text, nullable=True)

    parties: Mapped[List["Party"]] = relationship("Party", back_populates="case", cascade="all, delete-orphan")


class Party(Base):
    __tablename__ = "parties"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    case_id: Mapped[int] = mapped_column(ForeignKey("cases.id"))
    docket_no: Mapped[str] = mapped_column(String(64), index=True)
    role: Mapped[str] = mapped_column(String(16))
    name: Mapped[str] = mapped_column(String(255))
    attorney: Mapped[str] = mapped_column(String(255), default="")
    mailing_address: Mapped[str] = mapped_column("attorney_address", String(255))
    file_date: Mapped[str] = mapped_column(String(40))

    case: Mapped[Case] = relationship("Case", back_populates="parties")

    __table_args__ = (UniqueConstraint("case_id", "role", "name", name="uq_party_case_role_name"),)


class Subscriber(Base):
    __tablename__ = "subscribers"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    stripe_customer_id: Mapped[str | None] = mapped_column(String(120))
    active_until: Mapped[dt.datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=dt.datetime.utcnow)


class DigestSend(Base):
    __tablename__ = "digest_sends"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    subscriber_id: Mapped[int] = mapped_column(ForeignKey("subscribers.id"))
    sent_at: Mapped[dt.datetime] = mapped_column(DateTime, default=dt.datetime.utcnow)
    cases_sent: Mapped[int] = mapped_column(Integer, default=0)

    subscriber: Mapped[Subscriber] = relationship("Subscriber")
