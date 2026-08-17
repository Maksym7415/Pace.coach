# Execution Architecture

> Technical reference for the structured workout execution system: how a FIT file becomes a
> step-by-step comparison of planned versus actual training.
>
> Last verified against code: **2026-08-17** (M0 landed).
> Product context: [`product-roadmap.md`](./product-roadmap.md).

Audience: an engineer or AI agent who needs to modify this system without reverse-engineering
the repository. All type and function names below are real identifiers from the codebase.

Module root: `backend/src/modules/execution/`.

---

## 1. Data flow

```
POST /api/activities/import/fit                    activity_import/router.py
  │
  ├─ StoredFile (SHA-256 key)  +  ActivityImport(status="pending")
  │     LocalFilesystemStorage (dev) or SupabaseStorage (production)
  │
  └─ BackgroundTasks → _process_import              activity_import/service.py
       │
       ├─ FitParser.parse(bytes) → NormalizedActivity        fit_parser/parser.py
       │     meta / laps / track_points / device_workout / events / developer_fields
       │
       ├─ _persist_activity
       │     Activity                     (gear_track/models.py)
       │     ActivityLap[]                (activity_import/models.py)
       │     ActivityTrackPoint[]         one row per FIT record, ~1 Hz
       │     ActivitySource.raw_metadata  device_workout + events + dev fields as JSON
       │
       ├─ try_link_activity_to_workout()             training/activity_link.py
       │     └─ sets workout.activity_id, status=completed, completed_at
       │        (exactly one eligible same-day candidate after sport_id filter)
       │
       └─ if linked is not None and linked.steps:
             ExecutionMatchingService(db).match_from_normalized(...)
                                                     execution/service.py

POST /api/training/workouts/{id}/link-activity     training/router.py
  └─ rematch_workout_activity() → match_persisted()

POST /api/activities/{id}/workout-execution/rematch  execution/router.py
  └─ rematch_workout_activity() → match_persisted()
```

Then, on read:

```
GET /api/activities/{activity_id}/workout-execution   execution/router.py
  → WorkoutExecutionService.get_for_activity
  → serialize_workout_execution(execution)
  → PlannedVsActual.tsx  /  WorkoutReviewDrawer.tsx
```

### Matching triggers

`ExecutionMatchingService` is invoked from three places:

1. **FIT import auto-link** — `activity_import/service.py` calls `match_from_normalized` when
   `try_link_activity_to_workout` returns a workout that has `steps`. Auto-link still requires
   exactly one eligible same-day candidate (sport-filtered; never guesses).
2. **Manual link** — `POST /api/training/workouts/{id}/link-activity` calls
   `rematch_workout_activity` → `match_persisted`.
3. **Re-match** — `POST /api/activities/{id}/workout-execution/rematch` uses the same helper.

`rematch_workout_activity` refuses to persist an unmatched row when the activity has no
`start_time` or no laps/streams (422). `_run` still only flushes; the helper commits.

Consequences that remain:

- Strava's webhook and manual activity creation both call `try_link_activity_to_workout` but
  **never** call `ExecutionMatchingService`. Re-match on those activities returns 422.
- Matching errors inside the FIT import job are still wrapped in `try/except Exception` with
  `logger.exception`, so import still reports success. Manual rematch surfaces the error.

---

## 2. Matching architecture

`ExecutionMatchingService._run(workout_id, activity_id, evidence)` — `execution/service.py`.

| # | Stage | Function |
|---|---|---|
| 1 | Load workout | `db.get(Workout, workout_id)` |
| 2 | Resolve plan | `JsonWorkoutPlanSource.load()` → `resolve_plan()` |
| 3 | Snapshot plan | `_create_snapshot()` → `WorkoutPlanSnapshot` |
| 4 | Idempotent delete | remove prior `WorkoutExecution` with same `(workout_id, activity_id, algorithm_version)` |
| 5 | Correlate structurally | `correlate_structurally(plan, evidence.device_plan)` |
| 6 | Select strategy | `default_registry().select(evidence)` |
| 7 | Segment | `strategy.segment(evidence, plan, correlation)` → `list[SegmentMatch]` |
| 8 | Extract metrics | `get_metric_extractor(plan.sport_code).extract(...)` per matched window |
| 9 | Score | `score_occurrence(occurrence, metrics, evidence)` |
| 10 | Detect issues | `detect_issues(match, metrics, score)` |
| 11 | Roll up status | `_rollup_status(matches)` |
| 12 | Persist | `WorkoutExecution` + `WorkoutStepExecution[]` + `ExecutionIssue[]` |

