"""MO Scraper Database models."""
from __future__ import annotations

import datetime as dt
from typing import List

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import declarative_base, Mapped, mapped_column, relationship

Base = declarative_base()


class Case(Base):
    __tablename__ = "cases"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    date_filed: Mapped[str] = mapped_column(String(40))
    case_number: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    case_url: Mapped[str] = mapped_column(String(255))
    style_of_case: Mapped[str] = mapped_column(String(255))
    case_type: Mapped[str] = mapped_column(String(120))
    location: Mapped[str] = mapped_column(String(120))
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=dt.datetime.utcnow)

    parties: Mapped[List["Party"]] = relationship("Party", back_populates="case", cascade="all, delete-orphan")


class Party(Base):
    __tablename__ = "parties"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    case_id: Mapped[int] = mapped_column(ForeignKey("cases.id"))
    party_index: Mapped[int] = mapped_column(Integer)  # 1-10
    name: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(120))
    address: Mapped[str] = mapped_column(String(255))
    has_attorney: Mapped[bool] = mapped_column(Boolean, default=False)

    case: Mapped[Case] = relationship("Case", back_populates="parties")

    __table_args__ = (UniqueConstraint("case_id", "party_index", name="uq_case_party_index"),)


class CaseType(Base):
    __tablename__ = "case_types"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(120), unique=True)


class DropdownOption(Base):
    __tablename__ = "dropdown_options"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    category: Mapped[str] = mapped_column(String(64))
    value: Mapped[str] = mapped_column(String(255), unique=True)