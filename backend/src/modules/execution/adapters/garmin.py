"""Garmin FIT evidence adapter and device-plan extractor."""
from __future__ import annotations

from datetime import timedelta
from typing import Any

from src.modules.execution.adapters.base import DevicePlanExtractor, EvidenceAdapter
from src.modules.execution.domain import ActivityEvidence, EvidenceSegment
from src.modules.execution.enums import EvidenceCapability
from src.modules.fit_parser.models import DeviceWorkout, NormalizedActivity, TrackPoint


def _segment_end_time(start, duration_s: float | None):
    if start is None or duration_s is None:
        return None
    return start + timedelta(seconds=duration_s)


class GarminEvidenceAdapter(EvidenceAdapter):
    vendor = "garmin"

    def adapt(
        self,
        normalized: NormalizedActivity,
        *,
        activity_id: int | None = None,
    ) -> ActivityEvidence:
        segments: list[EvidenceSegment] = []
        for lap in normalized.laps:
            segments.append(
                EvidenceSegment(
                    segment_id=f"lap-{lap.lap_number}",
                    lap_number=lap.lap_number,
                    message_index=lap.message_index,
                    start_time=lap.start_time,
                    end_time=_segment_end_time(lap.start_time, lap.duration),
                    duration_elapsed_s=lap.duration,
                    duration_moving_s=lap.timer_time,
                    distance_m=lap.distance,
                    device_step_index=lap.wkt_step_index,
                    lap_trigger=lap.lap_trigger,
                    intensity=lap.intensity,
                )
            )

        capabilities: set[EvidenceCapability] = set()
        if any(s.device_step_index is not None for s in segments):
            capabilities.add(EvidenceCapability.device_step_index)
        if normalized.device_workout is not None:
            capabilities.add(EvidenceCapability.device_plan)
        if segments:
            capabilities.add(EvidenceCapability.lap_structure)
        if normalized.track_points:
            capabilities.add(EvidenceCapability.timeline)
            if any(p.heart_rate is not None for p in normalized.track_points):
                capabilities.add(EvidenceCapability.heart_rate)
            if any(p.pace is not None or p.speed is not None for p in normalized.track_points):
                capabilities.add(EvidenceCapability.pace)
            if any(p.power is not None for p in normalized.track_points):
                capabilities.add(EvidenceCapability.power)
            if any(p.cadence is not None for p in normalized.track_points):
                capabilities.add(EvidenceCapability.cadence)

        return ActivityEvidence(
            vendor=self.vendor,
            activity_id=activity_id,
            start_time=normalized.meta.start_time,
            end_time=normalized.meta.end_time,
            sport=normalized.meta.sport,
            segments=segments,
            timeline=list(normalized.track_points),
            markers=list(normalized.events),
            device_plan=normalized.device_workout,
            capabilities=capabilities,
        )


class GarminDevicePlanExtractor(DevicePlanExtractor):
    vendor = "garmin"

    def extract(self, source: Any) -> DeviceWorkout | None:
        if isinstance(source, NormalizedActivity):
            return source.device_workout
        if isinstance(source, DeviceWorkout):
            return source
        if isinstance(source, dict):
            return DeviceWorkout.model_validate(source)
        return None


def activity_evidence_from_persisted(
    *,
    activity_id: int,
    vendor: str,
    sport: str | None,
    start_time,
    end_time,
    laps: list[Any],
    track_points: list[TrackPoint],
    device_workout: DeviceWorkout | None,
    events: list | None = None,
) -> ActivityEvidence:
    """Build ActivityEvidence from already-persisted Activity rows (recompute path)."""
    adapter = GarminEvidenceAdapter() if vendor == "garmin" else GarminEvidenceAdapter()
    # Reconstruct a minimal NormalizedActivity-like shape via the Garmin adapter fields
    from src.modules.fit_parser.models import ActivityMeta, Lap, NormalizedActivity

    fit_laps = []
    for lap in laps:
        fit_laps.append(
            Lap(
                lap_number=getattr(lap, "lap_number"),
                duration=getattr(lap, "duration", None),
                timer_time=getattr(lap, "timer_time", None),
                distance=getattr(lap, "distance", None),
                avg_hr=getattr(lap, "avg_hr", None),
                max_hr=getattr(lap, "max_hr", None),
                avg_power=getattr(lap, "avg_power", None),
                avg_speed=getattr(lap, "avg_speed", None),
                avg_pace=getattr(lap, "avg_pace", None),
                start_time=getattr(lap, "start_time", None),
                message_index=getattr(lap, "message_index", None),
                wkt_step_index=getattr(lap, "wkt_step_index", None),
                lap_trigger=getattr(lap, "lap_trigger", None),
                intensity=getattr(lap, "intensity", None),
            )
        )

    normalized = NormalizedActivity(
        meta=ActivityMeta(
            start_time=start_time,
            end_time=end_time,
            sport=sport,
            source="fit",
        ),
        laps=fit_laps,
        track_points=track_points,
        device_workout=device_workout,
        events=events or [],
    )
    return adapter.adapt(normalized, activity_id=activity_id)
