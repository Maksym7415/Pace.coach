"""Structured workout step validation and rollup helpers."""
from __future__ import annotations

import enum
import uuid
from typing import Annotated, Any, Union

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

BUILDER_SPORT_CODES = frozenset({"running", "cycling"})


class StepType(str, enum.Enum):
    warmup = "warmup"
    run = "run"
    interval = "interval"
    recovery = "recovery"
    cooldown = "cooldown"
    rest = "rest"
    ride = "ride"
    recovery_ride = "recovery_ride"


class TargetType(str, enum.Enum):
    none = "none"
    heart_rate = "heart_rate"
    pace = "pace"
    power = "power"
    cadence = "cadence"


class DurationType(str, enum.Enum):
    time = "time"
    distance = "distance"
    lap_button = "lap_button"


STEP_TYPES_BY_SPORT_CODE: dict[str, frozenset[StepType]] = {
    "running": frozenset(
        {
            StepType.warmup,
            StepType.run,
            StepType.interval,
            StepType.recovery,
            StepType.cooldown,
            StepType.rest,
        }
    ),
    "cycling": frozenset(
        {
            StepType.warmup,
            StepType.ride,
            StepType.interval,
            StepType.recovery,
            StepType.recovery_ride,
            StepType.cooldown,
            StepType.rest,
        }
    ),
}


def _infer_duration_type(step: "WorkoutStepModel") -> DurationType:
    if step.duration_type is not None:
        return step.duration_type
    if step.distance is not None and step.duration is None:
        return DurationType.distance
    if step.duration is not None and step.distance is None:
        return DurationType.time
    if step.duration is not None and step.distance is not None:
        if step.type == StepType.interval:
            return DurationType.distance
        return DurationType.time
    return DurationType.lap_button


