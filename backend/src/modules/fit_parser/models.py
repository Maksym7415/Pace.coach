"""Domain models produced by the FIT parser."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class TrackPoint(BaseModel):
    timestamp: datetime | None = None
    latitude: float | None = None
    longitude: float | None = None
    altitude: float | None = None
    distance: float | None = None
    speed: float | None = None
    pace: float | None = None
    heart_rate: int | None = None
    cadence: int | None = None
    power: int | None = None
    accumulated_power: int | None = None
    motor_power: int | None = None
    temperature: float | None = None
    running_power: int | None = None
    stride_length: float | None = None
    vertical_oscillation: float | None = None
    ground_contact_time: float | None = None
    left_right_balance: float | None = None
    stamina: float | None = None


class Lap(BaseModel):
    lap_number: int
    duration: float | None = None
    distance: float | None = None
    avg_hr: int | None = None
    max_hr: int | None = None
    avg_power: int | None = None
    max_power: int | None = None
    normalized_power: int | None = None
    avg_motor_power: int | None = None
    max_motor_power: int | None = None
    avg_speed: float | None = None
    avg_pace: float | None = None


class ActivityMeta(BaseModel):
    start_time: datetime | None = None
    end_time: datetime | None = None
    duration: float | None = None
    moving_time: float | None = None
    distance: float | None = None
    sport: str | None = None
    activity_type: str | None = None
    calories: int | None = None
    elevation_gain: float | None = None
    elevation_loss: float | None = None
    avg_hr: int | None = None
    max_hr: int | None = None
    avg_cadence: int | None = None
    avg_speed: float | None = None
    avg_pace: float | None = None
    avg_power: int | None = None
    max_power: int | None = None
    normalized_power: int | None = None
    threshold_power: int | None = None
    avg_motor_power: int | None = None
    max_motor_power: int | None = None
    temperature: float | None = None
    device_name: str | None = None
    source: str = Field(default="fit")


class NormalizedActivity(BaseModel):
    meta: ActivityMeta
    laps: list[Lap] = Field(default_factory=list)
    track_points: list[TrackPoint] = Field(default_factory=list)
    developer_fields: dict[str, Any] | None = None
