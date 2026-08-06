"""Tests for workout execution matching."""
from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path

import pytest

from src.modules.execution.adapters.garmin import GarminEvidenceAdapter
from src.modules.execution.correlation import correlate_structurally
from src.modules.execution.domain import ExecutionWindow, ResolvedOccurrence
from src.modules.execution.enums import EvidenceCapability, StepExecutionStatus
from src.modules.execution.insights import build_insights
from src.modules.execution.issues import detect_issues
from src.modules.execution.metrics.extractor import RunningMetricExtractor
from src.modules.execution.plan_resolution import resolve_plan
from src.modules.execution.scoring import score_occurrence
from src.modules.execution.segmentation.device_step_index import (
    DeviceStepIndexStrategy,
    _group_consecutive_index_runs,
)
from src.modules.execution.segmentation.signal import SignalSegmentationStrategy
from src.modules.execution.domain import (
    ActivityEvidence,
    EvidenceSegment,
    ExecutionIssueDraft,
    MatchEvidence,
    SegmentMatch,
)
from src.modules.fit_parser import FitParser
from src.modules.fit_parser.models import TrackPoint
from src.modules.training.workout_steps import (
    DurationType,
    StepType,
    TargetType,
    ensure_step_ids,
    validate_steps,
)


RESEARCH_FIT = Path("/Users/maksym/Downloads/23712955570_ACTIVITY.fit")


def test_ensure_step_ids_mints_and_preserves():
    items = [
        {"type": "warmup", "durationType": "time", "duration": 10},
        {
            "id": "keep-me",
            "repeatCount": 2,
            "steps": [
                {"type": "interval", "durationType": "distance", "distance": 400},
                {"id": "recovery-1", "type": "recovery", "durationType": "time", "duration": 1},
            ],
        },
    ]
    result = ensure_step_ids(items)
    assert result[0]["id"]
    assert result[1]["id"] == "keep-me"
    assert result[1]["steps"][0]["id"]
    assert result[1]["steps"][1]["id"] == "recovery-1"


def test_validate_steps_assigns_ids():
    result = validate_steps(
        "running",
        [
            {"type": "warmup", "durationType": "time", "duration": 15},
            {
                "repeatCount": 2,
                "steps": [
                    {"type": "interval", "durationType": "distance", "distance": 800},
                    {"type": "recovery", "durationType": "time", "duration": 2},
                ],
            },
        ],
    )
    assert all("id" in s or "repeatCount" in s for s in result)
    assert result[0]["id"]
    assert result[1]["steps"][0]["id"]


def test_resolve_plan_expands_repeats():
    steps = ensure_step_ids(
        [
            {"type": "warmup", "durationType": "time", "duration": 15},
            {
                "repeatCount": 2,
                "steps": [
                    {
                        "type": "interval",
                        "durationType": "distance",
                        "distance": 300,
                        "targetType": "pace",
                        "targetMin": 220,
                        "targetMax": 230,
                    },
                    {"type": "recovery", "durationType": "distance", "distance": 400},
                ],
            },
            {"type": "cooldown", "durationType": "lap_button"},
        ]
    )
    plan = resolve_plan(steps, workout_id=1, sport_code="running")
    # warmup + 2*(interval+recovery) + cooldown = 6
    assert len(plan.occurrences) == 6
    assert plan.occurrences[0].step_type == StepType.warmup
    assert plan.occurrences[1].authored_step_id == plan.occurrences[3].authored_step_id
    assert plan.occurrences[1].occurrence_ordinal == 2
    assert plan.occurrences[3].occurrence_ordinal == 4
    assert any(n.kind == "repeat" for n in plan.tree)