`ALGORITHM_VERSION = "1.0.0"` (`execution/enums.py`). Changing it produces a new execution row
rather than overwriting the old one, so results are reproducible per version.

### Evidence adaptation

Matching never reads the database directly. It consumes `ActivityEvidence`
(`execution/domain.py`) — a vendor-neutral value object:

| Field | Meaning |
|---|---|
| `segments: list[EvidenceSegment]` | laps, each with `device_step_index`, `lap_trigger`, `intensity`, times |
| `timeline: list[TrackPoint]` | per-record stream |
| `markers: list[FitEvent]` | FIT events |
| `device_plan: DeviceWorkout \| None` | the workout embedded in the FIT file |
| `capabilities: set[EvidenceCapability]` | what this evidence can support |

Two producers, both in `execution/adapters/garmin.py`:

- `GarminEvidenceAdapter.adapt(normalized)` — the import path, from parser output.
- `activity_evidence_from_persisted(...)` — the recompute path, from DB rows (used by
  `_load_evidence` via `match_persisted`, which `rematch_workout_activity` wraps).

`EvidenceCapability` values: `device_step_index`, `device_plan`, `lap_structure`, `timeline`,
`heart_rate`, `pace`, `power`, `cadence`.

> The `vendor` argument is currently cosmetic — both branches construct
> `GarminEvidenceAdapter()`.

### Structural correlation

`correlate_structurally(plan, device_plan)` — `execution/correlation.py` — aligns authored
steps to the device-embedded workout steps by positional walk, producing
`PlanCorrelationResult`:

- `mapping: dict[authored_step_id, device_message_index]`
- `confidence: float` — `(compatible / pairs)` minus a `0.2` penalty when step counts differ
- `divergences: list[dict]`
- `trusted_by_id: bool` — **always `False`** today

Compatibility is checked on two axes:

- `_intensity_compatible` — `warmup`→`warmup`, `cooldown`→`cooldown`,
  `run`/`ride`/`interval`→`active`/`interval`, `recovery`/`recovery_ride`/`rest`→`rest`/`recovery`
- `_duration_compatible` — `time`→`time`/`open`, `distance`→`distance`/`open`,
  `lap_button`→`open`/`lap_button`

Device repeat wrappers are filtered out by `_device_leaf_steps` before comparison. Correlation
deduplicates to *unique* `authored_step_id`; per-occurrence alignment is the segmentation
layer's job.

---

## 3. Plan resolution

`resolve_plan(workout_id, sport_code, steps)` — `execution/plan_resolution.py` — converts the
authored `workouts.steps` JSON into `ResolvedPlan`:

```python
class ResolvedPlan(BaseModel):
    workout_id: int | None
    sport_code: str | None
    tree: list[ResolvedPlanNode]          # structure, supports nesting
    occurrences: list[ResolvedOccurrence] # flat, one per concrete execution
```

`_expand_items` performs the expansion (there is no function named `flatten`). Each repeat
iteration produces a distinct `ResolvedOccurrence`:

```python
class ResolvedOccurrence(BaseModel):
    authored_step_id: str      # stable UUID from the authored step
    occurrence_path: str       # e.g. "1/r2/0"  → item 1, repeat cycle 2, child 0
    occurrence_ordinal: int    # 1-based, monotonic across the whole workout
    step_type: StepType
    duration_type: DurationType
    duration_min: int | None
    distance_m: int | None
    target: ResolvedStepTarget
    notes: str | None
    template_step_id: str | None
```

So `4 × (interval + recovery)` yields 8 occurrences sharing 2 `authored_step_id` values,
distinguished by `occurrence_ordinal`.

**Nesting:** `_expand_items` handles nested repeats recursively, but the authoring validator
makes them unreachable — `RepeatBlockModel.steps` is typed `list[WorkoutStepModel]`
(`training/workout_steps.py`), so a repeat can never contain a repeat. The resolver capability
is latent.

### Plan snapshot

`WorkoutPlanSnapshot.resolved_plan` stores `ResolvedPlan.model_dump(mode="json")`.

