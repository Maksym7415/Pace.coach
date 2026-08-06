"""Resolve authored workout steps into a tree + flattened occurrence list."""
from __future__ import annotations

from typing import Any

from src.modules.execution.domain import (
    ResolvedOccurrence,
    ResolvedPlan,
    ResolvedPlanNode,
    ResolvedStepTarget,
)
from src.modules.training.workout_steps import (
    DurationType,
    RepeatBlockModel,
    StepType,
    TargetType,
    WorkoutStepModel,
    _infer_duration_type,
    ensure_step_ids,
    parse_step_item,
)


def _target_from_step(step: WorkoutStepModel) -> ResolvedStepTarget:
    target_type = step.target_type
    if target_type == TargetType.none:
        target_type = None
    return ResolvedStepTarget(
        target_type=target_type,
        target_min=step.target_min,
        target_max=step.target_max,
        target_zone_id=step.target_zone_id,
        target_zone_name=step.target_zone_name,
    )


def _occurrence_from_step(
    step: WorkoutStepModel,
    *,
    occurrence_path: str,
    occurrence_ordinal: int,
) -> ResolvedOccurrence:
    if not step.id:
        raise ValueError("Resolved steps require a stable id")
    duration_type = _infer_duration_type(step)
    return ResolvedOccurrence(
        authored_step_id=step.id,
        occurrence_path=occurrence_path,
        occurrence_ordinal=occurrence_ordinal,
        step_type=step.type,
        duration_type=duration_type,
        duration_min=step.duration if duration_type == DurationType.time else None,
        distance_m=step.distance if duration_type == DurationType.distance else None,
        target=_target_from_step(step),
        notes=step.notes,
        template_step_id=step.template_step_id,
    )


def _expand_items(
    items: list[Any],
    *,
    path_prefix: str,
    ordinal_counter: list[int],
) -> tuple[list[ResolvedPlanNode], list[ResolvedOccurrence]]:
    """Expand steps/repeats into a tree and flat occurrences.

    Supports nested repeats structurally even though authoring currently rejects them.
    """
    tree: list[ResolvedPlanNode] = []
    occurrences: list[ResolvedOccurrence] = []

    for index, raw in enumerate(items):
        item = (
            raw
            if isinstance(raw, (WorkoutStepModel, RepeatBlockModel))
            else parse_step_item(raw)
        )
        node_path = f"{path_prefix}/{index}" if path_prefix else str(index)

        if isinstance(item, RepeatBlockModel):
            block_id = item.id or f"repeat-{node_path}"
            child_nodes: list[ResolvedPlanNode] = []
            for rep in range(item.repeat_count):
                rep_path = f"{node_path}/r{rep}"
                # Nested structure: each repetition is a virtual group of child steps
                for child_index, child_step in enumerate(item.steps):
                    child_path = f"{rep_path}/{child_index}"
                    ordinal_counter[0] += 1
                    occurrence = _occurrence_from_step(
                        child_step,
                        occurrence_path=child_path,
                        occurrence_ordinal=ordinal_counter[0],
                    )
                    occurrences.append(occurrence)
                    child_nodes.append(
                        ResolvedPlanNode(
                            kind="step",
                            id=child_step.id or child_path,
                            step=occurrence,
                        )
                    )
            tree.append(
                ResolvedPlanNode(
                    kind="repeat",
                    id=block_id,
                    repeat_count=item.repeat_count,
                    children=child_nodes,
                )
            )
        else:
            ordinal_counter[0] += 1
            occurrence = _occurrence_from_step(
                item,
                occurrence_path=node_path,
                occurrence_ordinal=ordinal_counter[0],
            )
            occurrences.append(occurrence)
            tree.append(
                ResolvedPlanNode(
                    kind="step",
                    id=item.id or node_path,
                    step=occurrence,
                )
            )

    return tree, occurrences


def resolve_plan(
    steps: list[Any] | None,
    *,
    workout_id: int | None = None,
    sport_code: str | None = None,
) -> ResolvedPlan:
    """Build a ResolvedPlan from authored workout steps JSON."""
    if not steps:
        return ResolvedPlan(workout_id=workout_id, sport_code=sport_code)

    ensured = ensure_step_ids(list(steps))
    tree, occurrences = _expand_items(ensured, path_prefix="", ordinal_counter=[0])
    return ResolvedPlan(
        workout_id=workout_id,
        sport_code=sport_code,
        tree=tree,
        occurrences=occurrences,
    )
