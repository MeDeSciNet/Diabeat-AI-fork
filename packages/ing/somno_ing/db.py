"""Database models and session handling.

Timescale is used where it earns its keep - the one-row-per-second signal
summary - and plain relational tables everywhere else. The schema is created
through SQLAlchemy so the same code runs on SQLite (tests, `make demo` without
docker) and PostgreSQL/TimescaleDB (compose, production-shaped runs).
"""

from __future__ import annotations

from contextlib import contextmanager
from datetime import UTC, datetime

from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    create_engine,
    text,
)
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from .settings import get_settings


class Base(DeclarativeBase):
    pass


def _now() -> datetime:
    return datetime.now(UTC)


def aware(dt: datetime | None) -> datetime | None:
    """Attach UTC to a timestamp read back from the database.

    SQLite has no timezone type, so a value written as aware comes back naive
    and any comparison against ``datetime.now(UTC)`` raises. Everything stored
    here is UTC, so re-attaching it is exact rather than a guess.
    """
    if dt is None or dt.tzinfo is not None:
        return dt
    return dt.replace(tzinfo=UTC)


class Subject(Base):
    __tablename__ = "subjects"
    # Pseudonymous only. PRD 10.2 forbids storing names or identifiers here; any
    # re-identification table lives outside this database with its own access
    # control.
    subject_code = Column(String, primary_key=True)
    display_label = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), default=_now)


class Bed(Base):
    __tablename__ = "beds"
    bed_id = Column(String, primary_key=True)
    ward = Column(String, nullable=True)
    subject_code = Column(String, ForeignKey("subjects.subject_code"), nullable=True)
    has_pam = Column(Boolean, default=False)


class Device(Base):
    __tablename__ = "devices"
    device_id = Column(String, primary_key=True)
    bed_id = Column(String, nullable=True)
    last_seen_at = Column(DateTime(timezone=True), nullable=True)
    battery_pct = Column(Float, nullable=True)
    storage_free_pct = Column(Float, nullable=True)
    electrode_ok = Column(Boolean, nullable=True)


class Session(Base):
    __tablename__ = "sessions"
    id = Column(String, primary_key=True)
    subject_code = Column(String, index=True, nullable=False)
    device_id = Column(String, index=True, nullable=False)
    bed_id = Column(String, index=True, nullable=True)
    status = Column(String, default="recording")
    started_at = Column(DateTime(timezone=True), default=_now)
    ended_at = Column(DateTime(timezone=True), nullable=True)
    duration_ms = Column(Integer, nullable=True)
    scenario = Column(String, nullable=True)
    seed = Column(Integer, nullable=True)
    sample_rates = Column(JSON, default=dict)
    gaps = Column(JSON, default=list)
    chunks_received = Column(Integer, default=0)
    chunks_expected = Column(Integer, nullable=True)
    analysis_error = Column(Text, nullable=True)


class SwallowEventRow(Base):
    """Detected, ground-truth and manually annotated events, in one table.

    Keyed on (session_id, id), not id alone. Event identifiers are minted
    upstream - by SIM, or by whatever produced a PSG annotation set - and are
    only unique within their own recording. Two sessions of the same scenario
    and seed legitimately carry the same identifiers, and a global key turns
    that into a constraint violation on ingest.
    """

    __tablename__ = "swallow_events"
    id = Column(String, primary_key=True)
    session_id = Column(String, ForeignKey("sessions.id"), primary_key=True, index=True)
    t_start_ms = Column(Integer, nullable=False)
    t_end_ms = Column(Integer, nullable=False)
    confidence = Column(Float, nullable=False)
    source = Column(String, nullable=False, index=True)
    modality_votes = Column(JSON, default=dict)
    sleep_stage = Column(String, default="UNKNOWN")
    arousal_linked = Column(Boolean, default=False)
    arousal_id = Column(String, nullable=True)
    resp_phase_before = Column(String, default="UNKNOWN")
    resp_phase_after = Column(String, default="UNKNOWN")
    coordination_pattern = Column(String, default="UNKNOWN")
    swallow_apnea_ms = Column(Integer, nullable=True)
    posture = Column(String, default="UNKNOWN")
    hob_angle_deg = Column(Float, nullable=True)


Index("ix_swallow_session_time", SwallowEventRow.session_id, SwallowEventRow.t_start_ms)


class SleepEpochRow(Base):
    __tablename__ = "sleep_epochs"
    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String, ForeignKey("sessions.id"), index=True)
    t_start_ms = Column(Integer)
    stage = Column(String)


class ArousalRow(Base):
    # Session-scoped identifiers, same as SwallowEventRow.
    __tablename__ = "arousals"
    id = Column(String, primary_key=True)
    session_id = Column(String, ForeignKey("sessions.id"), primary_key=True, index=True)
    t_start_ms = Column(Integer)
    duration_ms = Column(Integer)


class PostureSegmentRow(Base):
    __tablename__ = "posture_segments"
    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String, ForeignKey("sessions.id"), index=True)
    t_start_ms = Column(Integer)
    t_end_ms = Column(Integer)
    posture = Column(String)
    hob_angle_deg = Column(Float, nullable=True)
    source = Column(String, default="detected")