def test_group_consecutive_index_runs_handles_auto_laps_and_repeats():
    segments = [
        EvidenceSegment(segment_id="1", device_step_index=0, lap_number=1),
        EvidenceSegment(segment_id="2", device_step_index=1, lap_number=2),
        EvidenceSegment(segment_id="2b", device_step_index=1, lap_number=3),  # auto lap
        EvidenceSegment(segment_id="3", device_step_index=2, lap_number=4),
        EvidenceSegment(segment_id="4", device_step_index=1, lap_number=5),  # repeat
        EvidenceSegment(segment_id="5", device_step_index=2, lap_number=6),
    ]
    runs = _group_consecutive_index_runs(segments)
    assert [r[0].device_step_index for r in runs] == [0, 1, 2, 1, 2]
    assert len(runs[1]) == 2  # auto-lap merged


@pytest.mark.skipif(not RESEARCH_FIT.exists(), reason="research FIT not available")
def test_device_step_index_strategy_on_research_fit():
    normalized = FitParser.parse(RESEARCH_FIT.read_bytes())
    evidence = GarminEvidenceAdapter().adapt(normalized, activity_id=1)

    assert EvidenceCapability.device_step_index in evidence.capabilities
    assert evidence.device_plan is not None
    assert [s.device_step_index for s in evidence.segments] == [
        0, 1, 2, 1, 2, 4, 5, 4, 5, 7
    ]

    # Mirror the embedded device workout as a Pace.coach plan
    steps = ensure_step_ids(
        [
            {"type": "warmup", "durationType": "distance", "distance": 3000},
            {
                "repeatCount": 2,
                "steps": [
                    {"type": "interval", "durationType": "distance", "distance": 300},
                    {"type": "recovery", "durationType": "distance", "distance": 400},
                ],
            },
            {
                "repeatCount": 2,
                "steps": [
                    {"type": "interval", "durationType": "distance", "distance": 200},
                    {"type": "recovery", "durationType": "distance", "distance": 400},
                ],
            },
            {"type": "cooldown", "durationType": "lap_button"},
        ]
    )
    plan = resolve_plan(steps, sport_code="running")
    assert len(plan.occurrences) == 10

    correlation = correlate_structurally(plan, evidence.device_plan)
    assert correlation.mapping
    assert correlation.confidence > 0.5

    matches = DeviceStepIndexStrategy().segment(evidence, plan, correlation)
    assert len(matches) == 10
    executed = [m for m in matches if m.status == StepExecutionStatus.executed]
    assert len(executed) == 10

    # Repeat-cycle evidence on first interval block
    first_hard = matches[1]
    second_hard = matches[3]
    assert first_hard.evidence.device_step_index == 1
    assert first_hard.evidence.repeat_cycle_run == 1
    assert second_hard.evidence.device_step_index == 1
    assert second_hard.evidence.repeat_cycle_run == 2
    assert second_hard.evidence.prior_runs_of_same_index == 1

    # Every match explains itself
    for match in matches:
        assert match.evidence.strategy_id == "device_step_index"
        assert match.window is not None


def test_running_metric_extractor_time_in_target():
    start = datetime(2026, 1, 1, 10, 0, 0)
    points = []
    for i in range(10):
        # pace in min/km: 4.0 = 240 s/km — within 230-250
        points.append(
            TrackPoint(
                timestamp=start + timedelta(seconds=i),
                distance=float(i * 10),
                pace=4.0,
                heart_rate=150,
                speed=15.0,
            )
        )
    evidence = ActivityEvidence(
        vendor="garmin",
        timeline=points,
        capabilities={EvidenceCapability.timeline, EvidenceCapability.pace},
    )
    occurrence = ResolvedOccurrence(
        authored_step_id="s1",
        occurrence_path="0",
        occurrence_ordinal=1,
        step_type=StepType.interval,
        duration_type=DurationType.time,
        duration_min=1,
        target=__import__(
            "src.modules.execution.domain", fromlist=["ResolvedStepTarget"]
        ).ResolvedStepTarget(
            target_type=TargetType.pace,
            target_min=230,
            target_max=250,
        ),
    )
    window = ExecutionWindow(
        started_at=start,
        ended_at=start + timedelta(seconds=9),
        authored_step_id="s1",
        occurrence_path="0",
        occurrence_ordinal=1,
        confidence=0.9,
    )
    metrics = RunningMetricExtractor().extract(evidence, window, occurrence)
    assert metrics.time_in_target_pct == pytest.approx(100.0)
    assert metrics.target_metric == "pace"
    assert metrics.metrics["avg_pace_s_per_km"] == pytest.approx(240.0)


