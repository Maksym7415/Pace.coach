"""Pydantic schemas for athlete profile endpoints."""
from datetime import date

from pydantic import BaseModel, Field

from src.modules.athlete_profile.models import ZoneCategoryEnum, ZoneSourceEnum


class SportOut(BaseModel):
    id: int
    code: str
    name: str


class AthleteSportOut(BaseModel):
    id: int
    sport: SportOut
    is_primary: bool
    created_at: str | None


class AddSportRequest(BaseModel):
    sport_id: int
    is_primary: bool = False


class BaselineUpsertRequest(BaseModel):
    hrv_baseline_min: float | None = Field(None, gt=0)
    hrv_baseline_max: float | None = Field(None, gt=0)
    resting_hr_baseline: float | None = Field(None, ge=20, le=220)


class BaselineOut(BaseModel):
    id: int
    athlete_id: int
    hrv_baseline_min: float | None
    hrv_baseline_max: float | None
    resting_hr_baseline: float | None
    created_at: str | None
    updated_at: str | None


class BodyMetricCreateRequest(BaseModel):
    weight_kg: float | None = Field(None, gt=0, le=500)
    height_cm: float | None = Field(None, gt=0, le=300)
    measured_at: date


class BodyMetricOut(BaseModel):
    id: int
    athlete_id: int
    weight_kg: float | None
    height_cm: float | None
    measured_at: str
    created_at: str | None


class SportProfileUpsertRequest(BaseModel):
    threshold_pace_sec_per_km: int | None = Field(None, gt=0)
    threshold_hr: int | None = Field(None, ge=40, le=220)
    ftp_watts: int | None = Field(None, gt=0, le=2000)
    css_pace_sec_per_100m: int | None = Field(None, gt=0)
    zone_source: ZoneSourceEnum | None = None


class SportProfileOut(BaseModel):
    id: int
    athlete_id: int
    sport: SportOut
    threshold_pace_sec_per_km: int | None
    threshold_hr: int | None
    ftp_watts: int | None
    css_pace_sec_per_100m: int | None
    zone_source: str | None
    created_at: str | None
    updated_at: str | None


class ZoneCreateRequest(BaseModel):
    zone_category: ZoneCategoryEnum
    zone_name: str = Field(..., min_length=1, max_length=50)
    min_value: float
    max_value: float


class ZoneOut(BaseModel):
    id: int
    athlete_sport_profile_id: int
    zone_category: str
    zone_name: str
    min_value: float
    max_value: float
    created_at: str | None
