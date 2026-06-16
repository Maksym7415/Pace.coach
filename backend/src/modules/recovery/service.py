"""Recovery business logic."""
from __future__ import annotations

import logging
from datetime import date, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.modules.identity.models import User
from src.modules.recovery.models import RecoveryEntry
from src.modules.recovery.schemas import RecoveryEntryCreateRequest

logger = logging.getLogger("coach_app.recovery")


def _compute_readiness(
    fatigue: int | None,
    soreness: int | None,
    mood: int | None,
    sleep_quality: int | None,
    body_battery: int | None,
) -> int | None:
    scores: list[float] = []
    if fatigue is not None:
        scores.append((10 - fatigue) / 9 * 100)
    if soreness is not None:
        scores.append((10 - soreness) / 9 * 100)
    if mood is not None:
        scores.append((mood - 1) / 9 * 100)
    if sleep_quality is not None:
        scores.append((sleep_quality - 1) / 9 * 100)
    if body_battery is not None:
        scores.append(float(body_battery))
    if not scores:
        return None
    return round(sum(scores) / len(scores))


class RecoveryService:
    def __init__(self, db: Session):
        self.db = db

    def _entry_to_dict(self, entry: RecoveryEntry) -> dict:
        return {
            "id": entry.id,
            "user_id": entry.user_id,
            "entry_date": entry.entry_date.isoformat(),
            "hrv_ms": entry.hrv_ms,
            "resting_hr_bpm": entry.resting_hr_bpm,
            "body_battery": entry.body_battery,
            "fatigue": entry.fatigue,
            "soreness": entry.soreness,
            "mood": entry.mood,
            "sleep_quality": entry.sleep_quality,
            "sleep_hours": entry.sleep_hours,
            "readiness_score": entry.readiness_score,
            "notes": entry.notes,
            "created_at": entry.created_at.isoformat() if entry.created_at else None,
            "updated_at": entry.updated_at.isoformat() if entry.updated_at else None,
        }

    def upsert_entry(
        self, user: User, data: RecoveryEntryCreateRequest
    ) -> tuple[dict | None, str | None, int]:
        readiness = _compute_readiness(
            data.fatigue,
            data.soreness,
            data.mood,
            data.sleep_quality,
            data.body_battery,
        )
        existing = self.db.scalar(
            select(RecoveryEntry).where(
                RecoveryEntry.user_id == user.id,
                RecoveryEntry.entry_date == data.entry_date,
            )
        )
        if existing:
            existing.hrv_ms = data.hrv_ms
            existing.resting_hr_bpm = data.resting_hr_bpm
            existing.body_battery = data.body_battery
            existing.fatigue = data.fatigue
            existing.soreness = data.soreness
            existing.mood = data.mood
            existing.sleep_quality = data.sleep_quality
            existing.sleep_hours = data.sleep_hours
            existing.notes = data.notes
            existing.readiness_score = readiness
            self.db.commit()
            self.db.refresh(existing)
            return {"entry": self._entry_to_dict(existing)}, None, 200

        entry = RecoveryEntry(
            user_id=user.id,
            entry_date=data.entry_date,
            hrv_ms=data.hrv_ms,
            resting_hr_bpm=data.resting_hr_bpm,
            body_battery=data.body_battery,
            fatigue=data.fatigue,
            soreness=data.soreness,
            mood=data.mood,
            sleep_quality=data.sleep_quality,
            sleep_hours=data.sleep_hours,
            notes=data.notes,
            readiness_score=readiness,
        )
        self.db.add(entry)
        self.db.commit()
        self.db.refresh(entry)
        logger.info("Recovery entry created user_id=%s date=%s", user.id, data.entry_date)
        return {"entry": self._entry_to_dict(entry)}, None, 201

    def list_entries(
        self,
        user: User,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> tuple[dict | None, str | None, int]:
        today = datetime.utcnow().date()
        if start_date is None and end_date is None:
            start_date = today - timedelta(days=30)
            end_date = today
        elif start_date is None:
            start_date = end_date - timedelta(days=30) if end_date else today - timedelta(days=30)
        elif end_date is None:
            end_date = today

        if start_date > end_date:
            return None, "start_date must be before or equal to end_date", 400
        if (end_date - start_date).days > 365:
            return None, "Date range cannot exceed 365 days", 400

        entries = self.db.scalars(
            select(RecoveryEntry)
            .where(
                RecoveryEntry.user_id == user.id,
                RecoveryEntry.entry_date >= start_date,
                RecoveryEntry.entry_date <= end_date,
            )
            .order_by(RecoveryEntry.entry_date.desc())
        ).all()
        result = [self._entry_to_dict(e) for e in entries]
        return {"entries": result, "count": len(result)}, None, 200

    def get_today(self, user: User, today: date) -> tuple[dict | None, str | None, int]:
        entry = self.db.scalar(
            select(RecoveryEntry).where(
                RecoveryEntry.user_id == user.id,
                RecoveryEntry.entry_date == today,
            )
        )
        if not entry:
            return None, "No entry for today", 404
        return {"entry": self._entry_to_dict(entry)}, None, 200
