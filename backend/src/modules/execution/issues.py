"""Execution issue detection from metrics, scores, and match evidence."""
from __future__ import annotations

from src.modules.execution.domain import (
    ExecutionIssueDraft,
    ExecutionMetrics,
    ExecutionScore,
    MatchEvidence,
    ResolvedOccurrence,
    SegmentMatch,
)
from src.modules.execution.enums import (
    IssueDimension,
    IssueSeverity,
    StepExecutionStatus,
)
from src.modules.training.workout_steps import StepType, TargetType


def detect_issues(
    match: SegmentMatch,
    metrics: ExecutionMetrics | None,
    score: ExecutionScore | None,
) -> list[ExecutionIssueDraft]:
    issues: list[ExecutionIssueDraft] = []
    occurrence = match.occurrence
    evidence = match.evidence

    if match.status == StepExecutionStatus.not_executed:
        issues.append(
            _issue(
                "step_not_executed",
                IssueSeverity.warning,
                IssueDimension.matching,
                occurrence,
                {"evidence": evidence.model_dump()},
            )
        )
    elif match.status == StepExecutionStatus.not_attempted:
        issues.append(
            _issue(
                "step_not_attempted",
                IssueSeverity.info,
                IssueDimension.matching,
                occurrence,
                {"evidence": evidence.model_dump()},
            )
        )
    elif match.status == StepExecutionStatus.unmatched:
        issues.append(
            _issue(
                "step_unmatched",
                IssueSeverity.warning,
                IssueDimension.matching,
                occurrence,
                {"evidence": evidence.model_dump()},
            )
        )
    elif match.status == StepExecutionStatus.substituted:
        issues.append(
            _issue(
                "step_substituted",
                IssueSeverity.warning,
                IssueDimension.structure,
                occurrence,
                {"evidence": evidence.model_dump()},
            )
        )

    if metrics is None or match.window is None:
        return issues

    if score and score.completion is not None and score.completion < 80:
        issues.append(
            _issue(
                "incomplete_duration_or_distance",
                IssueSeverity.warning if score.completion >= 50 else IssueSeverity.critical,
                IssueDimension.completion,
                occurrence,
                {
                    "completion": score.completion,
                    "duration_moving_s": metrics.duration_moving_s,
                    "distance_m": metrics.distance_m,
                },
            )
        )

    if (
        metrics.target_metric
        and metrics.time_in_target_pct is not None
        and metrics.time_in_target_pct < 50
    ):
        severity = IssueSeverity.critical if metrics.time_in_target_pct < 25 else IssueSeverity.warning
        issues.append(
            _issue(
                "below_target_adherence",
                severity,
                IssueDimension.intensity,
                occurrence,
                {
                    "target_metric": metrics.target_metric,
                    "time_in_target_pct": metrics.time_in_target_pct,
                    "target_deviation_pct": metrics.target_deviation_pct,
                    "step_type": occurrence.step_type.value,
                },
            )
        )

    # Intent-specific: recovery too hard
    if (
        occurrence.step_type in {StepType.recovery, StepType.recovery_ride, StepType.rest}
        and metrics.target_deviation_pct is not None
    ):
        is_pace = occurrence.target.target_type == TargetType.pace
        too_hard = (metrics.target_deviation_pct < -5) if is_pace else (
            metrics.target_deviation_pct > 5
        )
        if too_hard:
            issues.append(
                _issue(
                    "recovery_too_hard",
                    IssueSeverity.warning,
                    IssueDimension.intensity,
                    occurrence,
                    {"target_deviation_pct": metrics.target_deviation_pct},
                )
            )

    variability = metrics.metrics.get("pace_variability")
    if isinstance(variability, (int, float)) and variability > 0.08:
        if evidence.strategy_id != "signal":
            issues.append(
                _issue(
                    "inconsistent_pacing",
                    IssueSeverity.info,
                    IssueDimension.quality,
                    occurrence,
                    {"pace_variability": variability},
                )
            )

    return issues


def _issue(
    code: str,
    severity: IssueSeverity,
    dimension: IssueDimension,
    occurrence: ResolvedOccurrence,
    payload: dict,
) -> ExecutionIssueDraft:
    return ExecutionIssueDraft(
        code=code,
        severity=severity.value,
        dimension=dimension.value,
        authored_step_id=occurrence.authored_step_id,
        occurrence_ordinal=occurrence.occurrence_ordinal,
        payload=payload,
    )
