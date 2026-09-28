"""Planning business logic for training plans, cycles, items, and reviews."""
from __future__ import annotations

from datetime import date, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from src.modules.coaching.relations import (
    COACH_ATHLETE_NOT_LINKED_STATUS,
    coach_athlete_relation_error,
)
from src.modules.execution.enums import ALGORITHM_VERSION
from src.modules.execution.models import WorkoutExecution
from src.modules.identity.models import User, UserRole, UserRoleEnum
from src.modules.planning.analysis import generate_mesocycle_analysis
from src.modules.planning.changelog import diff_fields, record_change
from src.modules.planning.clock import is_valid_timezone, planning_today
from src.modules.planning.context import cycle_bands
from src.modules.planning.dates import DateMove, MesoSpec, MicroSpec, duration_days, reflow
from src.modules.planning.enums import (
    ChangeLogEntityType,
    CoachReviewStatus,
    LockState,
    PlacementType,
    PlanOperation,
    TrainingPlanStatus,
)
from src.modules.planning.immutability import (
    assert_locked_structure_unchanged,
    assert_mutable,
    bulk_evidence_microcycle_ids,
    mesocycle_lock_state,
    microcycle_lock_state,
    snapshot_locked_periods,
)
from src.modules.planning.models import (
    CycleCoachReview,
    CycleSystemAnalysis,
    Mesocycle,
    Microcycle,
    PlanChangeLog,
    PlanItem,
    TrainingPlan,
)
from src.modules.planning.schemas import (
    CoachReviewCreateRequest,
    CoachReviewUpdateRequest,
    MesocycleCreateRequest,
    MesocycleUpdateRequest,
    MicrocycleCreateRequest,
    MicrocycleUpdateRequest,
    PlanItemCreateRequest,
    PlanItemUpdateRequest,
    TrainingPlanCreateRequest,
    TrainingPlanUpdateRequest,
)
from src.modules.training.models import Workout, WorkoutStatus
from src.modules.training.schemas import WorkoutCreateRequest

MAX_MESOCYCLES = 52
MAX_MICROCYCLES = 52
REORDER_OFFSET = 10_000
UNKNOWN_TZ = "Unknown timezone; expected an IANA name such as 'Europe/Warsaw'"
OVERLAP_ERROR = "Athlete already has an active plan covering these dates"
LOCKED_LATER_ERROR = "A completed session in a later period blocks this change"
REORDER_IDS_ERROR = "ordered_ids must contain exactly the current children"


def _iso(value: date | datetime | None) -> str | None:
    return value.isoformat() if value is not None else None


def _enum_val(value) -> str | None:
    if value is None:
        return None
    return value.value if hasattr(value, "value") else str(value)


def _resolve_placement(item: PlanItem, micro: Microcycle | None) -> dict | None:
    """Derive calendar placement for a PlanItem. Never persists resolved_date."""
    placement_type = item.placement_type
    if placement_type is None:
        return None
    type_val = _enum_val(placement_type)
    if type_val == PlacementType.relative_day.value:
        day = item.placement_day
        resolved: date | None = None
        if day is not None and micro is not None and micro.start_date is not None:
            resolved = micro.start_date + timedelta(days=day - 1)
        return {
            "type": PlacementType.relative_day.value,
            "day": day,
            "resolved_date": _iso(resolved),
            "conflict": False,
        }
    if type_val == PlacementType.specific_date.value:
        pinned = item.placement_date
        conflict = False
        if (
            pinned is not None
            and micro is not None
            and micro.start_date is not None
            and micro.end_date is not None
            and not (micro.start_date <= pinned <= micro.end_date)
        ):
            conflict = True
        return {
            "type": PlacementType.specific_date.value,
            "date": _iso(pinned),
            "resolved_date": _iso(pinned),
            "conflict": conflict,
        }
    return None


def _placement_fields_set(payload) -> bool:
    return bool(
        {"placement_type", "placement_day", "placement_date"} & payload.model_fields_set
    )


def _validate_and_normalize_placement(
    micro: Microcycle,
    placement_type: PlacementType | None,
    placement_day: int | None,
    placement_date: date | None,
    *,
    clearing: bool = False,
) -> tuple[PlacementType | None, int | None, date | None, str | None]:
    """Validate placement inputs. Returns (type, day, date, error)."""
    if clearing or placement_type is None:
        if placement_day is not None or placement_date is not None:
            return None, None, None, "placement_day and placement_date require placement_type"
        return None, None, None, None

    if placement_type == PlacementType.relative_day:
        if placement_day is None:
            return None, None, None, "placement_day is required for relative_day"
        if placement_date is not None:
            return None, None, None, "placement_date must be null for relative_day"
        if not (1 <= placement_day <= micro.duration_days):
            return (
                None,
                None,
                None,
                f"placement_day must be between 1 and {micro.duration_days}",
            )
        return PlacementType.relative_day, placement_day, None, None

    if placement_type == PlacementType.specific_date:
        if placement_date is None:
            return None, None, None, "placement_date is required for specific_date"
        if placement_day is not None:
            return None, None, None, "placement_day must be null for specific_date"
        if micro.start_date is None or micro.end_date is None:
            return None, None, None, "Set a plan start date before assigning specific_date"
        if not (micro.start_date <= placement_date <= micro.end_date):
            return None, None, None, "placement_date must fall inside the microcycle"
        return PlacementType.specific_date, None, placement_date, None

    return None, None, None, "Invalid placement_type"