**Snapshots are created at match time, not at assignment time** — `_create_snapshot` runs
inside `_run` and reads whatever `workout.steps` says at that moment. The practical protection
against a coach editing history comes from a different rule: workouts are only editable while
`status == scheduled` (`training/service.py`). A re-match produces a fresh snapshot from the
then-current plan.

`plan_source.py` defines the `PlanSource` seam. Only `JsonWorkoutPlanSource` exists; a
relational implementation is reserved by comment.

---

## 4. Segmentation strategies

A strategy answers one question: **which time window corresponds to each planned occurrence?**

Interface — `execution/segmentation/base.py`:

```python
class SegmentationStrategy(ABC):
    strategy_id: str
    required_capabilities: set[EvidenceCapability]

    def supports(self, evidence) -> bool:
        return self.required_capabilities.issubset(evidence.capabilities)

    def segment(self, evidence, plan, correlation) -> list[SegmentMatch]: ...
```

`SegmentationRegistry.select()` returns the **first** strategy whose `supports()` is true, so
list order is priority order. `default_registry()` in `execution/service.py`:

| Priority | `strategy_id` | Requires | Behaviour |
|---|---|---|---|
| 1 | `device_step_index` | `device_step_index` | Groups consecutive laps sharing a FIT `wkt_step_index` via `_group_consecutive_index_runs` (merges auto-laps, counts repeat cycles). Uses `correlation.mapping` to skip ahead when planned work was not performed. Highest fidelity. |
| 2 | `lap_structure` | `lap_structure` | Positional 1:1 lap → occurrence mapping. Count mismatch is tolerated with reduced confidence. |
| 3 | `signal` | `timeline` | Walks the trackpoint timeline accumulating planned time or distance. Sets `details["approximate"] = True`. |
| — | `manual` | (needs boundaries) | Exact windows from supplied `ManualBoundary` list. **Implemented but not registered** — no UI produces boundaries yet. |

Each strategy returns one `SegmentMatch` per occurrence:

```python
class SegmentMatch(BaseModel):
    window: ExecutionWindow | None     # None when nothing was matched
    evidence: MatchEvidence           # why we believe this
    status: StepExecutionStatus
    occurrence: ResolvedOccurrence
```

`MatchEvidence` is deliberately structured, not prose: `strategy_id`, `capabilities_used`,
`device_step_index`, `repeat_cycle_run`, `prior_runs_of_same_index`, `lap_ids`,
`lap_message_indexes`, `lap_triggers`, `trackpoint_index_start/end`, `plan_correlation`,
`rejected_candidates`, `capability_gaps`, `negative_claim`, `details`. It is persisted verbatim
and is the audit trail for every downstream claim.

**Statuses actually emitted by strategies:** `executed`, `not_executed`, `not_attempted`,
`unmatched`. The enum also defines `partially_executed` and `substituted`; no strategy produces
them, though `_rollup_status` and `detect_issues` handle them.

---

## 5. Metrics extraction

`get_metric_extractor(sport_code)` — `execution/metrics/extractor.py`. Returns
`CyclingMetricExtractor` for `"cycling"`, otherwise `RunningMetricExtractor` (this is the
fallback for every other sport, including `None`).

**All metrics come from the trackpoint timeline sliced by the window** (`_points_in_window`),
not from lap aggregates. Laps determine boundaries; streams determine values.

Typed fields on `ExecutionMetrics`:

| Field | Derivation |
|---|---|
| `duration_elapsed_s` | `window.ended_at - window.started_at` |
| `duration_moving_s` | `_moving_time_s` — sums inter-point deltas, skipping samples where speed `< 0.5 km/h` |
| `distance_m` | `max(distance) - min(distance)` over the window |
| `target_metric` | the occurrence's `target_type` value |
| `time_in_target_pct` | share of samples inside `ordered_target_bounds(target_min, target_max)` |
| `target_deviation_pct` | signed `(avg - mid_target) / abs(mid_target) * 100` |

Free-form `metrics` dict keys (running): `avg_pace_s_per_km`, `avg_hr_bpm`, `avg_power_w`,
`avg_cadence`, `first_half_pace_s_per_km`, `second_half_pace_s_per_km`, `pace_variability`,
`hr_drift_pct`, `avg_ground_contact_time_ms`, `avg_vertical_oscillation_mm`.
`CyclingMetricExtractor` delegates to the running extractor and pops
`avg_ground_contact_time_ms`, `avg_vertical_oscillation_mm`, `vertical_ratio`.

