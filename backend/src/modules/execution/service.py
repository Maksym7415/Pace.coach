"""Orchestrates the execution matching pipeline and read API."""
from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload, selectinload

from src.modules.activity_import.models import ActivityLap, ActivitySource, ActivityTrackPoint
from src.modules.coaching.relations import get_active_coach_athlete_relation
from src.modules.execution.adapters.garmin import GarminEvidenceAdapter
from src.modules.execution.correlation import correlate_structurally
from src.modules.execution.domain import (
    ActivityEvidence,
    InsightClaim,
    ResolvedOccurrence,
    ResolvedPlan,
    SegmentMatch,
)
from src.modules.execution.enums import (
    ALGORITHM_VERSION,
    StepExecutionStatus,
    WorkoutExecutionStatus,
)
from src.modules.execution.insights import build_insights
from src.modules.execution.issues import detect_issues
from src.modules.execution.metrics.extractor import get_metric_extractor
from src.modules.execution.models import (
    ExecutionIssue,
    WorkoutExecution,
    WorkoutPlanSnapshot,
    WorkoutStepExecution,
)
from src.modules.execution.plan_source import JsonWorkoutPlanSource, PlanSource
from src.modules.execution.schemas import (
    AthleteIssueResponseOut,
    ExecutionIssueOut,
    PlannedStepOut,
    SaveAthleteResponsesIn,
    StepExecutionOut,
    WorkoutExecutionOut,
    WorkoutStubOut,
)
from src.modules.execution.scoring import score_occurrence
from src.modules.execution.segmentation.device_step_index import DeviceStepIndexStrategy
from src.modules.execution.segmentation.lap_structure import LapStructureStrategy
from src.modules.execution.segmentation.registry import SegmentationRegistry
from src.modules.execution.segmentation.signal import SignalSegmentationStrategy
from src.modules.fit_parser.models import DeviceWorkout, FitEvent, NormalizedActivity, TrackPoint
from src.modules.gear_track.models import Activity
from src.modules.training.models import Workout


def default_registry() -> SegmentationRegistry:
    return SegmentationRegistry(
        [
            DeviceStepIndexStrategy(),
            LapStructureStrategy(),
            SignalSegmentationStrategy(),
        ]
    )


