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
    timer_time: float | None = None
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
    start_time: datetime | None = None
    message_index: int | None = None
    wkt_step_index: int | None = None
    lap_trigger: str | None = None
    intensity: str | None = None


class DeviceWorkoutStep(BaseModel):
    """Prescribed step embedded in an activity FIT file."""

    message_index: int | None = None
    duration_type: str | None = None
    duration_value: float | None = None
    duration_distance: float | None = None
    duration_time: float | None = None
    duration_step: int | None = None
    repeat_steps: int | None = None
    target_type: str | None = None
    target_value: float | None = None
    custom_target_value_low: float | None = None
    custom_target_value_high: float | None = None
    custom_target_speed_low: float | None = None
    custom_target_speed_high: float | None = None
    intensity: str | None = None
    notes: str | None = None
    wkt_step_name: str | None = None


class DeviceWorkout(BaseModel):
    """Workout definition embedded in an activity FIT file."""

    wkt_name: str | None = None
    sport: str | None = None
    sub_sport: str | None = None
    num_valid_steps: int | None = None
    steps: list[DeviceWorkoutStep] = Field(default_factory=list)


class FitEvent(BaseModel):
    """Event message from an activity FIT file."""

    timestamp: datetime | None = None
    event: str | None = None
    event_type: str | None = None
    data: Any | None = None
    event_group: int | None = None


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
    device_workout: DeviceWorkout | None = None
    events: list[FitEvent] = Field(default_factory=list)
