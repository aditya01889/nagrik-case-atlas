from sqlalchemy import String, Integer, Boolean, Date, DateTime, ForeignKey, Text, JSON, UniqueConstraint, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime, timezone
from .db import Base

def now_utc(): return datetime.now(timezone.utc)

class Constituency(Base):
    __tablename__ = "constituencies"
    id: Mapped[str] = mapped_column(String(100), primary_key=True) # stable ID supplied by boundary registry
    name: Mapped[str] = mapped_column(String(240), index=True)
    state_name: Mapped[str] = mapped_column(String(120), index=True)
    legislature: Mapped[str] = mapped_column(String(30), index=True) # lok_sabha | assembly | rajya_sabha
    boundary_version_id: Mapped[str | None] = mapped_column(String(120), nullable=True)
    geometry_source_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

class Person(Base):
    __tablename__ = "people"
    id: Mapped[str] = mapped_column(String(100), primary_key=True)
    full_name: Mapped[str] = mapped_column(String(240), index=True)
    identity_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)

class Party(Base):
    __tablename__ = "parties"
    id: Mapped[str] = mapped_column(String(100), primary_key=True)
    name: Mapped[str] = mapped_column(String(240), unique=True, index=True)
    abbreviation: Mapped[str | None] = mapped_column(String(40), nullable=True)

class Candidacy(Base):
    __tablename__ = "candidacies"
    id: Mapped[str] = mapped_column(String(100), primary_key=True)
    person_id: Mapped[str] = mapped_column(ForeignKey("people.id"), index=True)
    constituency_id: Mapped[str] = mapped_column(ForeignKey("constituencies.id"), index=True)
    party_id: Mapped[str | None] = mapped_column(ForeignKey("parties.id"), nullable=True, index=True)
    election_date: Mapped[Date] = mapped_column(Date, index=True)
    status: Mapped[str] = mapped_column(String(40), default="contesting") # sitting | contesting | withdrawn | lost | elected
    source_document_id: Mapped[str | None] = mapped_column(ForeignKey("source_documents.id"), nullable=True)
    valid_from: Mapped[Date] = mapped_column(Date, index=True)
    valid_to: Mapped[Date | None] = mapped_column(Date, nullable=True, index=True)
    verification_status: Mapped[str] = mapped_column(String(30), default="unverified", index=True)
    verification_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    person: Mapped[Person] = relationship()
    party: Mapped[Party | None] = relationship()
    constituency: Mapped[Constituency] = relationship()
    __table_args__ = (Index("ix_candidacy_lookup", "constituency_id", "valid_from", "valid_to"),)

class CaseRecord(Base):
    __tablename__ = "case_records"
    id: Mapped[str] = mapped_column(String(100), primary_key=True)
    case_title: Mapped[str] = mapped_column(String(500))
    case_number: Mapped[str | None] = mapped_column(String(180), nullable=True, index=True)
    court_name: Mapped[str | None] = mapped_column(String(300), nullable=True)
    offence_summary: Mapped[str] = mapped_column(Text)
    statutory_provisions: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_serious: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    seriousness_rank: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True) # 1 = highest severity under documented framework
    seriousness_basis: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_document_id: Mapped[str | None] = mapped_column(ForeignKey("source_documents.id"), nullable=True)
    source_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    declared_in_affidavit: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    filed_date: Mapped[Date | None] = mapped_column(Date, nullable=True)
    verification_status: Mapped[str] = mapped_column(String(30), default="unverified", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)

class CasePersonLink(Base):
    __tablename__ = "case_person_links"
    id: Mapped[str] = mapped_column(String(100), primary_key=True)
    case_id: Mapped[str] = mapped_column(ForeignKey("case_records.id"), index=True)
    person_id: Mapped[str] = mapped_column(ForeignKey("people.id"), index=True)
    role: Mapped[str] = mapped_column(String(80), default="accused")
    identity_verification: Mapped[str] = mapped_column(String(30), default="unverified")
    __table_args__ = (UniqueConstraint("case_id", "person_id", name="uq_case_person"),)

class CaseEvent(Base):
    __tablename__ = "case_events"
    id: Mapped[str] = mapped_column(String(100), primary_key=True)
    case_id: Mapped[str] = mapped_column(ForeignKey("case_records.id"), index=True)
    event_type: Mapped[str] = mapped_column(String(80), index=True)
    event_date: Mapped[Date] = mapped_column(Date, index=True)
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc, index=True)
    status_after_event: Mapped[str | None] = mapped_column(String(100), nullable=True)
    summary: Mapped[str] = mapped_column(Text)
    source_document_id: Mapped[str | None] = mapped_column(ForeignKey("source_documents.id"), nullable=True)
    verification_status: Mapped[str] = mapped_column(String(30), default="discovered", index=True)
    verified_by: Mapped[str | None] = mapped_column(String(160), nullable=True)
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    __table_args__ = (Index("ix_case_event_time", "case_id", "event_date", "recorded_at"),)

class SourceDocument(Base):
    __tablename__ = "source_documents"
    id: Mapped[str] = mapped_column(String(100), primary_key=True)
    title: Mapped[str] = mapped_column(String(500))
    source_type: Mapped[str] = mapped_column(String(80), index=True)
    source_url: Mapped[str] = mapped_column(Text)
    published_date: Mapped[Date | None] = mapped_column(Date, nullable=True)
    retrieved_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)
    content_sha256: Mapped[str | None] = mapped_column(String(64), nullable=True)
    raw_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    verification_status: Mapped[str] = mapped_column(String(30), default="discovered", index=True)
    reviewer: Mapped[str | None] = mapped_column(String(160), nullable=True)
    review_notes: Mapped[str | None] = mapped_column(Text, nullable=True)

class BoundaryVersion(Base):
    __tablename__ = "boundary_versions"
    id: Mapped[str] = mapped_column(String(120), primary_key=True)
    legislature: Mapped[str] = mapped_column(String(30), index=True)
    source_url: Mapped[str] = mapped_column(Text)
    source_license: Mapped[str] = mapped_column(String(160))
    effective_from: Mapped[Date] = mapped_column(Date, index=True)
    effective_to: Mapped[Date | None] = mapped_column(Date, nullable=True)
    sha256: Mapped[str | None] = mapped_column(String(64), nullable=True)
    validation_status: Mapped[str] = mapped_column(String(30), default="unverified")
    validation_notes: Mapped[str | None] = mapped_column(Text, nullable=True)

class SourceCheck(Base):
    __tablename__ = "source_checks"
    id: Mapped[str] = mapped_column(String(100), primary_key=True)
    source_document_id: Mapped[str] = mapped_column(ForeignKey("source_documents.id"), index=True)
    checked_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)
    http_status: Mapped[int | None] = mapped_column(Integer, nullable=True)
    observed_sha256: Mapped[str | None] = mapped_column(String(64), nullable=True)
    changed: Mapped[bool] = mapped_column(Boolean, default=False)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