class SignalSummary(Base):
    """One row per second of recording - the Timescale hypertable."""

    __tablename__ = "signal_summary"
    session_id = Column(String, primary_key=True)
    t_ms = Column(Integer, primary_key=True)
    acoustic_rms = Column(Float)
    acoustic_swallow_band = Column(Float)
    acoustic_snore_band = Column(Float)
    semg_rms = Column(Float)
    imu_si_energy = Column(Float)
    resp_volume = Column(Float)
    posture = Column(String)
    hob_angle_deg = Column(Float)
    artifact = Column(Boolean, default=False)
    snoring = Column(Boolean, default=False)
    coverage = Column(Float, default=1.0)


class NightlyRiskRow(Base):
    __tablename__ = "nightly_risk"
    session_id = Column(String, ForeignKey("sessions.id"), primary_key=True)
    score = Column(Float, nullable=True)
    band = Column(String, nullable=False)
    components = Column(JSON, default=dict)
    data_quality = Column(JSON, default=dict)
    features = Column(JSON, default=dict)
    algorithm_version = Column(String, nullable=False)
    computed_at = Column(DateTime(timezone=True), default=_now)


class AlertRow(Base):
    __tablename__ = "alerts"
    id = Column(String, primary_key=True)
    session_id = Column(String, ForeignKey("sessions.id"), index=True)
    subject_code = Column(String, index=True)
    bed_id = Column(String, index=True, nullable=True)
    rule_id = Column(String, index=True)
    severity = Column(String, index=True)
    status = Column(String, default="open", index=True)
    title = Column(String)
    body = Column(Text, default="")
    recommended_actions = Column(JSON, default=list)
    dedup_key = Column(String, index=True)
    repeat_nights = Column(Integer, default=1)
    created_at = Column(DateTime(timezone=True), default=_now)
    deliver_after = Column(DateTime(timezone=True), nullable=True)
    acknowledged_by = Column(String, nullable=True)
    acknowledged_at = Column(DateTime(timezone=True), nullable=True)
    dismissed_by = Column(String, nullable=True)
    dismissed_at = Column(DateTime(timezone=True), nullable=True)
    dismiss_reason = Column(String, nullable=True)
    dismiss_note = Column(Text, nullable=True)
    context = Column(JSON, default=dict)


class CareActionRow(Base):
    __tablename__ = "care_actions"
    id = Column(String, primary_key=True)
    subject_code = Column(String, index=True)
    session_id = Column(String, nullable=True)
    alert_id = Column(String, nullable=True)
    action = Column(String)
    performed_by = Column(String)
    performed_at = Column(DateTime(timezone=True), default=_now)
    note = Column(Text, nullable=True)


class AuditLogRow(Base):
    """Append-only, hash-chained. Never updated or deleted (PRD 10.2, PAM-S7)."""

    __tablename__ = "audit_log"
    id = Column(Integer, primary_key=True, autoincrement=True)
    at = Column(DateTime(timezone=True), default=_now, index=True)
    actor_id = Column(String, nullable=False)
    bed_id = Column(String, nullable=True, index=True)
    action = Column(String, nullable=False, index=True)
    detail = Column(JSON, default=dict)
    prev_hash = Column(String, nullable=True)
    hash = Column(String, nullable=False)


_engine = None
_SessionLocal = None


def get_engine():
    global _engine, _SessionLocal
    if _engine is None:
        url = get_settings().database_url
        kwargs: dict = {"future": True}
        if url.startswith("sqlite"):
            kwargs["connect_args"] = {"check_same_thread": False}
            from pathlib import Path

            path = url.split("///")[-1]
            if path and path != ":memory:":
                Path(path).parent.mkdir(parents=True, exist_ok=True)
        _engine = create_engine(url, **kwargs)
        _SessionLocal = sessionmaker(bind=_engine, expire_on_commit=False, future=True)
    return _engine


def get_sessionmaker():
    get_engine()
    return _SessionLocal


@contextmanager
def db_session():
    sm = get_sessionmaker()
    s = sm()
    try:
        yield s
        s.commit()
    except Exception:
        s.rollback()
        raise
    finally:
        s.close()


def init_db() -> None:
    engine = get_engine()
    Base.metadata.create_all(engine)
    if engine.dialect.name == "postgresql":
        with engine.begin() as conn:
            conn.execute(text("CREATE EXTENSION IF NOT EXISTS timescaledb"))
            # Idempotent: if_not_exists keeps repeated container starts quiet.
            conn.execute(
                text(
                    "SELECT create_hypertable('signal_summary', 't_ms', "
                    "chunk_time_interval => 3600000, if_not_exists => TRUE, "
                    "migrate_data => TRUE)"
                )
            )


def reset_engine() -> None:
    """Test hook: drop cached engine so a new DATABASE_URL takes effect."""
    global _engine, _SessionLocal
    if _engine is not None:
        _engine.dispose()
    _engine = None
    _SessionLocal = None
    get_settings.cache_clear()