class PlanningService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def _authorize_coach_for_plan(
        self, coach: User, plan: TrainingPlan
    ) -> tuple[str | None, int]:
        err = coach_athlete_relation_error(self.db, coach.id, plan.athlete_id)
        if err:
            return err, COACH_ATHLETE_NOT_LINKED_STATUS
        return None, 200

    def _assert_athlete_user(self, athlete_id: int) -> str | None:
        has_role = self.db.scalar(
            select(UserRole).where(
                UserRole.user_id == athlete_id,
                UserRole.role == UserRoleEnum.athlete,
            )
        )
        return None if has_role else "Athlete not found"

    def _today(self, plan: TrainingPlan, today: date | None) -> date:
        return today if today is not None else planning_today(plan)

    def _load_plan(self, plan_id: int, depth: str = "items") -> TrainingPlan | None:
        stmt = select(TrainingPlan).where(TrainingPlan.id == plan_id)
        if depth == "mesocycles":
            stmt = stmt.options(selectinload(TrainingPlan.mesocycles))
        elif depth == "microcycles":
            stmt = stmt.options(
                selectinload(TrainingPlan.mesocycles).selectinload(Mesocycle.microcycles)
            )
        elif depth == "items":
            stmt = stmt.options(
                selectinload(TrainingPlan.mesocycles)
                .selectinload(Mesocycle.microcycles)
                .selectinload(Microcycle.items)
            )
        return self.db.scalar(stmt)

    def _load_mesocycle(self, mesocycle_id: int) -> Mesocycle | None:
        return self.db.scalar(
            select(Mesocycle)
            .options(
                selectinload(Mesocycle.microcycles).selectinload(Microcycle.items),
                selectinload(Mesocycle.training_plan),
            )
            .where(Mesocycle.id == mesocycle_id)
        )

    def _load_microcycle(self, microcycle_id: int) -> Microcycle | None:
        return self.db.scalar(
            select(Microcycle)
            .options(
                selectinload(Microcycle.items),
                selectinload(Microcycle.mesocycle).selectinload(Mesocycle.training_plan),
            )
            .where(Microcycle.id == microcycle_id)
        )

    def _load_item(self, item_id: int) -> PlanItem | None:
        return self.db.scalar(
            select(PlanItem)
            .options(
                selectinload(PlanItem.microcycle)
                .selectinload(Microcycle.mesocycle)
                .selectinload(Mesocycle.training_plan)
            )
            .where(PlanItem.id == item_id)
        )

    def _plan_of_meso(self, meso: Mesocycle) -> TrainingPlan:
        return meso.training_plan or self.db.get(TrainingPlan, meso.training_plan_id)

    def _plan_of_micro(self, micro: Microcycle) -> TrainingPlan:
        meso = micro.mesocycle or self.db.get(Mesocycle, micro.mesocycle_id)
        return self._plan_of_meso(meso)

    def _plan_of_item(self, item: PlanItem) -> TrainingPlan:
        micro = item.microcycle or self.db.get(Microcycle, item.microcycle_id)
        return self._plan_of_micro(micro)

    def _lock_maps(
        self, plan: TrainingPlan, today: date
    ) -> tuple[dict[int, LockState], dict[int, LockState], set[int]]:
        mesos = list(plan.mesocycles or [])
        micros = [m for meso in mesos for m in (meso.microcycles or [])]
        evidence = bulk_evidence_microcycle_ids(self.db, [m.id for m in micros])
        micro_states = {
            m.id: microcycle_lock_state(self.db, m, today, evidence) for m in micros
        }
        meso_states = {
            meso.id: mesocycle_lock_state(self.db, meso, today, evidence, micro_states)
            for meso in mesos
        }
        return micro_states, meso_states, evidence

    def _plan_lock_state(self, plan: TrainingPlan, today: date) -> LockState:
        if plan.start_date is None or plan.end_date is None:
            return LockState.future
        if plan.end_date < today:
            return LockState.locked
        if plan.start_date <= today <= plan.end_date:
            return LockState.current
        return LockState.future

    def _any_locked_period(self, plan: TrainingPlan, today: date) -> bool:
        micro_states, meso_states, _ = self._lock_maps(plan, today)
        return LockState.locked in micro_states.values() or LockState.locked in meso_states.values()

    def _assert_no_active_overlap(
        self,
        athlete_id: int,
        start: date | None,
        end: date | None,
        exclude_plan_id: int | None = None,
    ) -> str | None:
        if start is None:
            return None
        effective_end = end if end is not None else start
        from sqlalchemy import func

        plan_end = func.coalesce(TrainingPlan.end_date, TrainingPlan.start_date)
        stmt = select(TrainingPlan).where(
            TrainingPlan.athlete_id == athlete_id,
            TrainingPlan.status == TrainingPlanStatus.active,
            TrainingPlan.start_date.is_not(None),
            TrainingPlan.start_date <= effective_end,
            plan_end >= start,
        )
        if exclude_plan_id is not None:
            stmt = stmt.where(TrainingPlan.id != exclude_plan_id)
        if self.db.scalar(stmt):
            return OVERLAP_ERROR
        return None

    def _item_to_dict(self, item: PlanItem, micro: Microcycle | None = None) -> dict:
        micro = micro if micro is not None else item.microcycle
        return {
            "id": item.id,
            "microcycle_id": item.microcycle_id,
            "ordinal": item.ordinal,
            "placement": _resolve_placement(item, micro),
            "workout_id": item.workout_id,
            "is_placeholder": item.workout_id is None,
            "title": item.title,
            "intent": item.intent,
            "planned_workout_type": item.planned_workout_type,
            "planned_sport_id": item.planned_sport_id,
            "planned_duration_min": item.planned_duration_min,
            "planned_distance_m": item.planned_distance_m,
            "converted_at": _iso(item.converted_at),
            "converted_by_id": item.converted_by_id,
            "created_at": _iso(item.created_at),
            "updated_at": _iso(item.updated_at),
        }

    def _micro_to_dict(
        self, micro: Microcycle, lock_state: LockState | None, include_items: bool
    ) -> dict:
        payload = {
            "id": micro.id,
            "mesocycle_id": micro.mesocycle_id,
            "name": micro.name,
            "intent": micro.intent,
            "start_date": _iso(micro.start_date),
            "end_date": _iso(micro.end_date),
            "duration_days": micro.duration_days,
            "ordinal": micro.ordinal,
            "lock_state": lock_state.value if lock_state else None,
            "created_at": _iso(micro.created_at),
            "updated_at": _iso(micro.updated_at),
        }
        if include_items:
            payload["items"] = [self._item_to_dict(i, micro) for i in (micro.items or [])]
        return payload

    def _meso_to_dict(
        self,
        meso: Mesocycle,
        meso_state: LockState | None,
        micro_states: dict[int, LockState],
        depth: str,
        conflict: dict | None = None,
    ) -> dict:
        micros = list(meso.microcycles or [])
        meso_duration = sum(m.duration_days for m in micros) if micros else (
            duration_days(meso.start_date, meso.end_date) or 0
        )
        payload = {
            "id": meso.id,
            "training_plan_id": meso.training_plan_id,
            "name": meso.name,
            "focus": _enum_val(meso.focus),
            "intent": meso.intent,
            "start_date": _iso(meso.start_date),
            "end_date": _iso(meso.end_date),
            "anchor_date": _iso(meso.anchor_date),
            "duration_days": meso_duration,
            "ordinal": meso.ordinal,
            "lock_state": meso_state.value if meso_state else None,
            "conflict": conflict,
            "created_at": _iso(meso.created_at),
            "updated_at": _iso(meso.updated_at),
        }
        if depth in ("microcycles", "items"):
            payload["microcycles"] = [
                self._micro_to_dict(m, micro_states.get(m.id), include_items=(depth == "items"))
                for m in micros
            ]
        return payload

    def _plan_to_dict(
        self,
        plan: TrainingPlan,
        depth: str,
        today: date | None = None,
        gaps: list[dict] | None = None,
        conflicts: list[dict] | None = None,
    ) -> dict:
        today = self._today(plan, today)
        micro_states: dict[int, LockState] = {}
        meso_states: dict[int, LockState] = {}
        if depth != "plan":
            micro_states, meso_states, _ = self._lock_maps(plan, today)
        conflict_by_meso = {
            c["meso_id"]: c for c in (conflicts or []) if "meso_id" in c
        }
        payload = {
            "id": plan.id,
            "athlete_id": plan.athlete_id,
            "coach_id": plan.coach_id,
            "name": plan.name,
            "goal": plan.goal,
            "goal_event_date": _iso(plan.goal_event_date),
            "start_date": _iso(plan.start_date),
            "end_date": _iso(plan.end_date),
            "status": plan.status.value,
            "planning_timezone": plan.planning_timezone,
            "notes": plan.notes,
            "gaps": gaps or [],
            "conflicts": conflicts or [],
            "created_at": _iso(plan.created_at),
            "updated_at": _iso(plan.updated_at),
        }
        if depth in ("mesocycles", "microcycles", "items"):
            payload["mesocycles"] = [
                self._meso_to_dict(
                    m,
                    meso_states.get(m.id),
                    micro_states,
                    depth,
                    conflict=conflict_by_meso.get(m.id),
                )
                for m in (plan.mesocycles or [])
            ]
        return payload

    def _plan_to_dict_for_athlete(self, plan: TrainingPlan, today: date | None = None) -> dict:
        tree = self._plan_to_dict(plan, "items", today)
        tree.pop("coach_id", None)
        tree.pop("notes", None)
        approved = self._approved_reviews_for_plan(plan.id)
        for meso in tree.get("mesocycles") or []:
            meso.pop("lock_state", None)
            meso.pop("created_at", None)
            meso.pop("updated_at", None)
            meso["coach_review"] = approved.get(meso["id"])
            for micro in meso.get("microcycles") or []:
                micro.pop("lock_state", None)
                micro.pop("created_at", None)
                micro.pop("updated_at", None)
                for item in micro.get("items") or []:
                    item.pop("converted_at", None)
                    item.pop("converted_by_id", None)
                    item.pop("created_at", None)
                    item.pop("updated_at", None)
        return tree

    def _approved_reviews_for_plan(self, plan_id: int) -> dict[int, dict]:
        rows = self.db.scalars(
            select(CycleCoachReview)
            .join(Mesocycle, Mesocycle.id == CycleCoachReview.mesocycle_id)
            .where(
                Mesocycle.training_plan_id == plan_id,
                CycleCoachReview.status == CoachReviewStatus.approved,
                CycleCoachReview.superseded_by_id.is_(None),
            )
        ).all()
        return {r.mesocycle_id: self._review_to_dict(r, public=True) for r in rows}

    def _review_to_dict(self, review: CycleCoachReview, public: bool = False) -> dict:
        payload = {
            "id": review.id,
            "mesocycle_id": review.mesocycle_id,
            "status": review.status.value,
            "content": review.content,
            "next_cycle_focus": review.next_cycle_focus,
            "version": review.version,
            "approved_at": _iso(review.approved_at),
        }
        if not public:
            payload.update(
                {
                    "coach_id": review.coach_id,
                    "source_analysis_id": review.source_analysis_id,
                    "superseded_by_id": review.superseded_by_id,
                    "approved_by_id": review.approved_by_id,
                    "created_at": _iso(review.created_at),
                    "updated_at": _iso(review.updated_at),
                }
            )
        return payload

    def _analysis_to_dict(self, row: CycleSystemAnalysis) -> dict:
        return {
            "id": row.id,
            "mesocycle_id": row.mesocycle_id,
            "generated_at": _iso(row.generated_at),
            "generator": row.generator,
            "generator_version": row.generator_version,
            "data_cutoff_date": _iso(row.data_cutoff_date),
            "summary": row.summary,
            "metrics": row.metrics,
            "source_refs": row.source_refs,
        }

    def _locked_after_unlocked(
        self, micros: list[Microcycle], states: dict[int, LockState]
    ) -> Microcycle | None:
        seen_unlocked = False
        for micro in sorted(micros, key=lambda m: m.ordinal):
            if states.get(micro.id) == LockState.locked:
                if seen_unlocked:
                    return micro
            else:
                seen_unlocked = True
        return None

    def _workout_has_evidence(self, workout: Workout) -> bool:
        if workout.status != WorkoutStatus.scheduled or workout.activity_id is not None:
            return True
        row = self.db.scalar(
            select(WorkoutExecution.id).where(
                WorkoutExecution.workout_id == workout.id,
                WorkoutExecution.algorithm_version == ALGORITHM_VERSION,
            )
        )
        return row is not None

    def _log_reflow_if_moved(
        self,
        plan: TrainingPlan,
        moved: list[dict],
        today: date,
        coach: User,
        reason: str | None,
    ) -> None:
        if not moved:
            return
        self._log(
            plan,
            ChangeLogEntityType.training_plan,
            plan.id,
            "reflow",
            self._plan_lock_state(plan, today),
            coach,
            PlanOperation.dates,
            after={"moved": moved},
            reason=reason,
        )

    def _meso_fully_locked(
        self, micros: list[Microcycle], micro_states: dict[int, LockState]
    ) -> bool:
        if not micros:
            return True
        return all(micro_states.get(m.id) == LockState.locked for m in micros)

    def _log(
        self,
        plan: TrainingPlan,
        entity_type: ChangeLogEntityType,
        entity_id: int,
        operation: str,
        lock_state: LockState,
        actor: User | None,
        plan_operation: PlanOperation | None = None,
        before: dict | None = None,
        after: dict | None = None,
        reason: str | None = None,
    ) -> None:
        record_change(
            self.db,
            plan_id=plan.id,
            entity_type=entity_type,
            entity_id=entity_id,
            operation=operation,
            lock_state=lock_state,
            actor=actor,
            plan_operation=plan_operation,
            before=before,
            after=after,
            reason=reason,
        )

    def _two_phase_reorder(self, objs: list, ordered_ids: list[int]) -> str | None:
        by_id = {obj.id: obj for obj in objs}
        if set(ordered_ids) != set(by_id):
            return REORDER_IDS_ERROR
        for i, obj in enumerate(objs):
            obj.ordinal = REORDER_OFFSET + i
        self.db.flush()
        for i, oid in enumerate(ordered_ids):
            by_id[oid].ordinal = i
        self.db.flush()
        return None

    def _locked_prefix_ids(self, objs: list, states: dict[int, LockState]) -> list[int]:
        return [
            obj.id
            for obj in sorted(objs, key=lambda o: o.ordinal)
            if states.get(obj.id) == LockState.locked
        ]

    def _shift_micro_contents(
        self,
        micro: Microcycle,
        old_start: date | None,
        new_start: date | None,
        new_end: date | None,
        conflicts: list[dict],
    ) -> None:
        if old_start is None or new_start is None or new_end is None:
            return
        delta = new_start - old_start
        touched_dates: set[date] = set()
        for item in list(micro.items or []):
            type_val = _enum_val(item.placement_type)
            if type_val == PlacementType.specific_date.value and item.placement_date is not None:
                if not (new_start <= item.placement_date <= new_end):
                    conflicts.append(
                        {
                            "kind": "placement_conflict",
                            "plan_item_id": item.id,
                            "placement_date": _iso(item.placement_date),
                        }
                    )
            # relative_day and unplaced: nothing persisted to shift
            if not item.workout_id:
                continue
            workout = self.db.get(Workout, item.workout_id)
            if workout is None:
                continue
            candidate = (
                workout.scheduled_date + delta if delta.days else workout.scheduled_date
            )
            if self._workout_has_evidence(workout):
                if candidate != workout.scheduled_date or not (
                    new_start <= workout.scheduled_date <= new_end
                ):
                    conflicts.append(
                        {
                            "kind": "workout_not_rescheduled",
                            "workout_id": workout.id,
                            "scheduled_date": _iso(workout.scheduled_date),
                        }
                    )
                continue
            if not (new_start <= candidate <= new_end):
                conflicts.append(
                    {
                        "kind": "workout_not_rescheduled",
                        "workout_id": workout.id,
                        "scheduled_date": _iso(workout.scheduled_date),
                    }
                )
                continue
            if candidate != workout.scheduled_date:
                old_date = workout.scheduled_date
                workout.scheduled_date = candidate
                touched_dates.add(old_date)
                touched_dates.add(candidate)
        if not touched_dates:
            return
        workout_ids = [i.workout_id for i in (micro.items or []) if i.workout_id]
        workouts = list(
            self.db.scalars(
                select(Workout)
                .where(Workout.id.in_(workout_ids), Workout.scheduled_date.in_(touched_dates))
                .order_by(Workout.scheduled_date.asc(), Workout.slot_ordinal.asc(), Workout.id.asc())
            ).all()
        )
        by_date: dict[date, list[Workout]] = {}
        for w in workouts:
            by_date.setdefault(w.scheduled_date, []).append(w)
        for group in by_date.values():
            for i, w in enumerate(group):
                w.slot_ordinal = i

    def _apply_reflow(
        self, plan: TrainingPlan, today: date, strict: bool = False
    ) -> tuple[list[dict], list[dict], list[dict], list[dict], str | None, int]:
        """Returns (moved, workout_conflicts, gaps, anchor_conflicts, err, status)."""
        self.db.flush()
        mesos = list(
            self.db.scalars(
                select(Mesocycle)
                .options(selectinload(Mesocycle.microcycles).selectinload(Microcycle.items))
                .where(Mesocycle.training_plan_id == plan.id)
                .order_by(Mesocycle.ordinal.asc())
            ).all()
        )
        micros = [m for meso in mesos for m in meso.microcycles]
        evidence = bulk_evidence_microcycle_ids(self.db, [m.id for m in micros])
        micro_states = {
            m.id: microcycle_lock_state(self.db, m, today, evidence) for m in micros
        }
        meso_states = {
            meso.id: mesocycle_lock_state(self.db, meso, today, evidence, micro_states)
            for meso in mesos
        }
        for meso in mesos:
            blocker = self._locked_after_unlocked(list(meso.microcycles), micro_states)
            if blocker:
                return [], [], [], [], f"{LOCKED_LATER_ERROR} (microcycle {blocker.id})", 409
        before = snapshot_locked_periods(mesos, micro_states, meso_states)
        old_starts = {m.id: m.start_date for m in micros}
        specs = [
            MesoSpec(
                id=meso.id,
                ordinal=meso.ordinal,
                start_date=meso.start_date,
                end_date=meso.end_date,
                locked=meso_states[meso.id] == LockState.locked,
                anchor_date=meso.anchor_date,
                name=meso.name or "",
                empty_duration_days=(
                    duration_days(meso.start_date, meso.end_date) or 0
                    if not list(meso.microcycles or [])
                    else 0
                ),
                micros=[
                    MicroSpec(
                        id=m.id,
                        ordinal=m.ordinal,
                        duration_days=m.duration_days,
                        start_date=m.start_date,
                        end_date=m.end_date,
                        locked=micro_states[m.id] == LockState.locked,
                    )
                    for m in meso.microcycles
                ],
            )
            for meso in mesos
        ]
        specs, moves, plan_end, gaps, anchor_conflicts = reflow(
            plan.start_date, specs, today=today
        )
        meso_by_id = {m.id: m for m in mesos}
        micro_by_id = {m.id: m for m in micros}
        workout_conflicts: list[dict] = []
        for spec in specs:
            meso = meso_by_id[spec.id]
            meso.start_date = spec.start_date
            meso.end_date = spec.end_date
            for ms in spec.micros:
                micro = micro_by_id[ms.id]
                old_start = old_starts[micro.id]
                micro.start_date = ms.start_date
                micro.end_date = ms.end_date
                if micro_states[micro.id] != LockState.locked:
                    self._shift_micro_contents(
                        micro, old_start, ms.start_date, ms.end_date, workout_conflicts
                    )
        old_plan_end = plan.end_date
        plan.end_date = plan_end
        if old_plan_end != plan_end:
            moves.append(
                DateMove(
                    kind="plan",
                    id=plan.id,
                    old_start=plan.start_date,
                    new_start=plan.start_date,
                    old_end=old_plan_end,
                    new_end=plan_end,
                )
            )
        after_micro = {
            m.id: microcycle_lock_state(self.db, m, today, evidence) for m in micros
        }
        after_meso = {
            meso.id: mesocycle_lock_state(self.db, meso, today, evidence, after_micro)
            for meso in mesos
        }
        structure_err = assert_locked_structure_unchanged(
            before, snapshot_locked_periods(mesos, after_micro, after_meso)
        )
        if structure_err:
            self.db.rollback()
            return [], [], [], [], structure_err, 409
        if plan.status == TrainingPlanStatus.active:
            overlap = self._assert_no_active_overlap(
                plan.athlete_id, plan.start_date, plan.end_date, exclude_plan_id=plan.id
            )
            if overlap:
                self.db.rollback()
                return [], [], [], [], overlap, 409
        if strict and workout_conflicts:
            self.db.rollback()
            return [], [], [], [], "Restructuring conflicts with existing scheduled workouts", 409
        return (
            [m.to_dict() for m in moves],
            workout_conflicts,
            [g.to_dict() for g in gaps],
            [c.to_dict() for c in anchor_conflicts],
            None,
            200,
        )

    def create_plan(
        self, coach: User, payload: TrainingPlanCreateRequest
    ) -> tuple[dict | None, str | None, int]:
        athlete_err = self._assert_athlete_user(payload.athlete_id)
        if athlete_err:
            return None, athlete_err, 404
        relation_err = coach_athlete_relation_error(self.db, coach.id, payload.athlete_id)
        if relation_err:
            return None, relation_err, COACH_ATHLETE_NOT_LINKED_STATUS
        if not is_valid_timezone(payload.planning_timezone):
            return None, UNKNOWN_TZ, 400
        plan = TrainingPlan(
            athlete_id=payload.athlete_id,
            coach_id=coach.id,
            name=payload.name,
            goal=payload.goal,
            goal_event_date=payload.goal_event_date,
            start_date=payload.start_date,
            end_date=payload.start_date,
            status=TrainingPlanStatus.draft,
            planning_timezone=payload.planning_timezone,
            notes=payload.notes,
        )
        self.db.add(plan)
        self.db.flush()
        today = self._today(plan, None)
        self._log(
            plan,
            ChangeLogEntityType.training_plan,
            plan.id,
            "create",
            self._plan_lock_state(plan, today),
            coach,
            PlanOperation.structure,
            after={"name": plan.name},
            reason=payload.reason,
        )
        self.db.commit()
        plan = self._load_plan(plan.id, "plan")
        return {"plan": self._plan_to_dict(plan, "plan"), "moved": []}, None, 201

    def list_plans_for_athlete(
        self, coach: User, athlete_id: int
    ) -> tuple[dict | None, str | None, int]:
        relation_err = coach_athlete_relation_error(self.db, coach.id, athlete_id)
        if relation_err:
            return None, relation_err, COACH_ATHLETE_NOT_LINKED_STATUS
        plans = self.db.scalars(
            select(TrainingPlan)
            .where(TrainingPlan.athlete_id == athlete_id)
            .order_by(TrainingPlan.start_date.desc(), TrainingPlan.id.desc())
        ).all()
        return {
            "plans": [self._plan_to_dict(p, "plan") for p in plans],
            "count": len(plans),
        }, None, 200

    def get_plan(
        self, user: User, plan_id: int, depth: str = "items"
    ) -> tuple[dict | None, str | None, int]:
        if depth not in ("plan", "mesocycles", "microcycles", "items"):
            return None, "Invalid depth", 400
        plan = self._load_plan(plan_id, depth)
        if not plan:
            return None, "Training plan not found", 404
        auth_err, auth_status = self._authorize_coach_for_plan(user, plan)
        if auth_err:
            return None, auth_err, auth_status
        gaps, conflicts = self._preview_gaps_and_conflicts(plan)
        return {
            "plan": self._plan_to_dict(
                plan, depth, gaps=gaps, conflicts=conflicts
            )
        }, None, 200

    def _preview_gaps_and_conflicts(
        self, plan: TrainingPlan
    ) -> tuple[list[dict], list[dict]]:
        """Derive gaps/anchor conflicts without writing (for GET responses)."""
        today = self._today(plan, None)
        mesos = list(plan.mesocycles or [])
        micros = [m for meso in mesos for m in (meso.microcycles or [])]
        evidence = bulk_evidence_microcycle_ids(self.db, [m.id for m in micros])
        micro_states = {
            m.id: microcycle_lock_state(self.db, m, today, evidence) for m in micros
        }
        meso_states = {
            meso.id: mesocycle_lock_state(self.db, meso, today, evidence, micro_states)
            for meso in mesos
        }
        specs = [
            MesoSpec(
                id=meso.id,
                ordinal=meso.ordinal,
                start_date=meso.start_date,
                end_date=meso.end_date,
                locked=meso_states.get(meso.id) == LockState.locked,
                anchor_date=meso.anchor_date,
                name=meso.name or "",
                empty_duration_days=0,
                micros=[
                    MicroSpec(
                        id=m.id,
                        ordinal=m.ordinal,
                        duration_days=m.duration_days,
                        start_date=m.start_date,
                        end_date=m.end_date,
                        locked=micro_states.get(m.id) == LockState.locked,
                    )
                    for m in (meso.microcycles or [])
                ],
            )
            for meso in mesos
        ]
        _, _, _, gaps, conflicts = reflow(plan.start_date, specs, today=today)
        return [g.to_dict() for g in gaps], [c.to_dict() for c in conflicts]

    def update_plan(
        self, coach: User, plan_id: int, payload: TrainingPlanUpdateRequest
    ) -> tuple[dict | None, str | None, int]:
        plan = self._load_plan(plan_id, "items")
        if not plan:
            return None, "Training plan not found", 404
        auth_err, auth_status = self._authorize_coach_for_plan(coach, plan)
        if auth_err:
            return None, auth_err, auth_status
        if payload.planning_timezone is not None and not is_valid_timezone(
            payload.planning_timezone
        ):
            return None, UNKNOWN_TZ, 400
        today = self._today(plan, None)
        start_date_in_payload = "start_date" in payload.model_fields_set
        operation = (
            PlanOperation.dates if start_date_in_payload else PlanOperation.metadata
        )
        changes = payload.model_dump(exclude_unset=True, exclude={"reason", "strict"})
        before, after = diff_fields(plan, changes)
        if start_date_in_payload:
            plan.start_date = payload.start_date
            # end_date is derived by reflow; clear it in duration mode
            if plan.start_date is None:
                plan.end_date = None
        if payload.name is not None:
            plan.name = payload.name
        if "goal" in payload.model_fields_set:
            plan.goal = payload.goal
        if "goal_event_date" in payload.model_fields_set:
            plan.goal_event_date = payload.goal_event_date
        if "notes" in payload.model_fields_set:
            plan.notes = payload.notes
        if "planning_timezone" in payload.model_fields_set:
            plan.planning_timezone = payload.planning_timezone
        if payload.status is not None:
            if payload.status == TrainingPlanStatus.active:
                overlap = self._assert_no_active_overlap(
                    plan.athlete_id, plan.start_date, plan.end_date, exclude_plan_id=plan.id
                )
                if overlap:
                    return None, overlap, 409
            plan.status = payload.status
        moved: list[dict] = []
        conflicts: list[dict] = []
        gaps: list[dict] = []
        anchor_conflicts: list[dict] = []
        if start_date_in_payload:
            moved, conflicts, gaps, anchor_conflicts, err, status = self._apply_reflow(
                plan, today, strict=payload.strict
            )
            if err:
                return None, err, status
            self._log_reflow_if_moved(plan, moved, today, coach, payload.reason)
        self._log(
            plan,
            ChangeLogEntityType.training_plan,
            plan.id,
            "update",
            self._plan_lock_state(plan, today),
            coach,
            operation,
            before=before,
            after=after,
            reason=payload.reason,
        )
        self.db.commit()
        plan = self._load_plan(plan_id, "items")
        return {
            "plan": self._plan_to_dict(
                plan, "items", today, gaps=gaps, conflicts=anchor_conflicts
            ),
            "moved": moved,
            "conflicts": conflicts,
            "gaps": gaps,
            "anchor_conflicts": anchor_conflicts,
        }, None, 200

    def delete_plan(
        self, coach: User, plan_id: int
    ) -> tuple[dict | None, str | None, int]:
        plan = self._load_plan(plan_id, "items")
        if not plan:
            return None, "Training plan not found", 404
        auth_err, auth_status = self._authorize_coach_for_plan(coach, plan)
        if auth_err:
            return None, auth_err, auth_status
        today = self._today(plan, None)
        if self._any_locked_period(plan, today):
            return None, "Cannot delete a plan that contains a completed training period", 409
        self._log(
            plan,
            ChangeLogEntityType.training_plan,
            plan.id,
            "delete",
            self._plan_lock_state(plan, today),
            coach,
            PlanOperation.delete,
        )
        self.db.delete(plan)
        self.db.commit()
        return {"deleted": True, "plan_id": plan_id, "moved": []}, None, 200

    def list_change_log(
        self,
        coach: User,
        plan_id: int,
        entity_type: str | None = None,
        entity_id: int | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> tuple[dict | None, str | None, int]:
        plan = self._load_plan(plan_id, "plan")
        if not plan:
            return None, "Training plan not found", 404
        auth_err, auth_status = self._authorize_coach_for_plan(coach, plan)
        if auth_err:
            return None, auth_err, auth_status
        stmt = select(PlanChangeLog).where(PlanChangeLog.training_plan_id == plan_id)
        if entity_type:
            stmt = stmt.where(PlanChangeLog.entity_type == entity_type)
        if entity_id is not None:
            stmt = stmt.where(PlanChangeLog.entity_id == entity_id)
        rows = self.db.scalars(
            stmt.order_by(PlanChangeLog.changed_at.desc(), PlanChangeLog.id.desc()).offset(
                offset
            ).limit(min(limit, 500))
        ).all()
        return {
            "changes": [
                {
                    "id": r.id,
                    "entity_type": r.entity_type,
                    "entity_id": r.entity_id,
                    "operation": r.operation,
                    "plan_operation": _enum_val(r.plan_operation),
                    "lock_state_at_change": r.lock_state_at_change,
                    "changed_by_id": r.changed_by_id,
                    "changed_at": _iso(r.changed_at),
                    "before": r.before,
                    "after": r.after,
                    "reason": r.reason,
                }
                for r in rows
            ],
            "count": len(rows),
        }, None, 200

    def create_mesocycle(
        self, coach: User, plan_id: int, payload: MesocycleCreateRequest
    ) -> tuple[dict | None, str | None, int]:
        plan = self._load_plan(plan_id, "items")
        if not plan:
            return None, "Training plan not found", 404
        auth_err, auth_status = self._authorize_coach_for_plan(coach, plan)
        if auth_err:
            return None, auth_err, auth_status
        today = self._today(plan, None)
        if payload.anchor_date is not None and plan.start_date is None:
            return None, "Set a plan start date before anchoring a block", 400
        if payload.anchor_date is not None and payload.anchor_date < today:
            return None, "Anchors are not available for historical dates", 400
        mesos = list(plan.mesocycles or [])
        if len(mesos) >= MAX_MESOCYCLES:
            return None, "A plan cannot have more than 52 mesocycles", 400
        _ms, meso_states, _ = self._lock_maps(plan, today)
        locked_prefix = self._locked_prefix_ids(mesos, meso_states)
        insert_at = payload.insert_at_ordinal
        if insert_at is None or insert_at > len(mesos):
            insert_at = len(mesos)
        if insert_at < len(locked_prefix):
            return None, "Cannot insert a mesocycle before a completed training period", 409
        micro_count = payload.microcycle_count or 0
        micro_dur = payload.microcycle_duration_days or 7
        for i, obj in enumerate(sorted(mesos, key=lambda m: m.ordinal)):
            obj.ordinal = REORDER_OFFSET + i
        self.db.flush()
        for i, obj in enumerate(sorted(mesos, key=lambda m: m.ordinal)):
            obj.ordinal = i if i < insert_at else i + 1
        self.db.flush()
        meso = Mesocycle(
            training_plan_id=plan.id,
            name=payload.name,
            focus=payload.focus,
            intent=payload.intent,
            start_date=None,
            end_date=None,
            anchor_date=payload.anchor_date,
            ordinal=insert_at,
        )
        self.db.add(meso)
        self.db.flush()
        if micro_count:
            for i in range(micro_count):
                self.db.add(
                    Microcycle(
                        mesocycle_id=meso.id,
                        start_date=None,
                        end_date=None,
                        duration_days=micro_dur,
                        ordinal=i,
                    )
                )
        moved, conflicts, gaps, anchor_conflicts, err, status = self._apply_reflow(
            plan, today, payload.strict
        )
        if err:
            return None, err, status
        self._log(
            plan, ChangeLogEntityType.mesocycle, meso.id, "create",
            LockState.future, coach, PlanOperation.structure,
            after={"name": meso.name, "anchor_date": _iso(meso.anchor_date)},
            reason=payload.reason,
        )
        if moved:
            self._log_reflow_if_moved(plan, moved, today, coach, payload.reason)
        self.db.commit()
        plan = self._load_plan(plan_id, "items")
        created = next(m for m in plan.mesocycles if m.id == meso.id)
        return {
            "mesocycle": self._meso_to_dict(
                created, None, {}, "items", conflict=next(
                    (c for c in anchor_conflicts if c.get("meso_id") == created.id), None
                )
            ),
            "plan": self._plan_to_dict(
                plan, "items", today, gaps=gaps, conflicts=anchor_conflicts
            ),
            "moved": moved,
            "conflicts": conflicts,
            "gaps": gaps,
            "anchor_conflicts": anchor_conflicts,
        }, None, 201

    def update_mesocycle(
        self, coach: User, mesocycle_id: int, payload: MesocycleUpdateRequest
    ) -> tuple[dict | None, str | None, int]:
        meso = self._load_mesocycle(mesocycle_id)
        if not meso:
            return None, "Mesocycle not found", 404
        plan = self._plan_of_meso(meso)
        auth_err, auth_status = self._authorize_coach_for_plan(coach, plan)
        if auth_err:
            return None, auth_err, auth_status
        today = self._today(plan, None)
        state = mesocycle_lock_state(self.db, meso, today)
        anchor_in_payload = "anchor_date" in payload.model_fields_set
        operation = PlanOperation.dates if anchor_in_payload else PlanOperation.metadata
        err, status = assert_mutable(state, operation, payload.reason)
        if err:
            return None, err, status
        if anchor_in_payload:
            if state == LockState.locked:
                return None, "Anchors are never available for historical blocks", 409
            if payload.anchor_date is not None and plan.start_date is None:
                return None, "Set a plan start date before anchoring a block", 400
            if payload.anchor_date is not None and payload.anchor_date < today:
                return None, "Anchors are not available for historical dates", 400
        changes = payload.model_dump(exclude_unset=True, exclude={"reason", "strict"})
        before, after = diff_fields(meso, changes)
        if payload.name is not None:
            meso.name = payload.name
        if "focus" in payload.model_fields_set:
            meso.focus = payload.focus
        if "intent" in payload.model_fields_set:
            meso.intent = payload.intent
        if anchor_in_payload:
            meso.anchor_date = payload.anchor_date
        moved: list[dict] = []
        conflicts: list[dict] = []
        gaps: list[dict] = []
        anchor_conflicts: list[dict] = []
        if anchor_in_payload:
            moved, conflicts, gaps, anchor_conflicts, rerr, rstatus = self._apply_reflow(
                plan, today, payload.strict
            )
            if rerr:
                return None, rerr, rstatus
            self._log_reflow_if_moved(plan, moved, today, coach, payload.reason)
        self._log(
            plan, ChangeLogEntityType.mesocycle, meso.id, "update",
            state, coach, operation, before=before, after=after,
            reason=payload.reason,
        )
        self.db.commit()
        meso = self._load_mesocycle(mesocycle_id)
        plan = self._plan_of_meso(meso)
        return {
            "mesocycle": self._meso_to_dict(meso, state, {}, "items"),
            "moved": moved,
            "conflicts": conflicts,
            "gaps": gaps,
            "anchor_conflicts": anchor_conflicts,
        }, None, 200

    def delete_mesocycle(
        self, coach: User, mesocycle_id: int
    ) -> tuple[dict | None, str | None, int]:
        meso = self._load_mesocycle(mesocycle_id)
        if not meso:
            return None, "Mesocycle not found", 404
        plan = self._plan_of_meso(meso)
        auth_err, auth_status = self._authorize_coach_for_plan(coach, plan)
        if auth_err:
            return None, auth_err, auth_status
        today = self._today(plan, None)
        state = mesocycle_lock_state(self.db, meso, today)
        err, status = assert_mutable(state, PlanOperation.delete, None)
        if err:
            return None, err, status
        for micro in meso.microcycles or []:
            if any(i.workout_id is not None for i in (micro.items or [])):
                return None, "Cannot delete a mesocycle that contains a workout", 409
        deleted_id, ordinal = meso.id, meso.ordinal
        self._log(
            plan, ChangeLogEntityType.mesocycle, deleted_id, "delete",
            state, coach, PlanOperation.delete,
        )
        self.db.delete(meso)
        self.db.flush()
        for other in self.db.scalars(
            select(Mesocycle).where(
                Mesocycle.training_plan_id == plan.id, Mesocycle.ordinal > ordinal
            )
        ):
            other.ordinal -= 1
        moved, conflicts, gaps, anchor_conflicts, rerr, rstatus = self._apply_reflow(plan, today)
        if rerr:
            return None, rerr, rstatus
        self._log_reflow_if_moved(plan, moved, today, coach, None)
        self.db.commit()
        return {
            "deleted": True,
            "mesocycle_id": deleted_id,
            "moved": moved,
            "conflicts": conflicts,
        }, None, 200

    def reorder_mesocycles(
        self, coach: User, plan_id: int, ordered_ids: list[int], reason: str | None = None
    ) -> tuple[dict | None, str | None, int]:
        plan = self._load_plan(plan_id, "items")
        if not plan:
            return None, "Training plan not found", 404
        auth_err, auth_status = self._authorize_coach_for_plan(coach, plan)
        if auth_err:
            return None, auth_err, auth_status
        today = self._today(plan, None)
        mesos = list(plan.mesocycles or [])
        _ms, meso_states, _ = self._lock_maps(plan, today)
        prefix = self._locked_prefix_ids(mesos, meso_states)
        if ordered_ids[: len(prefix)] != prefix:
            return None, "Cannot reorder across a locked boundary", 409
        err = self._two_phase_reorder(mesos, ordered_ids)
        if err:
            return None, err, 400
        moved, conflicts, gaps, anchor_conflicts, rerr, status = self._apply_reflow(plan, today)
        if rerr:
            return None, rerr, status
        self._log_reflow_if_moved(plan, moved, today, coach, reason)
        self._log(
            plan, ChangeLogEntityType.training_plan, plan.id, "reorder",
            self._plan_lock_state(plan, today), coach, PlanOperation.structure,
            after={"ordered_ids": ordered_ids}, reason=reason,
        )
        self.db.commit()
        plan = self._load_plan(plan_id, "items")
        return {
            "plan": self._plan_to_dict(plan, "items", today),
            "moved": moved,
            "conflicts": conflicts,
        }, None, 200

    def create_microcycle(
        self, coach: User, mesocycle_id: int, payload: MicrocycleCreateRequest
    ) -> tuple[dict | None, str | None, int]:
        meso = self._load_mesocycle(mesocycle_id)
        if not meso:
            return None, "Mesocycle not found", 404
        plan = self._plan_of_meso(meso)
        auth_err, auth_status = self._authorize_coach_for_plan(coach, plan)
        if auth_err:
            return None, auth_err, auth_status
        today = self._today(plan, None)
        micros = list(meso.microcycles or [])
        if len(micros) >= MAX_MICROCYCLES:
            return None, "A mesocycle cannot have more than 52 microcycles", 400
        evidence = bulk_evidence_microcycle_ids(self.db, [m.id for m in micros])
        micro_states = {
            m.id: microcycle_lock_state(self.db, m, today, evidence) for m in micros
        }
        meso_state = mesocycle_lock_state(self.db, meso, today, evidence, micro_states)
        if meso_state == LockState.locked and self._meso_fully_locked(micros, micro_states):
            err, status = assert_mutable(meso_state, PlanOperation.structure, payload.reason)
            if err:
                return None, err, status
        prefix = self._locked_prefix_ids(micros, micro_states)
        insert_at = payload.insert_at_ordinal
        if insert_at is None or insert_at > len(micros):
            insert_at = len(micros)
        if insert_at < len(prefix):
            return None, "Cannot insert a microcycle before a completed training period", 409
        for i, obj in enumerate(sorted(micros, key=lambda m: m.ordinal)):
            obj.ordinal = REORDER_OFFSET + i
        self.db.flush()
        for i, obj in enumerate(sorted(micros, key=lambda m: m.ordinal)):
            obj.ordinal = i if i < insert_at else i + 1
        self.db.flush()
        micro = Microcycle(
            mesocycle_id=meso.id,
            name=payload.name,
            intent=payload.intent,
            start_date=None,
            end_date=None,
            duration_days=payload.duration_days,
            ordinal=insert_at,
        )
        self.db.add(micro)
        self.db.flush()
        moved, conflicts, gaps, anchor_conflicts, err, status = self._apply_reflow(
            plan, today, payload.strict
        )
        if err:
            return None, err, status
        self._log(
            plan, ChangeLogEntityType.microcycle, micro.id, "create",
            LockState.future, coach, PlanOperation.structure,
            after={"duration_days": payload.duration_days}, reason=payload.reason,
        )
        self._log_reflow_if_moved(plan, moved, today, coach, payload.reason)
        self.db.commit()
        micro = self._load_microcycle(micro.id)
        return {
            "microcycle": self._micro_to_dict(micro, LockState.future, True),
            "moved": moved,
            "conflicts": conflicts,
            "gaps": gaps,
            "anchor_conflicts": anchor_conflicts,
        }, None, 201

    def update_microcycle(
        self, coach: User, microcycle_id: int, payload: MicrocycleUpdateRequest
    ) -> tuple[dict | None, str | None, int]:
        micro = self._load_microcycle(microcycle_id)
        if not micro:
            return None, "Microcycle not found", 404
        plan = self._plan_of_micro(micro)
        auth_err, auth_status = self._authorize_coach_for_plan(coach, plan)
        if auth_err:
            return None, auth_err, auth_status
        today = self._today(plan, None)
        state = microcycle_lock_state(self.db, micro, today)
        operation = (
            PlanOperation.dates if payload.duration_days is not None else PlanOperation.metadata
        )
        err, status = assert_mutable(state, operation, payload.reason)
        if err:
            return None, err, status
        if (
            state == LockState.current
            and payload.duration_days is not None
            and micro.start_date is not None
        ):
            new_end = micro.start_date + timedelta(days=payload.duration_days - 1)
            if new_end < today:
                return None, "end_date cannot move earlier than today", 409
        changes = payload.model_dump(exclude_unset=True, exclude={"reason", "strict"})
        before, after = diff_fields(micro, changes)
        if payload.name is not None:
            micro.name = payload.name
        if "intent" in payload.model_fields_set:
            micro.intent = payload.intent
        moved: list[dict] = []
        conflicts: list[dict] = []
        gaps: list[dict] = []
        anchor_conflicts: list[dict] = []
        if payload.duration_days is not None:
            micro.duration_days = payload.duration_days
            moved, conflicts, gaps, anchor_conflicts, rerr, rstatus = self._apply_reflow(
                plan, today, payload.strict
            )
            if rerr:
                return None, rerr, rstatus
            self._log_reflow_if_moved(plan, moved, today, coach, payload.reason)
        self._log(
            plan, ChangeLogEntityType.microcycle, micro.id, "update",
            state, coach, operation, before=before, after=after, reason=payload.reason,
        )
        self.db.commit()
        micro = self._load_microcycle(microcycle_id)
        new_state = microcycle_lock_state(self.db, micro, today)
        return {
            "microcycle": self._micro_to_dict(micro, new_state, True),
            "moved": moved,
            "conflicts": conflicts,
            "gaps": gaps,
            "anchor_conflicts": anchor_conflicts,
        }, None, 200

    def delete_microcycle(
        self, coach: User, microcycle_id: int
    ) -> tuple[dict | None, str | None, int]:
        micro = self._load_microcycle(microcycle_id)
        if not micro:
            return None, "Microcycle not found", 404
        plan = self._plan_of_micro(micro)
        auth_err, auth_status = self._authorize_coach_for_plan(coach, plan)
        if auth_err:
            return None, auth_err, auth_status
        today = self._today(plan, None)
        state = microcycle_lock_state(self.db, micro, today)
        err, status = assert_mutable(state, PlanOperation.delete, None)
        if err:
            return None, err, status
        if any(i.workout_id is not None for i in (micro.items or [])):
            return None, "Cannot delete a microcycle that contains a workout", 409
        meso_id, ordinal, deleted_id = micro.mesocycle_id, micro.ordinal, micro.id
        self._log(
            plan, ChangeLogEntityType.microcycle, deleted_id, "delete",
            state, coach, PlanOperation.delete,
        )
        self.db.delete(micro)
        self.db.flush()
        for other in self.db.scalars(
            select(Microcycle).where(
                Microcycle.mesocycle_id == meso_id, Microcycle.ordinal > ordinal
            )
        ):
            other.ordinal -= 1
        moved, conflicts, gaps, anchor_conflicts, rerr, rstatus = self._apply_reflow(plan, today)
        if rerr:
            return None, rerr, rstatus
        self._log_reflow_if_moved(plan, moved, today, coach, None)
        self.db.commit()
        return {
            "deleted": True,
            "microcycle_id": deleted_id,
            "moved": moved,
            "conflicts": conflicts,
        }, None, 200

    def reorder_microcycles(
        self,
        coach: User,
        mesocycle_id: int,
        ordered_ids: list[int],
        reason: str | None = None,
    ) -> tuple[dict | None, str | None, int]:
        meso = self._load_mesocycle(mesocycle_id)
        if not meso:
            return None, "Mesocycle not found", 404
        plan = self._plan_of_meso(meso)
        auth_err, auth_status = self._authorize_coach_for_plan(coach, plan)
        if auth_err:
            return None, auth_err, auth_status
        today = self._today(plan, None)
        micros = list(meso.microcycles or [])
        evidence = bulk_evidence_microcycle_ids(self.db, [m.id for m in micros])
        micro_states = {
            m.id: microcycle_lock_state(self.db, m, today, evidence) for m in micros
        }
        prefix = self._locked_prefix_ids(micros, micro_states)
        if ordered_ids[: len(prefix)] != prefix:
            return None, "Cannot reorder across a locked boundary", 409
        err = self._two_phase_reorder(micros, ordered_ids)
        if err:
            return None, err, 400
        moved, conflicts, gaps, anchor_conflicts, rerr, status = self._apply_reflow(plan, today)
        if rerr:
            return None, rerr, status
        self._log_reflow_if_moved(plan, moved, today, coach, reason)
        self._log(
            plan, ChangeLogEntityType.mesocycle, meso.id, "reorder",
            mesocycle_lock_state(self.db, meso, today, evidence, micro_states),
            coach, PlanOperation.structure,
            after={"ordered_ids": ordered_ids}, reason=reason,
        )
        self.db.commit()
        meso = self._load_mesocycle(mesocycle_id)
        return {
            "mesocycle": self._meso_to_dict(meso, None, micro_states, "items"),
            "moved": moved,
            "conflicts": conflicts,
        }, None, 200

    def move_microcycle(
        self,
        coach: User,
        microcycle_id: int,
        target_mesocycle_id: int,
        insert_at_ordinal: int = 0,
        reason: str | None = None,
    ) -> tuple[dict | None, str | None, int]:
        micro = self._load_microcycle(microcycle_id)
        if not micro:
            return None, "Microcycle not found", 404
        dest = self._load_mesocycle(target_mesocycle_id)
        if not dest:
            return None, "Mesocycle not found", 404
        plan = self._plan_of_micro(micro)
        dest_plan = self._plan_of_meso(dest)
        if plan.id != dest_plan.id:
            return None, "Microcycle must stay inside the same training plan", 400
        auth_err, auth_status = self._authorize_coach_for_plan(coach, plan)
        if auth_err:
            return None, auth_err, auth_status
        today = self._today(plan, None)
        source = micro.mesocycle
        state = microcycle_lock_state(self.db, micro, today)
        err, status = assert_mutable(state, PlanOperation.structure, reason)
        if err:
            return None, err, status
        dest_micros = list(dest.microcycles or [])
        dest_evidence = bulk_evidence_microcycle_ids(self.db, [m.id for m in dest_micros])
        dest_states = {
            m.id: microcycle_lock_state(self.db, m, today, dest_evidence) for m in dest_micros
        }
        dest_meso_state = mesocycle_lock_state(
            self.db, dest, today, dest_evidence, dest_states
        )
        if dest_meso_state == LockState.locked and self._meso_fully_locked(
            dest_micros, dest_states
        ):
            err, status = assert_mutable(dest_meso_state, PlanOperation.structure, reason)
            if err:
                return None, err, status
        dest_prefix = self._locked_prefix_ids(dest_micros, dest_states)
        insert_at = insert_at_ordinal
        if insert_at is None or insert_at > len(dest_micros):
            insert_at = len(dest_micros)
        if insert_at < len(dest_prefix):
            return None, "Cannot insert a microcycle before a completed training period", 409
        source_remaining = [m for m in list(source.microcycles or []) if m.id != micro.id]
        dest_list = [m for m in dest_micros if m.id != micro.id]
        dest_list.insert(insert_at, micro)
        touched = source_remaining + dest_list
        for i, obj in enumerate(touched):
            obj.ordinal = REORDER_OFFSET + i
        self.db.flush()
        micro.mesocycle_id = dest.id
        for i, obj in enumerate(source_remaining):
            obj.ordinal = i
        for i, obj in enumerate(dest_list):
            obj.ordinal = i
        self.db.flush()
        self.db.expire(source, ["microcycles"])
        self.db.expire(dest, ["microcycles"])
        moved, conflicts, gaps, anchor_conflicts, rerr, rstatus = self._apply_reflow(plan, today)
        if rerr:
            return None, rerr, rstatus
        self._log(
            plan, ChangeLogEntityType.microcycle, micro.id, "move",
            state, coach, PlanOperation.structure,
            after={
                "from_mesocycle_id": source.id,
                "to_mesocycle_id": dest.id,
                "insert_at_ordinal": insert_at,
            },
            reason=reason,
        )
        self._log_reflow_if_moved(plan, moved, today, coach, reason)
        self.db.commit()
        micro = self._load_microcycle(microcycle_id)
        return {
            "microcycle": self._micro_to_dict(micro, None, True),
            "moved": moved,
            "conflicts": conflicts,
        }, None, 200

    def create_item(
        self, coach: User, microcycle_id: int, payload: PlanItemCreateRequest
    ) -> tuple[dict | None, str | None, int]:
        micro = self._load_microcycle(microcycle_id)
        if not micro:
            return None, "Microcycle not found", 404
        plan = self._plan_of_micro(micro)
        auth_err, auth_status = self._authorize_coach_for_plan(coach, plan)
        if auth_err:
            return None, auth_err, auth_status
        today = self._today(plan, None)
        state = microcycle_lock_state(self.db, micro, today)
        err, status = assert_mutable(state, PlanOperation.structure, payload.reason)
        if err:
            return None, err, status
        ptype, pday, pdate, perr = _validate_and_normalize_placement(
            micro,
            payload.placement_type,
            payload.placement_day,
            payload.placement_date,
        )
        if perr:
            return None, perr, 400
        if state == LockState.current and ptype is not None:
            resolved = None
            if ptype == PlacementType.relative_day and pday is not None and micro.start_date:
                resolved = micro.start_date + timedelta(days=pday - 1)
            elif ptype == PlacementType.specific_date:
                resolved = pdate
            if resolved is not None and resolved <= today:
                return None, "Cannot add a past-dated item to the current period", 409
        items = list(micro.items or [])
        insert_at = payload.insert_at_ordinal
        if insert_at is None or insert_at > len(items):
            insert_at = len(items)
        for i, obj in enumerate(sorted(items, key=lambda m: m.ordinal)):
            obj.ordinal = REORDER_OFFSET + i
        self.db.flush()
        for i, obj in enumerate(sorted(items, key=lambda m: m.ordinal)):
            obj.ordinal = i if i < insert_at else i + 1
        self.db.flush()
        item = PlanItem(
            microcycle_id=micro.id,
            ordinal=insert_at,
            placement_type=ptype,
            placement_day=pday,
            placement_date=pdate,
            title=payload.title,
            intent=payload.intent,
            planned_workout_type=(
                payload.planned_workout_type.value if payload.planned_workout_type else None
            ),
            planned_sport_id=payload.planned_sport_id,
            planned_duration_min=payload.planned_duration_min,
            planned_distance_m=payload.planned_distance_m,
        )
        self.db.add(item)
        self.db.flush()
        self._log(
            plan, ChangeLogEntityType.plan_item, item.id, "create",
            state, coach, PlanOperation.structure,
            after={"title": item.title}, reason=payload.reason,
        )
        self.db.commit()
        return {"item": self._item_to_dict(self._load_item(item.id)), "moved": []}, None, 201

    def update_item(
        self, coach: User, item_id: int, payload: PlanItemUpdateRequest
    ) -> tuple[dict | None, str | None, int]:
        item = self._load_item(item_id)
        if not item:
            return None, "Plan item not found", 404
        plan = self._plan_of_item(item)
        auth_err, auth_status = self._authorize_coach_for_plan(coach, plan)
        if auth_err:
            return None, auth_err, auth_status
        micro = item.microcycle
        today = self._today(plan, None)
        state = microcycle_lock_state(self.db, micro, today)
        operation = (
            PlanOperation.association
            if _placement_fields_set(payload)
            else PlanOperation.metadata
        )
        err, status = assert_mutable(state, operation, payload.reason)
        if err:
            return None, err, status
        changes = payload.model_dump(exclude_unset=True, exclude={"reason", "strict"})
        if "planned_workout_type" in changes and payload.planned_workout_type is not None:
            changes["planned_workout_type"] = payload.planned_workout_type.value
        before, after = diff_fields(item, changes)
        if payload.title is not None:
            item.title = payload.title
        if "intent" in payload.model_fields_set:
            item.intent = payload.intent
        if _placement_fields_set(payload):
            # Explicit null placement_type clears placement.
            clearing = (
                "placement_type" in payload.model_fields_set
                and payload.placement_type is None
            )
            next_type = (
                payload.placement_type
                if "placement_type" in payload.model_fields_set
                else item.placement_type
            )
            if clearing:
                next_type, next_day, next_date = None, None, None
            elif next_type == PlacementType.relative_day:
                next_day = (
                    payload.placement_day
                    if "placement_day" in payload.model_fields_set
                    else item.placement_day
                )
                next_date = None
            elif next_type == PlacementType.specific_date:
                next_date = (
                    payload.placement_date
                    if "placement_date" in payload.model_fields_set
                    else item.placement_date
                )
                next_day = None
            else:
                next_day = None
                next_date = None
            ptype, pday, pdate, perr = _validate_and_normalize_placement(
                micro, next_type, next_day, next_date, clearing=clearing
            )
            if perr:
                return None, perr, 400
            item.placement_type = ptype
            item.placement_day = pday
            item.placement_date = pdate
        if "planned_workout_type" in payload.model_fields_set:
            item.planned_workout_type = (
                payload.planned_workout_type.value if payload.planned_workout_type else None
            )
        if "planned_sport_id" in payload.model_fields_set:
            item.planned_sport_id = payload.planned_sport_id
        if "planned_duration_min" in payload.model_fields_set:
            item.planned_duration_min = payload.planned_duration_min
        if "planned_distance_m" in payload.model_fields_set:
            item.planned_distance_m = payload.planned_distance_m
        self._log(
            plan, ChangeLogEntityType.plan_item, item.id, "update",
            state, coach, operation, before=before, after=after, reason=payload.reason,
        )
        self.db.commit()
        return {"item": self._item_to_dict(self._load_item(item_id)), "moved": []}, None, 200

    def delete_item(
        self, coach: User, item_id: int
    ) -> tuple[dict | None, str | None, int]:
        item = self._load_item(item_id)
        if not item:
            return None, "Plan item not found", 404
        plan = self._plan_of_item(item)
        auth_err, auth_status = self._authorize_coach_for_plan(coach, plan)
        if auth_err:
            return None, auth_err, auth_status
        micro = item.microcycle
        today = self._today(plan, None)
        state = microcycle_lock_state(self.db, micro, today)
        err, status = assert_mutable(state, PlanOperation.structure, None)
        if err:
            return None, err, status
        if item.workout_id:
            workout = self.db.get(Workout, item.workout_id)
            if workout and self._workout_has_evidence(workout):
                return None, "Cannot delete an item that holds executed training", 409
        deleted_id, ordinal, micro_id = item.id, item.ordinal, item.microcycle_id
        self._log(
            plan, ChangeLogEntityType.plan_item, deleted_id, "delete",
            state, coach, PlanOperation.structure,
        )
        self.db.delete(item)
        self.db.flush()
        for other in self.db.scalars(
            select(PlanItem).where(
                PlanItem.microcycle_id == micro_id, PlanItem.ordinal > ordinal
            )
        ):
            other.ordinal -= 1
        self.db.commit()
        return {"deleted": True, "item_id": deleted_id, "moved": []}, None, 200

    def reorder_items(
        self,
        coach: User,
        microcycle_id: int,
        ordered_ids: list[int],
        reason: str | None = None,
    ) -> tuple[dict | None, str | None, int]:
        micro = self._load_microcycle(microcycle_id)
        if not micro:
            return None, "Microcycle not found", 404
        plan = self._plan_of_micro(micro)
        auth_err, auth_status = self._authorize_coach_for_plan(coach, plan)
        if auth_err:
            return None, auth_err, auth_status
        today = self._today(plan, None)
        state = microcycle_lock_state(self.db, micro, today)
        err, status = assert_mutable(state, PlanOperation.structure, reason)
        if err:
            return None, err, status
        rerr = self._two_phase_reorder(list(micro.items or []), ordered_ids)
        if rerr:
            return None, rerr, 400
        self._log(
            plan, ChangeLogEntityType.microcycle, micro.id, "reorder",
            state, coach, PlanOperation.structure,
            after={"ordered_ids": ordered_ids}, reason=reason,
        )
        self.db.commit()
        micro = self._load_microcycle(microcycle_id)
        return {"items": [self._item_to_dict(i) for i in micro.items], "moved": []}, None, 200

    def attach_workout(
        self, coach: User, item_id: int, workout_id: int, reason: str | None = None,
        commit: bool = True,
    ) -> tuple[dict | None, str | None, int]:
        item = self._load_item(item_id)
        if not item:
            return None, "Plan item not found", 404
        plan = self._plan_of_item(item)
        auth_err, auth_status = self._authorize_coach_for_plan(coach, plan)
        if auth_err:
            return None, auth_err, auth_status
        micro = item.microcycle
        today = self._today(plan, None)
        state = microcycle_lock_state(self.db, micro, today)
        err, status = assert_mutable(state, PlanOperation.association, reason)
        if err:
            return None, err, status
        workout = self.db.get(Workout, workout_id)
        if not workout or workout.athlete_id != plan.athlete_id:
            return None, "Workout not found", 404
        existing = self.db.scalar(
            select(PlanItem).where(PlanItem.workout_id == workout_id, PlanItem.id != item.id)
        )
        if existing:
            return None, "Workout is already part of a training cycle", 409
        if micro.start_date is None or micro.end_date is None:
            return (
                None,
                "Set a plan start date before attaching a workout — workouts need a scheduled date",
                400,
            )
        if not (micro.start_date <= workout.scheduled_date <= micro.end_date):
            return None, "Workout scheduled_date must fall inside the microcycle", 400
        item.workout_id = workout_id
        item.converted_at = datetime.utcnow()
        item.converted_by_id = coach.id
        self._log(
            plan, ChangeLogEntityType.plan_item, item.id, "attach_workout",
            state, coach, PlanOperation.association,
            after={"workout_id": workout_id}, reason=reason,
        )
        if commit:
            self.db.commit()
            item = self._load_item(item_id)
        return {"item": self._item_to_dict(item), "moved": []}, None, 200

    def detach_workout(
        self, coach: User, item_id: int, reason: str | None = None
    ) -> tuple[dict | None, str | None, int]:
        item = self._load_item(item_id)
        if not item:
            return None, "Plan item not found", 404
        plan = self._plan_of_item(item)
        auth_err, auth_status = self._authorize_coach_for_plan(coach, plan)
        if auth_err:
            return None, auth_err, auth_status
        micro = item.microcycle
        today = self._today(plan, None)
        state = microcycle_lock_state(self.db, micro, today)
        err, status = assert_mutable(state, PlanOperation.association, reason)
        if err:
            return None, err, status
        if item.workout_id:
            workout = self.db.get(Workout, item.workout_id)
            if workout and self._workout_has_evidence(workout):
                return None, "Cannot detach an executed workout", 409
        before = {"workout_id": item.workout_id}
        item.workout_id = None
        self._log(
            plan, ChangeLogEntityType.plan_item, item.id, "detach_workout",
            state, coach, PlanOperation.association,
            before=before, after={"workout_id": None}, reason=reason,
        )
        self.db.commit()
        return {"item": self._item_to_dict(self._load_item(item_id)), "moved": []}, None, 200

    def get_builder_context(
        self, coach: User, item_id: int
    ) -> tuple[dict | None, str | None, int]:
        item = self._load_item(item_id)
        if not item:
            return None, "Plan item not found", 404
        plan = self._plan_of_item(item)
        auth_err, auth_status = self._authorize_coach_for_plan(coach, plan)
        if auth_err:
            return None, auth_err, auth_status
        micro = item.microcycle
        meso = micro.mesocycle
        placement = _resolve_placement(item, micro)
        suggested_date = None
        if placement and placement.get("resolved_date"):
            suggested_date = date.fromisoformat(placement["resolved_date"])
        else:
            suggested_date = micro.start_date
        return {
            "plan_item_id": item.id,
            "athlete_id": plan.athlete_id,
            "title": item.title,
            "intent": item.intent,
            "training_plan": {"id": plan.id, "name": plan.name, "goal": plan.goal},
            "mesocycle": {"id": meso.id, "name": meso.name, "intent": meso.intent},
            "microcycle": {
                "id": micro.id,
                "ordinal": micro.ordinal,
                "name": micro.name,
                "intent": micro.intent,
                "start_date": _iso(micro.start_date),
                "end_date": _iso(micro.end_date),
            },
            "suggested": {
                "sport_id": item.planned_sport_id,
                "workout_type": item.planned_workout_type,
                "scheduled_date": _iso(suggested_date),
                "duration_min": item.planned_duration_min,
                "distance_m": item.planned_distance_m,
            },
        }, None, 200

    def create_workout_for_item(
        self, coach: User, item_id: int, payload: WorkoutCreateRequest
    ) -> tuple[dict | None, str | None, int]:
        item = self._load_item(item_id)
        if not item:
            return None, "Plan item not found", 404
        plan = self._plan_of_item(item)
        auth_err, auth_status = self._authorize_coach_for_plan(coach, plan)
        if auth_err:
            return None, auth_err, auth_status
        if payload.athlete_id != plan.athlete_id:
            return None, "Workout athlete must match the training plan athlete", 400
        from src.modules.training.service import TrainingService

        training = TrainingService(self.db)
        result, err, status = training.create_workout(coach, payload, commit=False)
        if err:
            self.db.rollback()
            return None, err, status
        workout_id = result["workout"]["id"]
        attach_result, aerr, astatus = self.attach_workout(
            coach, item_id, workout_id, commit=False
        )
        if aerr:
            self.db.rollback()
            return None, aerr, astatus
        self.db.commit()
        return {
            "item": attach_result["item"],
            "workout": result["workout"],
            "moved": [],
        }, None, 201

    def generate_system_analysis(
        self, coach: User, mesocycle_id: int
    ) -> tuple[dict | None, str | None, int]:
        meso = self._load_mesocycle(mesocycle_id)
        if not meso:
            return None, "Mesocycle not found", 404
        plan = self._plan_of_meso(meso)
        auth_err, auth_status = self._authorize_coach_for_plan(coach, plan)
        if auth_err:
            return None, auth_err, auth_status
        today = self._today(plan, None)
        cutoff = min(meso.end_date, today)
        generated = generate_mesocycle_analysis(self.db, meso, cutoff)
        existing = self.db.scalar(
            select(CycleSystemAnalysis).where(
                CycleSystemAnalysis.mesocycle_id == meso.id,
                CycleSystemAnalysis.generator_version == generated["generator_version"],
                CycleSystemAnalysis.data_cutoff_date == cutoff,
            )
        )
        if existing:
            return {"system_analysis": self._analysis_to_dict(existing)}, None, 200
        row = CycleSystemAnalysis(
            mesocycle_id=meso.id,
            generated_at=datetime.utcnow(),
            generator=generated["generator"],
            generator_version=generated["generator_version"],
            data_cutoff_date=cutoff,
            summary=generated["summary"],
            metrics=generated["metrics"],
            source_refs=generated["source_refs"],
        )
        self.db.add(row)
        self.db.commit()
        return {"system_analysis": self._analysis_to_dict(row)}, None, 201

    def get_system_analysis(
        self, coach: User, mesocycle_id: int, all_rows: bool = False
    ) -> tuple[dict | None, str | None, int]:
        meso = self._load_mesocycle(mesocycle_id)
        if not meso:
            return None, "Mesocycle not found", 404
        plan = self._plan_of_meso(meso)
        auth_err, auth_status = self._authorize_coach_for_plan(coach, plan)
        if auth_err:
            return None, auth_err, auth_status
        rows = list(
            self.db.scalars(
                select(CycleSystemAnalysis)
                .where(CycleSystemAnalysis.mesocycle_id == meso.id)
                .order_by(
                    CycleSystemAnalysis.generated_at.desc(), CycleSystemAnalysis.id.desc()
                )
            ).all()
        )
        if all_rows:
            return {
                "system_analyses": [self._analysis_to_dict(r) for r in rows],
                "count": len(rows),
            }, None, 200
        latest = rows[0] if rows else None
        return {
            "system_analysis": self._analysis_to_dict(latest) if latest else None
        }, None, 200

    def create_coach_review(
        self, coach: User, mesocycle_id: int, payload: CoachReviewCreateRequest
    ) -> tuple[dict | None, str | None, int]:
        meso = self._load_mesocycle(mesocycle_id)
        if not meso:
            return None, "Mesocycle not found", 404
        plan = self._plan_of_meso(meso)
        auth_err, auth_status = self._authorize_coach_for_plan(coach, plan)
        if auth_err:
            return None, auth_err, auth_status
        existing_draft = self.db.scalar(
            select(CycleCoachReview).where(
                CycleCoachReview.mesocycle_id == meso.id,
                CycleCoachReview.status == CoachReviewStatus.draft,
                CycleCoachReview.superseded_by_id.is_(None),
            )
        )
        if existing_draft:
            return None, "A draft review already exists for this cycle", 409
        content = payload.content
        source_id = payload.source_analysis_id
        if source_id is not None and not content:
            analysis = self.db.get(CycleSystemAnalysis, source_id)
            if not analysis or analysis.mesocycle_id != meso.id:
                return None, "System analysis not found", 404
            content = analysis.summary
        if not content:
            return None, "content is required", 400
        max_version = self.db.scalar(
            select(CycleCoachReview.version)
            .where(CycleCoachReview.mesocycle_id == meso.id)
            .order_by(CycleCoachReview.version.desc())
        ) or 0
        review = CycleCoachReview(
            mesocycle_id=meso.id,
            coach_id=coach.id,
            source_analysis_id=source_id,
            status=CoachReviewStatus.draft,
            content=content,
            next_cycle_focus=payload.next_cycle_focus,
            version=max_version + 1,
        )
        self.db.add(review)
        self.db.flush()
        self._log(
            plan, ChangeLogEntityType.coach_review, review.id, "create",
            LockState.current, coach, PlanOperation.metadata,
            after={"version": review.version}, reason=payload.reason,
        )
        self.db.commit()
        return {"coach_review": self._review_to_dict(review)}, None, 201

    def update_coach_review(
        self, coach: User, review_id: int, payload: CoachReviewUpdateRequest
    ) -> tuple[dict | None, str | None, int]:
        review = self.db.get(CycleCoachReview, review_id)
        if not review:
            return None, "Coach review not found", 404
        meso = self._load_mesocycle(review.mesocycle_id)
        plan = self._plan_of_meso(meso)
        auth_err, auth_status = self._authorize_coach_for_plan(coach, plan)
        if auth_err:
            return None, auth_err, auth_status
        if review.status == CoachReviewStatus.approved:
            return None, "Approved reviews cannot be edited; create a new version", 409
        before, after = diff_fields(
            review, payload.model_dump(exclude_unset=True, exclude={"reason", "strict"})
        )
        if payload.content is not None:
            review.content = payload.content
        if "next_cycle_focus" in payload.model_fields_set:
            review.next_cycle_focus = payload.next_cycle_focus
        self._log(
            plan, ChangeLogEntityType.coach_review, review.id, "update",
            LockState.current, coach, PlanOperation.metadata,
            before=before, after=after, reason=payload.reason,
        )
        self.db.commit()
        return {"coach_review": self._review_to_dict(review)}, None, 200

    def new_coach_review_version(
        self, coach: User, review_id: int
    ) -> tuple[dict | None, str | None, int]:
        review = self.db.get(CycleCoachReview, review_id)
        if not review:
            return None, "Coach review not found", 404
        if review.status != CoachReviewStatus.approved:
            return None, "Only an approved review can start a new version", 400
        meso = self._load_mesocycle(review.mesocycle_id)
        plan = self._plan_of_meso(meso)
        auth_err, auth_status = self._authorize_coach_for_plan(coach, plan)
        if auth_err:
            return None, auth_err, auth_status
        existing_draft = self.db.scalar(
            select(CycleCoachReview).where(
                CycleCoachReview.mesocycle_id == review.mesocycle_id,
                CycleCoachReview.status == CoachReviewStatus.draft,
                CycleCoachReview.superseded_by_id.is_(None),
            )
        )
        if existing_draft:
            return None, "A draft review already exists for this cycle", 409
        successor = CycleCoachReview(
            mesocycle_id=review.mesocycle_id,
            coach_id=coach.id,
            source_analysis_id=review.source_analysis_id,
            status=CoachReviewStatus.draft,
            content=review.content,
            next_cycle_focus=review.next_cycle_focus,
            version=review.version + 1,
        )
        self.db.add(successor)
        self.db.flush()
        self._log(
            plan, ChangeLogEntityType.coach_review, successor.id, "create",
            LockState.current, coach, PlanOperation.metadata,
            after={"version": successor.version, "from_review_id": review.id},
        )
        self.db.commit()
        return {"coach_review": self._review_to_dict(successor)}, None, 201

    def approve_coach_review(
        self, coach: User, review_id: int
    ) -> tuple[dict | None, str | None, int]:
        review = self.db.get(CycleCoachReview, review_id)
        if not review:
            return None, "Coach review not found", 404
        meso = self._load_mesocycle(review.mesocycle_id)
        plan = self._plan_of_meso(meso)
        auth_err, auth_status = self._authorize_coach_for_plan(coach, plan)
        if auth_err:
            return None, auth_err, auth_status
        if review.status == CoachReviewStatus.approved:
            return None, "Review is already approved", 409
        previous = self.db.scalar(
            select(CycleCoachReview).where(
                CycleCoachReview.mesocycle_id == review.mesocycle_id,
                CycleCoachReview.status == CoachReviewStatus.approved,
                CycleCoachReview.superseded_by_id.is_(None),
                CycleCoachReview.id != review.id,
            )
        )
        review.status = CoachReviewStatus.approved
        review.approved_at = datetime.utcnow()
        review.approved_by_id = coach.id
        if previous:
            previous.superseded_by_id = review.id
        self._log(
            plan, ChangeLogEntityType.coach_review, review.id, "review_approve",
            LockState.current, coach, PlanOperation.metadata,
            after={"status": "approved"},
        )
        self.db.commit()
        return {"coach_review": self._review_to_dict(review)}, None, 200

    def get_coach_review(
        self, coach: User, mesocycle_id: int, history: bool = False
    ) -> tuple[dict | None, str | None, int]:
        meso = self._load_mesocycle(mesocycle_id)
        if not meso:
            return None, "Mesocycle not found", 404
        plan = self._plan_of_meso(meso)
        auth_err, auth_status = self._authorize_coach_for_plan(coach, plan)
        if auth_err:
            return None, auth_err, auth_status
        rows = list(
            self.db.scalars(
                select(CycleCoachReview)
                .where(CycleCoachReview.mesocycle_id == meso.id)
                .order_by(CycleCoachReview.version.desc())
            ).all()
        )
        if history:
            return {
                "coach_reviews": [self._review_to_dict(r) for r in rows],
                "count": len(rows),
            }, None, 200
        current = next((r for r in rows if r.superseded_by_id is None), None)
        return {
            "coach_review": self._review_to_dict(current) if current else None
        }, None, 200

    def list_my_plans(self, athlete: User) -> tuple[dict | None, str | None, int]:
        plans = self.db.scalars(
            select(TrainingPlan)
            .where(TrainingPlan.athlete_id == athlete.id)
            .order_by(TrainingPlan.start_date.desc())
        ).all()
        loaded = [self._load_plan(p.id, "items") for p in plans]
        return {
            "plans": [self._plan_to_dict_for_athlete(p) for p in loaded],
            "count": len(loaded),
        }, None, 200

    def get_my_plan(
        self, athlete: User, plan_id: int
    ) -> tuple[dict | None, str | None, int]:
        plan = self._load_plan(plan_id, "items")
        if not plan or plan.athlete_id != athlete.id:
            return None, "Training plan not found", 404
        return {"plan": self._plan_to_dict_for_athlete(plan)}, None, 200

    def get_my_position(self, athlete: User) -> tuple[dict | None, str | None, int]:
        plans = list(
            self.db.scalars(
                select(TrainingPlan)
                .options(
                    selectinload(TrainingPlan.mesocycles)
                    .selectinload(Mesocycle.microcycles)
                    .selectinload(Microcycle.items)
                )
                .where(
                    TrainingPlan.athlete_id == athlete.id,
                    TrainingPlan.status.in_(
                        [TrainingPlanStatus.active, TrainingPlanStatus.draft]
                    ),
                )
                .order_by(TrainingPlan.start_date.asc())
            ).all()
        )
        current_plan = None
        today = None
        for plan in plans:
            today = self._today(plan, None)
            if plan.start_date <= today <= plan.end_date:
                current_plan = plan
                break
        if current_plan is None:
            return {
                "plan": None,
                "mesocycle": None,
                "microcycle": None,
                "upcoming_items": [],
                "coach_review": None,
            }, None, 200
        today = self._today(current_plan, None)
        current_meso = next(
            (m for m in current_plan.mesocycles if m.start_date <= today <= m.end_date),
            None,
        )
        current_micro = None
        if current_meso:
            current_micro = next(
                (m for m in current_meso.microcycles if m.start_date <= today <= m.end_date),
                None,
            )
        upcoming = []
        if current_micro:
            for i in current_micro.items:
                placement = _resolve_placement(i, current_micro)
                resolved = placement.get("resolved_date") if placement else None
                if resolved is None or date.fromisoformat(resolved) >= today:
                    upcoming.append(self._item_to_dict(i))
            for item in upcoming:
                item.pop("converted_at", None)
                item.pop("converted_by_id", None)
        review = None
        if current_meso:
            review = self._approved_reviews_for_plan(current_plan.id).get(current_meso.id)
        return {
            "plan": {
                "id": current_plan.id,
                "name": current_plan.name,
                "goal": current_plan.goal,
                "start_date": _iso(current_plan.start_date),
                "end_date": _iso(current_plan.end_date),
                "status": current_plan.status.value,
            },
            "mesocycle": (
                {
                    "id": current_meso.id,
                    "name": current_meso.name,
                    "intent": current_meso.intent,
                    "start_date": _iso(current_meso.start_date),
                    "end_date": _iso(current_meso.end_date),
                }
                if current_meso
                else None
            ),
            "microcycle": (
                {
                    "id": current_micro.id,
                    "name": current_micro.name,
                    "intent": current_micro.intent,
                    "ordinal": current_micro.ordinal,
                    "start_date": _iso(current_micro.start_date),
                    "end_date": _iso(current_micro.end_date),
                }
                if current_micro
                else None
            ),
            "upcoming_items": upcoming,
            "coach_review": review,
        }, None, 200

    def get_cycle_bands(
        self, coach: User, athlete_id: int, start_date: date, end_date: date
    ) -> tuple[dict | None, str | None, int]:
        relation_err = coach_athlete_relation_error(self.db, coach.id, athlete_id)
        if relation_err:
            return None, relation_err, COACH_ATHLETE_NOT_LINKED_STATUS
        if start_date > end_date:
            return None, "start_date must be before or equal to end_date", 400
        return cycle_bands(self.db, athlete_id, start_date, end_date), None, 200