Two subtleties worth preserving:

- **Pace sign convention.** Pace is normalized to seconds per km, so a *larger* value is
  *slower*. `ordered_target_bounds` exists because coaches author pace ranges slow→fast
  (`6:00–5:15`), which stores `target_min > target_max`; it sorts for comparison without
  rewriting the authored display order.
- `metrics/catalog.py` documents metric keys for cycling, swimming and strength that **no
  extractor computes**. It is a naming registry, not a capability list.

---

## 6. Scoring

`score_occurrence(occurrence, metrics, evidence)` — `execution/scoring.py`. Three independently
nullable dimensions, averaged over whatever is non-null
(`components["weights"] == "equal_non_null"`).

**Completion** — `_completion_score`:

| `duration_type` | Rule |
|---|---|
| `lap_button` | `100` if elapsed `> 5 s` or distance `> 10 m`, else `0` |
| `time` | `clamp(moving_s / (duration_min × 60) × 100)` |
| `distance` | `clamp(distance_m / planned_m × 100)` |

**Intensity adherence** — `_intensity_score`. Base is `time_in_target_pct`, then an
intent-asymmetric penalty derived from `target_deviation_pct`. `too_hard` is
`deviation < 0` for pace and `deviation > 0` otherwise; `too_easy` requires
`abs(deviation) > 2.0`.

| Intent group | Members | Too hard | Too easy |
|---|---|---|---|
| `_RECOVERY_INTENTS` | `recovery`, `recovery_ride`, `rest`, `warmup`, `cooldown` | penalty `min(60, abs(dev) × 2.0)` | floor at `90` — going easier is fine |
| `_WORK_INTENTS` | `interval`, `run`, `ride` | mild penalty `min(25, abs(dev) × 0.8)` | penalty `min(70, abs(dev) × 2.5)` |

This asymmetry is the core coaching opinion encoded in the system: an easy run done too hard is
a real error, and an easy run done easier is not.

**Execution quality** — `_quality_score`. **Suppressed entirely** (returns `None`) when
`evidence.strategy_id == "signal"` or `evidence.details["approximate"]` is set, because you
cannot make fine-grained pacing claims from approximate boundaries. Otherwise averages:

- pace variability → `100 - variability × 300`
- fade (work intents only) → `100 - max(0, fade) × 400`, where `fade = (second - first) / first`
- HR drift → `100 - max(0, drift - 5) × 3`

Results land in `WorkoutStepExecution.score` and `score_components`. There is **no
execution-level score**; `overall_confidence` is the mean of window confidences, which measures
match certainty, not performance.

---

## 7. Issue detection

`detect_issues(match, metrics, score)` — `execution/issues.py`. Returns
`list[ExecutionIssueDraft]`. Status-derived issues are emitted first; if `metrics` or
`match.window` is `None` the function returns early.

| Code | Severity | Dimension | Rule |
|---|---|---|---|
| `step_not_executed` | `warning` | `matching` | `status == not_executed` |
| `step_not_attempted` | `info` | `matching` | `status == not_attempted` |
| `step_unmatched` | `warning` | `matching` | `status == unmatched` |
| `step_substituted` | `warning` | `structure` | `status == substituted` (unreachable — no strategy emits it) |
| `incomplete_duration_or_distance` | `warning`, or `critical` if `< 50` | `completion` | `score.completion < 80` |
| `below_target_adherence` | `warning`, or `critical` if `< 25` | `intensity` | `time_in_target_pct < 50` |
| `recovery_too_hard` | `warning` | `intensity` | step is `recovery`/`recovery_ride`/`rest` and deviation `< -5` (pace) or `> 5` (other) |
| `inconsistent_pacing` | `info` | `quality` | `pace_variability > 0.08` and `strategy_id != "signal"` |

`IssueSeverity`: `info`, `warning`, `critical`. `IssueDimension`: `completion`, `intensity`,
`quality`, `matching`, `structure`.

Each issue carries a `payload` JSON with the numbers that triggered it, so the UI never has to
recompute a justification.

### insights.py — implemented but unreachable

