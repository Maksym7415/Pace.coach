"""Metric key catalog — units, sports, labels for the metrics JSON blob."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class MetricKey:
    key: str
    unit: str
    sports: frozenset[str]
    label: str


METRIC_CATALOG: dict[str, MetricKey] = {
    # Cross-sport / common (also may live as typed columns)
    "avg_pace_s_per_km": MetricKey("avg_pace_s_per_km", "s/km", frozenset({"running"}), "Average pace"),
    "avg_hr_bpm": MetricKey("avg_hr_bpm", "bpm", frozenset({"running", "cycling"}), "Average heart rate"),
    "avg_power_w": MetricKey("avg_power_w", "W", frozenset({"running", "cycling"}), "Average power"),
    "avg_cadence": MetricKey("avg_cadence", "spm", frozenset({"running", "cycling"}), "Average cadence"),
    "first_half_pace_s_per_km": MetricKey(
        "first_half_pace_s_per_km", "s/km", frozenset({"running"}), "First-half pace"
    ),
    "second_half_pace_s_per_km": MetricKey(
        "second_half_pace_s_per_km", "s/km", frozenset({"running"}), "Second-half pace"
    ),
    "pace_variability": MetricKey(
        "pace_variability", "ratio", frozenset({"running"}), "Pace variability"
    ),
    "hr_drift_pct": MetricKey("hr_drift_pct", "%", frozenset({"running", "cycling"}), "HR drift"),
    # Running-specific
    "avg_ground_contact_time_ms": MetricKey(
        "avg_ground_contact_time_ms", "ms", frozenset({"running"}), "Ground contact time"
    ),
    "avg_vertical_oscillation_mm": MetricKey(
        "avg_vertical_oscillation_mm", "mm", frozenset({"running"}), "Vertical oscillation"
    ),
    "vertical_ratio": MetricKey(
        "vertical_ratio", "%", frozenset({"running"}), "Vertical ratio"
    ),
    # Cycling-specific (extension points)
    "torque_effectiveness": MetricKey(
        "torque_effectiveness", "%", frozenset({"cycling"}), "Torque effectiveness"
    ),
    "pedal_smoothness": MetricKey(
        "pedal_smoothness", "%", frozenset({"cycling"}), "Pedal smoothness"
    ),
    "normalized_power_w": MetricKey(
        "normalized_power_w", "W", frozenset({"cycling"}), "Normalized power"
    ),
    # Swimming (extension points)
    "swolf": MetricKey("swolf", "score", frozenset({"swimming"}), "SWOLF"),
    "stroke_count": MetricKey("stroke_count", "count", frozenset({"swimming"}), "Stroke count"),
    # Strength (extension points)
    "reps": MetricKey("reps", "count", frozenset({"strength"}), "Reps"),
    "weight_kg": MetricKey("weight_kg", "kg", frozenset({"strength"}), "Weight"),
}


def get_metric_key(key: str) -> MetricKey | None:
    return METRIC_CATALOG.get(key)


def validate_metric_keys(metrics: dict) -> list[str]:
    """Return unknown keys (allowed but flagged for catalog hygiene)."""
    return [k for k in metrics if k not in METRIC_CATALOG]