def test_scoring_null_when_no_target():
    from src.modules.execution.domain import ExecutionMetrics, ResolvedStepTarget

    occurrence = ResolvedOccurrence(
        authored_step_id="s1",
        occurrence_path="0",
        occurrence_ordinal=1,
        step_type=StepType.warmup,
        duration_type=DurationType.time,
        duration_min=10,
        target=ResolvedStepTarget(),
    )
    metrics = ExecutionMetrics(
        duration_moving_s=600,
        duration_elapsed_s=600,
        distance_m=1000,
    )
    score = score_occurrence(occurrence, metrics)
    assert score.completion == pytest.approx(100.0)
    assert score.intensity_adherence is None
    assert score.score is not None  # completion alone


def test_scoring_recovery_too_hard_penalized():
    from src.modules.execution.domain import ExecutionMetrics, ResolvedStepTarget

    occurrence = ResolvedOccurrence(
        authored_step_id="s1",
        occurrence_path="0",
        occurrence_ordinal=1,
        step_type=StepType.recovery,
        duration_type=DurationType.time,
        duration_min=2,
        target=ResolvedStepTarget(
            target_type=TargetType.pace,
            target_min=300,
            target_max=330,
        ),
    )
    # Average pace much faster than target (lower s/km) → negative deviation for pace
    metrics = ExecutionMetrics(
        duration_moving_s=120,
        duration_elapsed_s=120,
        distance_m=400,
        target_metric="pace",
        time_in_target_pct=20.0,
        target_deviation_pct=-20.0,
    )
    score = score_occurrence(occurrence, metrics)
    assert score.intensity_adherence is not None
    assert score.intensity_adherence < 50


def test_insights_suppress_quality_for_signal_strategy():
    occurrence = ResolvedOccurrence(
        authored_step_id="s1",
        occurrence_path="0",
        occurrence_ordinal=1,
        step_type=StepType.interval,
        duration_type=DurationType.distance,
        distance_m=400,
    )
    match = SegmentMatch(
        window=ExecutionWindow(
            started_at=datetime(2026, 1, 1),
            ended_at=datetime(2026, 1, 1, 0, 1),
            authored_step_id="s1",
            occurrence_path="0",
            occurrence_ordinal=1,
            confidence=0.45,
        ),
        evidence=MatchEvidence(
            strategy_id="signal",
            details={"approximate": True},
        ),
        status=StepExecutionStatus.executed,
        occurrence=occurrence,
    )
    issues = [
        ExecutionIssueDraft(
            code="inconsistent_pacing",
            severity="info",
            dimension="quality",
            authored_step_id="s1",
            occurrence_ordinal=1,
            payload={},
        )
    ]
    claims = build_insights([match], issues)
    assert claims[0].suppressed is True
    assert claims[0].suppression_reason == "approximate_boundaries"


def test_signal_strategy_segments_by_planned_distance():
    start = datetime(2026, 1, 1, 8, 0, 0)
    points = [
        TrackPoint(timestamp=start + timedelta(seconds=i), distance=float(i * 10), pace=5.0)
        for i in range(100)
    ]
    evidence = ActivityEvidence(
        vendor="unknown",
        start_time=start,
        timeline=points,
        capabilities={EvidenceCapability.timeline, EvidenceCapability.pace},
    )
    steps = ensure_step_ids(
        [
            {"type": "warmup", "durationType": "distance", "distance": 200},
            {"type": "interval", "durationType": "distance", "distance": 400},
            {"type": "cooldown", "durationType": "distance", "distance": 200},
        ]
    )
    plan = resolve_plan(steps, sport_code="running")
    matches = SignalSegmentationStrategy().segment(evidence, plan)
    assert len(matches) == 3
    assert all(m.window is not None for m in matches)
    assert all(m.evidence.strategy_id == "signal" for m in matches)
    assert matches[0].evidence.details.get("approximate") is True