`build_insights(matches, issues)` converts issues into confidence-gated `InsightClaim` objects,
suppressing quality claims when boundaries are approximate or confidence `< 0.6`, and intensity
claims when confidence `< 0.5` or the evidence is a `negative_claim`. `get_insights` on
`ExecutionMatchingService` calls it. **No router exposes either.** The whole layer is dormant.

---

## 8. Persistence

| Table | Model | Key constraint |
|---|---|---|
| `workout_plan_snapshots` | `WorkoutPlanSnapshot` | — |
| `workout_executions` | `WorkoutExecution` | unique `(workout_id, activity_id, algorithm_version)` |
| `workout_step_executions` | `WorkoutStepExecution` | unique `(workout_execution_id, authored_step_id, occurrence_ordinal)` |
| `execution_issues` | `ExecutionIssue` | indexed on `workout_execution_id`, `authored_step_id`, `code` |

All in `execution/models.py`, all cascade-deleted from `WorkoutExecution`.

`WorkoutExecutionStatus` is rolled up by `_rollup_status`: `matched` when every match is
`executed`, `unmatched` when all are `unmatched` or there are no matches, otherwise `partial`.
The enum also defines `pending` and `failed`; neither is ever assigned.

`workout_executions.extra_work` (JSON) exists in the schema and is never written.

---

## 9. API consumed by Planned vs Actual / Workout Review

Both routes are in `execution/router.py`.

### `GET /api/activities/{activity_id}/workout-execution`

Authorization: the requesting user owns the activity, **or** has an active
`CoachAthleteRelation` with its owner (`_can_access_activity`).

Returns the **most recent** execution for the activity (`ORDER BY created_at DESC, id DESC
LIMIT 1`), or `{"workout_execution": null}` when none exists — a `200`, not a `404`.

`serialize_workout_execution()` is where planned and actual are joined. It:

1. Rehydrates `ResolvedPlan` from `plan_snapshot.resolved_plan`.
2. Indexes occurrences by `(authored_step_id, occurrence_ordinal)`.
3. Groups issues by the same key.
4. Sorts step rows by `(occurrence_ordinal, authored_step_id)`.
5. Emits one `StepExecutionOut` per step, carrying `planned` (from the snapshot) alongside the
   actuals, with issues nested underneath.

```
WorkoutExecutionOut
  id, workout_id, activity_id, status, overall_confidence, algorithm_version
  issue_count, responded_issue_count
  workout: WorkoutStubOut { id, title, sport_code, scheduled_date }
  step_executions: [ StepExecutionOut
      authored_step_id, occurrence_path, occurrence_ordinal, status
      planned: PlannedStepOut { step_type, duration_type, duration_min, distance_m,
                                target_type, target_min, target_max,
                                target_zone_name, notes }
      duration_moving_s, distance_m, target_metric,
      time_in_target_pct, target_deviation_pct, score
      issues: [ ExecutionIssueOut { id, code, severity, dimension,
                                    athlete_response { reason, reason_other,
                                                       notes, responded_at } } ]
  ]
```

**The planned side always comes from the snapshot, never from the live workout.** This is what
makes the comparison stable.

### `POST /api/activities/{activity_id}/workout-execution/athlete-responses`

Athlete-only (`activity.user_id != user_id` → `403`; a coach cannot answer on an athlete's
behalf). Body is `SaveAthleteResponsesIn` — a list of `{issue_id, reason, reason_other, notes}`.

Behaviour: validates every `issue_id` belongs to this execution, then writes `athlete_id`,
`athlete_reason`, `athlete_reason_other`, `athlete_notes`, `athlete_responded_at` onto the issue
rows. `reason_other` is discarded unless `reason == "Other"`. Responses are **overwritten**, not
appended — there is no history and no coach reply.

Frontend consumers: `frontend/src/modules/execution/` — `PlannedVsActual.tsx`,
`WorkoutReviewDrawer.tsx`, `api.ts`, with presentation logic in `questions.ts`, `labels.ts`,
`severity.ts`, `stepStatus.ts`.

---

## 10. Current limitations