class ExecutionMatchingService:
    def __init__(
        self,
        db: Session,
        *,
        plan_source: PlanSource | None = None,
        registry: SegmentationRegistry | None = None,
        algorithm_version: str = ALGORITHM_VERSION,
    ):
        self.db = db
        self.plan_source = plan_source or JsonWorkoutPlanSource(db)
        self.registry = registry or default_registry()
        self.algorithm_version = algorithm_version

    def match_from_normalized(
        self,
        *,
        workout_id: int,
        activity_id: int,
        normalized: NormalizedActivity,
        vendor: str = "garmin",
    ) -> WorkoutExecution:
        adapter = GarminEvidenceAdapter()
        evidence = adapter.adapt(normalized, activity_id=activity_id)
        return self._run(workout_id=workout_id, activity_id=activity_id, evidence=evidence)

    def match_persisted(self, *, workout_id: int, activity_id: int) -> WorkoutExecution:
        evidence = self._load_evidence(activity_id)
        return self._run(workout_id=workout_id, activity_id=activity_id, evidence=evidence)

    def _run(
        self,
        *,
        workout_id: int,
        activity_id: int,
        evidence: ActivityEvidence,
    ) -> WorkoutExecution:
        workout = self.db.get(Workout, workout_id)
        if workout is None:
            raise ValueError(f"Workout {workout_id} not found")

        plan = self.plan_source.load(workout_id)
        snapshot = self._create_snapshot(workout, plan)

        # Delete prior execution for same version (idempotent recompute)
        existing = self.db.scalar(
            select(WorkoutExecution).where(
                WorkoutExecution.workout_id == workout_id,
                WorkoutExecution.activity_id == activity_id,
                WorkoutExecution.algorithm_version == self.algorithm_version,
            )
        )
        if existing is not None:
            self.db.delete(existing)
            self.db.flush()

        correlation = correlate_structurally(plan, evidence.device_plan)
        strategy = self.registry.select(evidence)
        if strategy is None:
            execution = WorkoutExecution(
                workout_id=workout_id,
                activity_id=activity_id,
                plan_snapshot_id=snapshot.id,
                status=WorkoutExecutionStatus.unmatched.value,
                overall_confidence=0.0,
                segmentation_strategy=None,
                algorithm_version=self.algorithm_version,
            )
            self.db.add(execution)
            self.db.flush()
            return execution

        matches = strategy.segment(evidence, plan, correlation)
        extractor = get_metric_extractor(plan.sport_code)

        all_issues = []
        step_rows: list[WorkoutStepExecution] = []
        confidences: list[float] = []

        for match in matches:
            metrics = None
            score = None
            metrics_at = None
            scored_at = None

            if match.window is not None:
                metrics = extractor.extract(evidence, match.window, match.occurrence)
                score = score_occurrence(match.occurrence, metrics, match.evidence)
                metrics_at = datetime.utcnow()
                scored_at = datetime.utcnow()
                confidences.append(match.window.confidence)

            issues = detect_issues(match, metrics, score)
            all_issues.extend(issues)

            row = WorkoutStepExecution(
                authored_step_id=match.occurrence.authored_step_id,
                occurrence_path=match.occurrence.occurrence_path,
                occurrence_ordinal=match.occurrence.occurrence_ordinal,
                status=match.status.value,
                started_at=match.window.started_at if match.window else None,
                ended_at=match.window.ended_at if match.window else None,
                match_confidence=match.window.confidence if match.window else None,
                match_evidence=match.evidence.model_dump(mode="json"),
                duration_moving_s=metrics.duration_moving_s if metrics else None,
                duration_elapsed_s=metrics.duration_elapsed_s if metrics else None,
                distance_m=metrics.distance_m if metrics else None,
                target_metric=metrics.target_metric if metrics else None,
                time_in_target_pct=metrics.time_in_target_pct if metrics else None,
                target_deviation_pct=metrics.target_deviation_pct if metrics else None,
                metrics=metrics.metrics if metrics else None,
                metrics_computed_at=metrics_at,
                score=score.score if score else None,
                score_components=score.components if score else None,
                scored_at=scored_at,
            )
            step_rows.append(row)

        status = self._rollup_status(matches)
        overall = sum(confidences) / len(confidences) if confidences else 0.0

        execution = WorkoutExecution(
            workout_id=workout_id,
            activity_id=activity_id,
            plan_snapshot_id=snapshot.id,
            status=status.value,
            overall_confidence=overall,
            segmentation_strategy=strategy.strategy_id,
            algorithm_version=self.algorithm_version,
        )
        self.db.add(execution)
        self.db.flush()

        for row in step_rows:
            row.workout_execution_id = execution.id
            self.db.add(row)

        for issue in all_issues:
            self.db.add(
                ExecutionIssue(
                    workout_execution_id=execution.id,
                    authored_step_id=issue.authored_step_id,
                    occurrence_ordinal=issue.occurrence_ordinal,
                    code=issue.code,
                    severity=issue.severity,
                    dimension=issue.dimension,
                    payload=issue.payload,
                )
            )

        self.db.flush()
        return execution

    def get_insights(self, execution_id: int) -> list[InsightClaim]:
        execution = self.db.get(WorkoutExecution, execution_id)
        if execution is None:
            raise ValueError(f"WorkoutExecution {execution_id} not found")

        # Rebuild lightweight SegmentMatch-like views from persisted rows
        from src.modules.execution.domain import (
            ExecutionIssueDraft,
            MatchEvidence,
            ResolvedOccurrence,
            SegmentMatch,
        )
        from src.modules.training.workout_steps import DurationType, StepType

        snapshot = execution.plan_snapshot
        plan = ResolvedPlan.model_validate(snapshot.resolved_plan)
        occ_by_key = {
            (o.authored_step_id, o.occurrence_ordinal): o for o in plan.occurrences
        }

        matches: list[SegmentMatch] = []
        for step in execution.step_executions:
            key = (step.authored_step_id, step.occurrence_ordinal)
            occurrence = occ_by_key.get(key)
            if occurrence is None:
                occurrence = ResolvedOccurrence(
                    authored_step_id=step.authored_step_id,
                    occurrence_path=step.occurrence_path,
                    occurrence_ordinal=step.occurrence_ordinal,
                    step_type=StepType.run,
                    duration_type=DurationType.time,
                )
            evidence = MatchEvidence.model_validate(step.match_evidence or {"strategy_id": "unknown"})
            window = None
            if step.started_at and step.ended_at:
                from src.modules.execution.domain import ExecutionWindow

                window = ExecutionWindow(
                    started_at=step.started_at,
                    ended_at=step.ended_at,
                    authored_step_id=step.authored_step_id,
                    occurrence_path=step.occurrence_path,
                    occurrence_ordinal=step.occurrence_ordinal,
                    confidence=step.match_confidence or 0.0,
                )
            matches.append(
                SegmentMatch(
                    window=window,
                    evidence=evidence,
                    status=StepExecutionStatus(step.status),
                    occurrence=occurrence,
                )
            )

        issue_drafts = [
            ExecutionIssueDraft(
                code=i.code,
                severity=i.severity,
                dimension=i.dimension,
                authored_step_id=i.authored_step_id,
                occurrence_ordinal=i.occurrence_ordinal,
                payload=i.payload or {},
            )
            for i in execution.issues
        ]
        return build_insights(matches, issue_drafts)

    def _create_snapshot(self, workout: Workout, plan: ResolvedPlan) -> WorkoutPlanSnapshot:
        snapshot = WorkoutPlanSnapshot(
            workout_id=workout.id,
            athlete_id=workout.athlete_id,
            resolved_plan=plan.model_dump(mode="json"),
        )
        self.db.add(snapshot)
        self.db.flush()
        return snapshot

    def _rollup_status(self, matches: list[SegmentMatch]) -> WorkoutExecutionStatus:
        if not matches:
            return WorkoutExecutionStatus.unmatched
        statuses = {m.status for m in matches}
        if statuses == {StepExecutionStatus.executed}:
            return WorkoutExecutionStatus.matched
        if StepExecutionStatus.executed in statuses or StepExecutionStatus.partially_executed in statuses:
            return WorkoutExecutionStatus.partial
        if statuses == {StepExecutionStatus.unmatched}:
            return WorkoutExecutionStatus.unmatched
        return WorkoutExecutionStatus.partial

    def _load_evidence(self, activity_id: int) -> ActivityEvidence:
        activity = self.db.get(Activity, activity_id)
        if activity is None:
            raise ValueError(f"Activity {activity_id} not found")

        laps = list(
            self.db.scalars(
                select(ActivityLap)
                .where(ActivityLap.activity_id == activity_id)
                .order_by(ActivityLap.lap_number)
            )
        )
        points = list(
            self.db.scalars(
                select(ActivityTrackPoint).where(ActivityTrackPoint.activity_id == activity_id)
            )
        )
        source = self.db.scalar(
            select(ActivitySource).where(ActivitySource.activity_id == activity_id)
        )
        raw = (source.raw_metadata if source else None) or {}
        device_workout = None
        if raw.get("device_workout"):
            device_workout = DeviceWorkout.model_validate(raw["device_workout"])
        events = [
            FitEvent.model_validate(e) for e in (raw.get("events") or [])
        ]

        timeline = [
            TrackPoint(
                timestamp=p.timestamp,
                latitude=p.latitude,
                longitude=p.longitude,
                altitude=p.altitude,
                distance=p.distance,
                speed=p.speed,
                pace=p.pace,
                heart_rate=p.heart_rate,
                cadence=p.cadence,
                power=p.power,
                temperature=p.temperature,
                running_power=p.running_power,
                stride_length=p.stride_length,
                vertical_oscillation=p.vertical_oscillation,
                ground_contact_time=p.ground_contact_time,
                left_right_balance=p.left_right_balance,
                stamina=p.stamina,
            )
            for p in points
        ]

        from src.modules.execution.adapters.garmin import activity_evidence_from_persisted
        from src.modules.athlete_profile.models import Sport

        sport_code = None
        if activity.sport_id:
            sport = self.db.get(Sport, activity.sport_id)
            sport_code = sport.code if sport else None

        end_time = None
        if activity.start_time and activity.total_hours:
            from datetime import timedelta

            end_time = activity.start_time + timedelta(hours=activity.total_hours)

        return activity_evidence_from_persisted(
            activity_id=activity_id,
            vendor="garmin",
            sport=sport_code,
            start_time=activity.start_time,
            end_time=end_time,
            laps=laps,
            track_points=timeline,
            device_workout=device_workout,
            events=events,
        )