class WorkoutStepModel(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: str | None = None
    template_step_id: str | None = Field(None, alias="templateStepId")
    type: StepType
    duration_type: DurationType | None = Field(None, alias="durationType")
    duration: int | None = Field(None, ge=1)
    distance: int | None = Field(None, ge=1)
    target_type: TargetType | None = Field(None, alias="targetType")
    target_min: float | None = Field(None, alias="targetMin")
    target_max: float | None = Field(None, alias="targetMax")
    target_zone_id: int | None = Field(None, alias="targetZoneId")
    target_zone_name: str | None = Field(None, alias="targetZoneName")
    notes: str | None = None

    @model_validator(mode="after")
    def validate_duration_mode(self) -> WorkoutStepModel:
        duration_type = _infer_duration_type(self)
        if self.duration is not None and self.distance is not None:
            raise ValueError("Each step must use either duration or distance, not both")
        if duration_type == DurationType.time:
            if self.duration is None:
                raise ValueError("Time-based steps require duration")
            if self.distance is not None:
                raise ValueError("Time-based steps cannot have distance")
        elif duration_type == DurationType.distance:
            if self.distance is None:
                raise ValueError("Distance-based steps require distance")
            if self.duration is not None:
                raise ValueError("Distance-based steps cannot have duration")
        elif duration_type == DurationType.lap_button:
            if self.duration is not None or self.distance is not None:
                raise ValueError("Lap button steps cannot have duration or distance")
        return self


class RepeatBlockModel(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: str | None = None
    repeat_count: int = Field(..., alias="repeatCount", ge=1)
    steps: list[WorkoutStepModel] = Field(..., min_length=1)

    @field_validator("steps")
    @classmethod
    def no_nested_repeats(cls, steps: list[WorkoutStepModel]) -> list[WorkoutStepModel]:
        return steps


WorkoutStepItem = Annotated[
    Union[WorkoutStepModel, RepeatBlockModel],
    Field(discriminator="repeatCount"),
]


def _is_repeat_block(item: dict[str, Any] | BaseModel) -> bool:
    if isinstance(item, BaseModel):
        return isinstance(item, RepeatBlockModel)
    return "repeatCount" in item


def parse_step_item(raw: dict[str, Any]) -> WorkoutStepModel | RepeatBlockModel:
    if "repeatCount" in raw:
        return RepeatBlockModel.model_validate(raw)
    return WorkoutStepModel.model_validate(raw)


def ensure_step_ids(items: list[Any]) -> list[dict[str, Any]]:
    """Mint stable UUIDs for any step (or repeat block) missing an id."""
    result: list[dict[str, Any]] = []
    for raw in items:
        if isinstance(raw, (WorkoutStepModel, RepeatBlockModel)):
            item = raw
        elif isinstance(raw, dict):
            item = parse_step_item(raw)
        else:
            raise ValueError("Invalid step item")

        if isinstance(item, RepeatBlockModel):
            block_id = item.id or str(uuid.uuid4())
            child_steps = []
            for step in item.steps:
                step_id = step.id or str(uuid.uuid4())
                dumped = step.model_dump(by_alias=True, exclude_none=False)
                dumped["id"] = step_id
                child_steps.append(dumped)
            result.append(
                {
                    "id": block_id,
                    "repeatCount": item.repeat_count,
                    "steps": child_steps,
                }
            )
        else:
            step_id = item.id or str(uuid.uuid4())
            dumped = item.model_dump(by_alias=True, exclude_none=False)
            dumped["id"] = step_id
            result.append(dumped)
    return result


def validate_steps(sport_code: str, items: list[Any]) -> list[dict[str, Any]]:
    if sport_code not in BUILDER_SPORT_CODES:
        raise ValueError(
            f"Structured workout builder is not available for sport '{sport_code}'"
        )
    if not items:
        raise ValueError("Workout must have at least one step")

    allowed = STEP_TYPES_BY_SPORT_CODE[sport_code]
    parsed: list[WorkoutStepModel | RepeatBlockModel] = []

    for raw in items:
        if isinstance(raw, (WorkoutStepModel, RepeatBlockModel)):
            item = raw
        elif isinstance(raw, dict):
            item = parse_step_item(raw)
        else:
            raise ValueError("Invalid step item")

        if isinstance(item, RepeatBlockModel):
            for step in item.steps:
                if step.type not in allowed:
                    raise ValueError(
                        f"Step type '{step.type.value}' is not allowed for {sport_code}"
                    )
            parsed.append(item)
        else:
            if item.type not in allowed:
                raise ValueError(
                    f"Step type '{item.type.value}' is not allowed for {sport_code}"
                )
            parsed.append(item)

    dumped = [p.model_dump(by_alias=True, exclude_none=False) for p in parsed]
    return ensure_step_ids(dumped)


def _rollup_leaf(step: WorkoutStepModel) -> tuple[int, int]:
    duration_type = _infer_duration_type(step)
    if duration_type == DurationType.lap_button:
        return 0, 0
    duration = step.duration or 0
    distance = step.distance or 0
    return duration, distance


def compute_rollups(items: list[Any]) -> tuple[int | None, int | None]:
    total_duration = 0
    total_distance = 0
    has_duration = False
    has_distance = False

    for raw in items:
        item = (
            raw
            if isinstance(raw, (WorkoutStepModel, RepeatBlockModel))
            else parse_step_item(raw)
        )
        if isinstance(item, RepeatBlockModel):
            block_duration = 0
            block_distance = 0
            block_has_duration = False
            block_has_distance = False
            for step in item.steps:
                d, dist = _rollup_leaf(step)
                if d:
                    block_has_duration = True
                    block_duration += d
                if dist:
                    block_has_distance = True
                    block_distance += dist
            if block_has_duration:
                has_duration = True
                total_duration += block_duration * item.repeat_count
            if block_has_distance:
                has_distance = True
                total_distance += block_distance * item.repeat_count
        else:
            d, dist = _rollup_leaf(item)
            if d:
                has_duration = True
                total_duration += d
            if dist:
                has_distance = True
                total_distance += dist

    return (
        total_duration if has_duration else None,
        total_distance if has_distance else None,
    )