| # | Limitation | Detail |
|---|---|---|
| 1 | Strava and manual activity creation still do not match | They call `try_link_activity_to_workout` but never `ExecutionMatchingService`. Re-match on those activities returns 422 (no laps/streams). |
| 2 | Auto-link still refuses to guess | Exactly one eligible same-day `scheduled` workout after sport_id filter. Two same-sport sessions on one day remain unlinked until `POST .../link-activity`. |
| 3 | Manual link UI is API-first | Endpoints exist; athlete/coach pickers are not wired. |
| 4 | Matching still in-process | FIT import uses FastAPI `BackgroundTasks`. A real job runner is an M3 prerequisite. |
| 5 | Snapshot timing | Created at match time from the live plan, not at assignment. |
| 6 | Nested repeats blocked at authoring | Resolver supports them; `RepeatBlockModel` prevents them. |
| 7 | Sport coverage | Running is first-class. Cycling reuses the running extractor minus running-dynamics keys, with no dedicated tests. Swimming and strength appear only as catalog key names. Unknown sports silently fall back to the running extractor. |
| 8 | Elevation ignored | `altitude` is loaded into the timeline and never used by any extractor or score. |
| 9 | Session score is derived on read | `aggregate_execution_score` means non-null step scores. There is still no stored session-level metrics blob. `overall_confidence` measures match certainty, not performance. |
| 10 | `insights.py` unreachable | No route exposes `get_insights`. |
| 11 | `ManualStrategy` unregistered | Absent from `default_registry()`. |
| 12 | Dead enum values | `WorkoutExecutionStatus.pending`/`.failed`, `StepExecutionStatus.partially_executed`/`.substituted`. |
| 13 | Silent failure on import | Matching errors are caught and logged inside the import job; the import still reports success. Manual rematch surfaces the error. |
| 14 | No FIT-import end-to-end test | Persistence tests cover link, rematch, auto-link, and score aggregation. The import hook itself is not covered. Two matching tests depend on a machine-specific FIT path and skip when absent. |

---

## 11. Invariants

Violating any of these breaks the system in ways that are hard to detect. Preserve them.

1. **Authored step IDs are stable and permanent.** `ensure_step_ids()`
   (`training/workout_steps.py`) mints a UUID per step and repeat block and preserves existing
   ones across edits. Migration `w0e1f2a3b4c5` backfilled historical rows. Every execution row,
   issue, and snapshot occurrence keys off `authored_step_id`. Never regenerate an ID for a step
   that already has one.

2. **`(authored_step_id, occurrence_ordinal)` is the identity of a planned execution.** It is
   the join key between snapshot occurrences, step execution rows, and issues, and it is
   enforced by a unique constraint. `authored_step_id` alone is not unique within a workout —
   repeats reuse it.

3. **`occurrence_ordinal` is 1-based and monotonic** across the fully expanded plan.
   `occurrence_path` (`"1/r2/0"`) is for display and debugging, not for joins.

4. **The planned side is always read from the snapshot.** Never re-read `workout.steps` when
   rendering or scoring an existing execution.

5. **Executions are versioned, not mutated.** `(workout_id, activity_id, algorithm_version)` is
   unique, and `_run` deletes the same-version row before inserting. Bump `ALGORITHM_VERSION`
   when scoring or detection semantics change; do not silently overwrite history.

6. **Matching reads `ActivityEvidence`, never the ORM.** Keep the adapter boundary intact so
   new vendors and the recompute path stay interchangeable.

7. **Claims must be gated by evidence quality.** Approximate boundaries (`signal` strategy or
   `details["approximate"]`) must suppress `execution_quality` and `inconsistent_pacing`. Any
   new fine-grained metric needs the same gate.

8. **Pace is seconds per km, where larger is slower**, and authored pace ranges may arrive
   inverted. Use `ordered_target_bounds()` for every comparison.

9. **Metrics come from the timeline, boundaries come from laps.** Do not mix lap aggregates into
   metric computation.

10. **`MatchEvidence` is structured, not prose.** Every persisted claim must remain traceable to
    lap IDs, trackpoint indices, and the strategy that produced it.

11. **Segmentation strategies are pure and ordered.** `segment()` must not touch the database,
    and registry order is priority order.

12. **Matching failure must never fail an import.** A parsed activity is valuable on its own.

13. **Unlink never destroys execution history.** Clearing `workout.activity_id` must not delete
    `WorkoutExecution` rows. `get_for_activity` is scoped to executions whose workout still
    points at that activity, so a stale execution is hidden and recoverable by re-linking.
