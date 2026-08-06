"""Timeline-based metric extraction for an ExecutionWindow."""
from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime

from src.modules.execution.domain import (
    ActivityEvidence,
    ExecutionMetrics,
    ExecutionWindow,
    ResolvedOccurrence,
)
from src.modules.fit_parser.models import TrackPoint
from src.modules.training.workout_steps import TargetType


def _points_in_window(
    timeline: list[TrackPoint],
    started: datetime,
    ended: datetime,
) -> list[TrackPoint]:
    return [
        p
        for p in timeline
        if p.timestamp is not None and started <= p.timestamp <= ended
    ]


def _mean(values: list[float]) -> float | None:
    if not values:
        return None
    return sum(values) / len(values)


def _target_series(
    points: list[TrackPoint], target_type: TargetType | None
) -> list[float]:
    if target_type is None or target_type == TargetType.none:
        return []
    values: list[float] = []
    for p in points:
        if target_type == TargetType.pace and p.pace is not None:
            values.append(float(p.pace) * 60.0)  # min/km → s/km
        elif target_type == TargetType.heart_rate and p.heart_rate is not None:
            values.append(float(p.heart_rate))
        elif target_type == TargetType.power and p.power is not None:
            values.append(float(p.power))
        elif target_type == TargetType.cadence and p.cadence is not None:
            values.append(float(p.cadence))
    return values


class MetricExtractor(ABC):
    sport_code: str

    @abstractmethod
    def extract(
        self,
        evidence: ActivityEvidence,
        window: ExecutionWindow,
        occurrence: ResolvedOccurrence,
    ) -> ExecutionMetrics:
        raise NotImplementedError


class RunningMetricExtractor(MetricExtractor):
    sport_code = "running"

    def extract(
        self,
        evidence: ActivityEvidence,
        window: ExecutionWindow,
        occurrence: ResolvedOccurrence,
    ) -> ExecutionMetrics:
        points = _points_in_window(evidence.timeline, window.started_at, window.ended_at)
        elapsed_s = (window.ended_at - window.started_at).total_seconds()

        # Moving time: sum inter-point deltas where speed suggests movement
        moving_s = _moving_time_s(points)
        if moving_s is None:
            moving_s = elapsed_s

        distance_m = None
        dists = [p.distance for p in points if p.distance is not None]
        if len(dists) >= 2:
            distance_m = max(dists) - min(dists)
        elif dists:
            distance_m = dists[-1]

        paces_s_per_km = [float(p.pace) * 60.0 for p in points if p.pace is not None and p.pace > 0]
        hrs = [float(p.heart_rate) for p in points if p.heart_rate is not None]
        powers = [float(p.power) for p in points if p.power is not None]
        cadences = [float(p.cadence) for p in points if p.cadence is not None]
        gcts = [
            float(p.ground_contact_time)
            for p in points
            if p.ground_contact_time is not None
        ]
        vos = [
            float(p.vertical_oscillation)
            for p in points
            if p.vertical_oscillation is not None
        ]

        half = max(1, len(paces_s_per_km) // 2)
        first_half = paces_s_per_km[:half]
        second_half = paces_s_per_km[half:] or first_half

        metrics: dict = {}
        avg_pace = _mean(paces_s_per_km)
        if avg_pace is not None:
            metrics["avg_pace_s_per_km"] = avg_pace
        avg_hr = _mean(hrs)
        if avg_hr is not None:
            metrics["avg_hr_bpm"] = avg_hr
        avg_power = _mean(powers)
        if avg_power is not None:
            metrics["avg_power_w"] = avg_power
        avg_cadence = _mean(cadences)
        if avg_cadence is not None:
            metrics["avg_cadence"] = avg_cadence
        fh = _mean(first_half)
        sh = _mean(second_half)
        if fh is not None:
            metrics["first_half_pace_s_per_km"] = fh
        if sh is not None:
            metrics["second_half_pace_s_per_km"] = sh
        if fh and sh and fh > 0:
            metrics["pace_variability"] = abs(sh - fh) / fh
        if len(hrs) >= 4:
            mid = len(hrs) // 2
            first_hr = _mean(hrs[:mid])
            second_hr = _mean(hrs[mid:])
            if first_hr and second_hr and first_hr > 0:
                metrics["hr_drift_pct"] = ((second_hr - first_hr) / first_hr) * 100.0
        gct = _mean(gcts)
        if gct is not None:
            metrics["avg_ground_contact_time_ms"] = gct
        vo = _mean(vos)
        if vo is not None:
            metrics["avg_vertical_oscillation_mm"] = vo

        target_metric = None
        time_in_target_pct = None
        target_deviation_pct = None
        target = occurrence.target
        if target.target_type and target.target_type != TargetType.none:
            target_metric = target.target_type.value
            series = _target_series(points, target.target_type)
            if series and target.target_min is not None and target.target_max is not None:
                in_range = sum(
                    1 for v in series if target.target_min <= v <= target.target_max
                )
                time_in_target_pct = (in_range / len(series)) * 100.0
                mid_target = (target.target_min + target.target_max) / 2.0
                avg_val = _mean(series)
                if avg_val is not None and mid_target != 0:
                    # Signed: positive = above target (for pace: slower; for HR/power: higher)
                    target_deviation_pct = ((avg_val - mid_target) / abs(mid_target)) * 100.0

        return ExecutionMetrics(
            duration_moving_s=moving_s,
            duration_elapsed_s=elapsed_s,
            distance_m=distance_m,
            target_metric=target_metric,
            time_in_target_pct=time_in_target_pct,
            target_deviation_pct=target_deviation_pct,
            metrics=metrics,
        )


def _moving_time_s(points: list[TrackPoint]) -> float | None:
    if len(points) < 2:
        return None
    total = 0.0
    for a, b in zip(points, points[1:]):
        if a.timestamp is None or b.timestamp is None:
            continue
        dt = (b.timestamp - a.timestamp).total_seconds()
        if dt <= 0:
            continue
        # Treat near-zero speed as paused
        speed = b.speed if b.speed is not None else a.speed
        if speed is not None and speed < 0.5:  # km/h
            continue
        total += dt
    return total if total > 0 else None


class CyclingMetricExtractor(MetricExtractor):
    sport_code = "cycling"

    def extract(
        self,
        evidence: ActivityEvidence,
        window: ExecutionWindow,
        occurrence: ResolvedOccurrence,
    ) -> ExecutionMetrics:
        # Reuse running extractor volume/target logic; sport-specific keys differ.
        base = RunningMetricExtractor().extract(evidence, window, occurrence)
        # Drop running-only keys that don't apply
        for key in (
            "avg_ground_contact_time_ms",
            "avg_vertical_oscillation_mm",
            "vertical_ratio",
        ):
            base.metrics.pop(key, None)
        return base


def get_metric_extractor(sport_code: str | None) -> MetricExtractor:
    if sport_code == "cycling":
        return CyclingMetricExtractor()
    return RunningMetricExtractor()
