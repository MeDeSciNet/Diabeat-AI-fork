"""Append-only, hash-chained audit log (PRD 10.2, PAM-S7).

Each entry hashes its predecessor, so a deletion or edit anywhere in the chain
is detectable by replaying it. Nothing in the codebase updates or deletes rows
in this table.
"""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime

from sqlalchemy import select

from .db import AuditLogRow, db_session


def _iso(at: datetime) -> str:
    """Canonical timestamp form for hashing.

    SQLite does not round-trip tzinfo, so the digest must not depend on it:
    normalise to UTC and drop the offset, in both directions.
    """
    if at.tzinfo is not None:
        at = at.astimezone(UTC)
    return at.replace(tzinfo=None).isoformat(timespec="microseconds")


def _digest(prev_hash: str | None, at: str, actor_id: str, action: str, detail: dict) -> str:
    payload = json.dumps(
        {
            "prev": prev_hash,
            "at": at,
            "actor": actor_id,
            "action": action,
            "detail": detail,
        },
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(payload.encode()).hexdigest()


def record(actor_id: str, action: str, detail: dict, bed_id: str | None = None) -> dict:
    at = datetime.now(UTC)
    with db_session() as db:
        prev = db.scalars(
            select(AuditLogRow).order_by(AuditLogRow.id.desc()).limit(1)
        ).first()
        prev_hash = prev.hash if prev else None
        digest = _digest(prev_hash, _iso(at), actor_id, action, detail)
        row = AuditLogRow(
            at=at,
            actor_id=actor_id,
            bed_id=bed_id,
            action=action,
            detail=detail,
            prev_hash=prev_hash,
            hash=digest,
        )
        db.add(row)
        db.flush()
        return {
            "id": row.id,
            "at": at.isoformat(),
            "actor_id": actor_id,
            "bed_id": bed_id,
            "action": action,
            "detail": detail,
            "prev_hash": prev_hash,
            "hash": digest,
        }


def verify_chain() -> tuple[bool, int | None]:
    """Replay the chain. Returns (intact, first_bad_id)."""
    with db_session() as db:
        rows = db.scalars(select(AuditLogRow).order_by(AuditLogRow.id)).all()
        prev_hash = None
        for row in rows:
            at = _iso(row.at) if row.at else ""
            expected = _digest(prev_hash, at, row.actor_id, row.action, row.detail or {})
            if expected != row.hash or row.prev_hash != prev_hash:
                return False, row.id
            prev_hash = row.hash
    return True, None


def entries(bed_id: str | None = None, limit: int = 200) -> list[dict]:
    with db_session() as db:
        q = select(AuditLogRow).order_by(AuditLogRow.id.desc()).limit(limit)
        if bed_id:
            q = q.where(AuditLogRow.bed_id == bed_id)
        return [
            {
                "id": r.id,
                "at": r.at.isoformat() if r.at else None,
                "actor_id": r.actor_id,
                "bed_id": r.bed_id,
                "action": r.action,
                "detail": r.detail or {},
                "prev_hash": r.prev_hash,
                "hash": r.hash,
            }
            for r in db.scalars(q)
        ]
