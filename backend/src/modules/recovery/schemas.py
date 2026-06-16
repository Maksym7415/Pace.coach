"""Pydantic request schemas for recovery endpoints."""
from datetime import date

from pydantic import BaseModel, Field


class RecoveryEntryCreateRequest(BaseModel):
    entry_date: date
    hrv_ms: float | None = Field(None, gt=0)
    resting_hr_bpm: int | None = Field(None, ge=20, le=220)
    body_battery: int | None = Field(None, ge=0, le=100)
    fatigue: int | None = Field(None, ge=1, le=10)
    soreness: int | None = Field(None, ge=1, le=10)
    mood: int | None = Field(None, ge=1, le=10)
    sleep_quality: int | None = Field(None, ge=1, le=10)
    sleep_hours: float | None = Field(None, ge=0, le=24)
    notes: str | None = None