class WorkoutExecutionService:
    """Read/write access to persisted WorkoutExecution results."""

    def __init__(self, db: Session):
        self.db = db

    def get_for_activity(
        self, user_id: int, activity_id: int
    ) -> tuple[dict[str, Any] | None, str | None, int]:
        activity = self.db.get(Activity, activity_id)
        if activity is None:
            return None, "Activity not found", 404

        if not self._can_access_activity(user_id, activity):
            return None, "Activity not found", 404

        execution = self.db.scalar(
            select(WorkoutExecution)
            .where(WorkoutExecution.activity_id == activity_id)
            .options(
                selectinload(WorkoutExecution.step_executions),
                selectinload(WorkoutExecution.issues),
                joinedload(WorkoutExecution.plan_snapshot),
                joinedload(WorkoutExecution.workout).joinedload(Workout.sport),
            )
            .order_by(WorkoutExecution.created_at.desc(), WorkoutExecution.id.desc())
            .limit(1)
        )

        if execution is None:
            return {"workout_execution": None}, None, 200

        return {
            "workout_execution": serialize_workout_execution(execution).model_dump(mode="json"),
        }, None, 200

    def save_athlete_responses(
        self,
        user_id: int,
        activity_id: int,
        payload: SaveAthleteResponsesIn,
    ) -> tuple[dict[str, Any] | None, str | None, int]:
        activity = self.db.get(Activity, activity_id)
        if activity is None:
            return None, "Activity not found", 404
        if activity.user_id != user_id:
            return None, "Only the athlete can explain execution issues", 403

        execution = self.db.scalar(
            select(WorkoutExecution)
            .where(WorkoutExecution.activity_id == activity_id)
            .options(
                selectinload(WorkoutExecution.step_executions),
                selectinload(WorkoutExecution.issues),
                joinedload(WorkoutExecution.plan_snapshot),
                joinedload(WorkoutExecution.workout).joinedload(Workout.sport),
            )
            .order_by(WorkoutExecution.created_at.desc(), WorkoutExecution.id.desc())
            .limit(1)
        )
        if execution is None:
            return None, "Workout execution not found", 404

        issues_by_id = {issue.id: issue for issue in execution.issues}
        now = datetime.utcnow()
        updated = 0

        for item in payload.responses:
            issue = issues_by_id.get(item.issue_id)
            if issue is None:
                return None, f"Issue {item.issue_id} not found on this execution", 400

            reason = (item.reason or "").strip() or None
            reason_other = (item.reason_other or "").strip() or None
            notes = (item.notes or "").strip() or None
            if reason != "Other":
                reason_other = None

            issue.athlete_id = user_id
            issue.athlete_reason = reason
            issue.athlete_reason_other = reason_other
            issue.athlete_notes = notes
            issue.athlete_responded_at = now
            updated += 1

        self.db.commit()
        self.db.refresh(execution)

        return {
            "updated": updated,
            "workout_execution": serialize_workout_execution(execution).model_dump(mode="json"),
        }, None, 200

    def _can_access_activity(self, user_id: int, activity: Activity) -> bool:
        if activity.user_id == user_id:
            return True
        return get_active_coach_athlete_relation(self.db, user_id, activity.user_id) is not None


def _athlete_response_out(issue: ExecutionIssue) -> AthleteIssueResponseOut | None:
    reason = getattr(issue, "athlete_reason", None)
    reason_other = getattr(issue, "athlete_reason_other", None)
    notes = getattr(issue, "athlete_notes", None)
    responded_at = getattr(issue, "athlete_responded_at", None)
    if reason is None and reason_other is None and notes is None and responded_at is None:
        return None
    return AthleteIssueResponseOut(
        reason=reason,
        reason_other=reason_other,
        notes=notes,
        responded_at=responded_at,
    )


def serialize_workout_execution(execution: WorkoutExecution) -> WorkoutExecutionOut:
    """Join step rows to the plan snapshot and nest issues under each occurrence."""
    snapshot = execution.plan_snapshot
    plan = ResolvedPlan.model_validate(snapshot.resolved_plan) if snapshot else ResolvedPlan()
    occ_by_key: dict[tuple[str, int], ResolvedOccurrence] = {
        (o.authored_step_id, o.occurrence_ordinal): o for o in plan.occurrences
    }

    issues_by_key: dict[tuple[str, int], list[ExecutionIssue]] = {}
    for issue in execution.issues:
        if issue.authored_step_id is None or issue.occurrence_ordinal is None:
            continue
        key = (issue.authored_step_id, issue.occurrence_ordinal)
        issues_by_key.setdefault(key, []).append(issue)

    step_rows = sorted(
        execution.step_executions,
        key=lambda s: (s.occurrence_ordinal, s.authored_step_id),
    )

    step_outs: list[StepExecutionOut] = []
    responded = 0
    for step in step_rows:
        key = (step.authored_step_id, step.occurrence_ordinal)
        occurrence = occ_by_key.get(key)
        issue_outs: list[ExecutionIssueOut] = []
        for issue in issues_by_key.get(key, []):
            athlete_response = _athlete_response_out(issue)
            if athlete_response and athlete_response.responded_at is not None:
                responded += 1
            issue_outs.append(
                ExecutionIssueOut(
                    id=issue.id,
                    code=issue.code,
                    severity=issue.severity,
                    dimension=issue.dimension,
                    athlete_response=athlete_response,
                )
            )
        step_outs.append(
            StepExecutionOut(
                authored_step_id=step.authored_step_id,
                occurrence_path=step.occurrence_path,
                occurrence_ordinal=step.occurrence_ordinal,
                status=step.status,
                planned=_planned_from_occurrence(occurrence),
                duration_moving_s=step.duration_moving_s,
                distance_m=step.distance_m,
                target_metric=step.target_metric,
                time_in_target_pct=step.time_in_target_pct,
                target_deviation_pct=step.target_deviation_pct,
                score=step.score,
                issues=issue_outs,
            )
        )

    workout = execution.workout
    sport_code = workout.sport.code if workout and workout.sport else None

    return WorkoutExecutionOut(
        id=execution.id,
        workout_id=execution.workout_id,
        activity_id=execution.activity_id,
        status=execution.status,
        overall_confidence=execution.overall_confidence,
        algorithm_version=execution.algorithm_version,
        issue_count=sum(len(s.issues) for s in step_outs),
        responded_issue_count=responded,
        workout=WorkoutStubOut(
            id=workout.id if workout else execution.workout_id,
            title=workout.title if workout else "",
            sport_code=sport_code,
            scheduled_date=workout.scheduled_date if workout else datetime.utcnow().date(),
        ),
        step_executions=step_outs,
    )


def _planned_from_occurrence(occurrence: ResolvedOccurrence | None) -> PlannedStepOut:
    if occurrence is None:
        return PlannedStepOut(step_type="run")
    target = occurrence.target
    return PlannedStepOut(
        step_type=occurrence.step_type.value
        if hasattr(occurrence.step_type, "value")
        else str(occurrence.step_type),
        duration_type=(
            occurrence.duration_type.value
            if hasattr(occurrence.duration_type, "value")
            else str(occurrence.duration_type)
            if occurrence.duration_type is not None
            else None
        ),
        duration_min=occurrence.duration_min,
        distance_m=occurrence.distance_m,
        target_type=(
            target.target_type.value
            if target.target_type is not None and hasattr(target.target_type, "value")
            else (str(target.target_type) if target.target_type is not None else None)
        ),
        target_min=target.target_min,
        target_max=target.target_max,
        target_zone_name=target.target_zone_name,
        notes=occurrence.notes,
    )
