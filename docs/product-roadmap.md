# Pace.coach — Product Roadmap

> **Canonical source of truth** for product direction, current state, and implementation
> sequencing. Living document — update it in the same PR that changes the reality it describes.
>
> Last verified against code: **2026-09-28** (M2 domain/API landed; M1 coach half still open; small M2 UI follow-ups remain).
> Companion document: [`execution-architecture.md`](./execution-architecture.md).

## Status legend

Feature state (section 2):

| Status | Meaning |
|---|---|
| `DONE` | Implemented end to end and usable by a real user |
| `IN PROGRESS` | Actively being built, not yet usable |
| `PARTIAL` | Core path works; meaningful gaps or unreachable cases remain |
| `PLACEHOLDER` | UI or route exists but renders stub / mock / hardcoded data |
| `MISSING` | No implementation of any kind |

Roadmap state (section 6):

| Status | Meaning |
|---|---|
| `DONE` | Shipped |
| `IN PROGRESS` | Being implemented now |
| `NEXT` | Approved, next to be implemented |
| `FUTURE` | Agreed direction, not scheduled |
| `NEEDS DECISION` | Blocked on a product decision |

**Rule for this document: nothing is described as working unless the code supports it.**

---

## 1. Product vision

### The core product loop

```
Plan  →  Execute  →  Compare  →  Review  →  Learn  →  Track Progress  →  Improve Training
  ↑                                                                              │
  └──────────────────────────────────────────────────────────────────────────────┘
```

| Stage | Meaning |
|---|---|
| **Plan** | A coach prescribes structured training with explicit intent |
| **Execute** | The athlete trains; the device records what actually happened |
| **Compare** | The system aligns the plan against reality, step by step |
| **Review** | Deviations surface as concrete, discussable observations |
| **Learn** | Athlete and coach explain *why* it happened; the explanation is retained |
| **Track Progress** | Deterministic metrics accumulate into baselines and trends |
| **Improve Training** | Evidence from the loop informs the next planning cycle |

Each stage must produce durable, structured data. A stage that only renders a chart and
discards its reasoning breaks the loop.

### Long-term vision

Pace.coach is not a workout tracker. It is a **collaborative coaching system that captures
coaching knowledge over time**.

The three participants:

```
Athlete  ↔  Coach  ↔  AI
```

- **Athlete** — executes training, reports subjective context, asks questions
- **Coach** — prescribes, interprets, decides, and explains
- **AI** — retrieves relevant history, surfaces patterns, summarizes evidence

**AI augments the coach; it does not replace the coach.** The AI's role is to make a coach's
accumulated judgement searchable and to prevent relevant history from being forgotten. Every
AI capability must trace back to structured data a human produced.

The strategic asset is the **accumulated record of coaching decisions and their outcomes**.
This is why capture-at-write-time matters more than analysis features: history not recorded
today cannot be recovered later.

---

## 2. Current product state

### Athlete

| Area | Status | Reality |
|---|---|---|
| Today | `PARTIAL` | Real recovery check-in, today's workout, 7-day strip, recent activities, FIT upload. Scheduled workouts can be marked complete or skipped from the workout detail modal. The "AI insight" block is static text. |
| Calendar | `PARTIAL` | Month calendar on `/activities` backed by `/api/training/calendar` is real. Shows executable workouts (with optional `cycle_context`). **Does not yet render unconverted PlanItem placeholders** on their resolved planned date. No dedicated weekly view. Event popup shows the backend-derived `execution_score` when one exists. |
| Planned workouts | `DONE` | Read path fully wired. Athlete can mark complete or skip from Today (`PUT /workouts/{id}/complete` and `/skip`), only while status is `scheduled`. |
| Activities | `DONE` | List + calendar, date-ranged, real API, links to detail. |
| Activity detail | `PARTIAL` | Summary and execution sections real. Charts, zone distribution, insights and coach notes are placeholders. |
| Planned vs Actual | `DONE` | `PlannedVsActual.tsx` renders real `WorkoutExecution` data — when an execution exists. |
| Workout Review | `PARTIAL` | Issue questionnaire renders real issues and persists athlete responses (**foundation for M1**). "Discussion" panel is still a stub — no coach reply, no resolution. |
| Athlete feedback | `DONE` (athlete half) | One athlete response per `ExecutionIssue` (reason / other / notes / responded_at), overwritable. No thread, no coach reply — that is M1. |
| Recovery | `PARTIAL` | The `/recovery` nav route is a `ComingSoonPage`. The real check-in lives on Today and is fully wired, with a computed `readiness_score`. |
| Performance | `PLACEHOLDER` | `/performance` redirects to the profile page (thresholds, zones, body metrics). No trends, no progress, no history. |

### Coach

| Area | Status | Reality |
|---|---|---|
| Athlete management | `PARTIAL` | Invite, user search, accept/reject, active roster all real. Roster rows still display mock mesocycle labels (not yet wired to live plans). |
| Cycle Designer / Training Plan | `PARTIAL` | Domain + API + coach/athlete Cycle Designer UI are live (`/api/planning/...`). Coach can design mesocycles, microcycles, and PlanItems; convert placeholders to workouts; run cycle review. **Follow-ups:** Placement UI in Designer (unplaced / Day N / specific date) and Calendar presentation of placeholders — see M2. |
| Individual Workout Builder | `DONE` | Three-pane builder (Library / Canvas / Inspector) with intent bar. Step types gated by sport, time/distance/lap-button durations, pace/HR/power/cadence targets, real zone integration, single-level repeats, templates, client validation. Builder can open from a PlanItem via builder-context. |
| Workout assignment | `DONE` | `POST /api/training/workouts/assign`, athletes × dates, capped at 50 server-side. Ad-hoc assignment remains; plan-attached workouts also flow through planning attach/create. |
| Activity review | `PARTIAL` | Coach opens the **same** `/activity/:id` page as the athlete and can **read** saved athlete responses. No coach-specific review UI, no reply, no resolution, no "mark reviewed" (button disabled). That coach half is M1. |
| Coach Today attention queue | `PARTIAL` | Real signals for skipped sessions, missing recovery, low readiness, no planned session. **Not** an unreviewed-execution review queue (M1). |
| Coach ↔ athlete communication | `MISSING` | No comment/thread table, no coach-reply API, no Discussion UI. Entry points are disabled buttons or "coming soon". Entirely M1. |

### Execution

| Area | Status | Reality |
|---|---|---|
| FIT import | `DONE` | Upload → parse → persist. Production uses `SupabaseStorage`; development uses `LocalFilesystemStorage`. Matching still runs in-process via `BackgroundTasks`. |
| Activity laps | `DONE` | Full lap rows persisted including `wkt_step_index`, `lap_trigger`, `intensity`, `message_index`. |
| Workout matching | `PARTIAL` | Engine is real. Triggers: FIT-import auto-link (unambiguous same-day + sport), `POST .../link-activity`, and `POST .../workout-execution/rematch`. Strava activities still cannot be matched (no laps/streams). |
| `WorkoutExecution` | `DONE` | Real persistence, idempotent per `(workout_id, activity_id, algorithm_version)`. Unlink hides an execution without deleting it. |
| `WorkoutStepExecution` | `DONE` | One row per planned occurrence, keyed `(authored_step_id, occurrence_ordinal)`. |
| `ExecutionIssue` | `DONE` | 8 issue codes with real detection rules and thresholds. |
| Execution scoring | `DONE` | Per-step scores plus a session aggregate (`aggregate_execution_score`: mean of non-null step scores, 1 decimal) exposed on `WorkoutExecutionOut` and the training calendar. Unscored sessions show no score. |
| Workout Review | `DONE` (athlete data path) | Consumes real execution data via `GET /api/activities/{id}/workout-execution`. Athlete responses persist. Coach reply / resolution / review queue are M1. |

---

## 3. Current architecture

### Repository layout

```
pace.coach/
├── backend/          FastAPI + SQLAlchemy 2 + Alembic (Python ≥3.12)
│   ├── src/api/app.py        app factory, router registration, CORS, error envelope
│   ├── src/core/             auth (JWT), config, database, responses, rate_limit
│   ├── src/models.py         imports every ORM model for Alembic metadata
│   ├── src/modules/          feature modules (see below)
│   ├── migrations/versions/  Alembic chain, head = z3c4d5e6f7a8
│   └── tests/
├── frontend/         React 19 + Vite 6 + TypeScript, React Router v7, Tailwind 4
└── docs/
```

A second repository, `evolve-training`, is a **Lovable-hosted UI/UX wireframe prototype** for
Pace.coach's future interface. It has no backend integration and all of its data is mock.
It is not the production frontend and must not be wired to the API.

### Backend modules

| Module | Owns | State |
|---|---|---|
| `identity` | `User`, `UserRole`, auth endpoints | implemented |
| `coaching` | `CoachAthleteRelation`, invitation lifecycle, access helper | implemented |
| `training` | `Workout`, `WorkoutTemplate`, calendar, assignment, step schema, activity linking | implemented |
| `planning` | `TrainingPlan`, `Mesocycle`, `Microcycle`, `PlanItem` (+ placement), cycle review, change log | implemented (M2) |
| `execution` | plan resolution, segmentation, metrics, scoring, issues, execution read API | implemented |
| `activity_import` | FIT upload, `StoredFile`, `ActivityImport`, laps, track points, sources | implemented |
| `fit_parser` | pure FIT parsing → Pydantic DTOs (no DB) | implemented |
| `gear_track` | **`Activity` and `ActivityType` live here**, plus legacy gear/shoe tracking | implemented |
| `athlete_profile` | sports, sport profiles, thresholds, zones, baselines, body metrics | implemented |
| `recovery` | `RecoveryEntry`, computed readiness | implemented |
| `third_party/strava` | OAuth + webhook summary import | implemented |
| `ai` | — | scaffold only (`__init__.py` + README) |
| `adaptation` | — | scaffold only (`__init__.py` + README) |

> Note the coupling: the `Activity` model lives in `gear_track` for historical reasons
> (this backend began as a shoe-mileage tracker). Recorded as technical debt in section 9.

### Frontend

- **Routing** — `react-router-dom` v7 in `frontend/src/app/App.tsx`. Guards: `RequireAuth`,
  `RequireRole`. Dual-role users get an athlete/coach view switcher in `AppLayout`.
- **Data layer** — native `fetch` through `modules/shared/api.ts`. No React Query, no global
  store; each screen fetches in an effect.
- **Builder drag-and-drop** — `@dnd-kit` (canvas step reordering).
- **Modules** — mirror backend domains (`athlete/`, `coach/`, `planning/`, `execution/`,
  `workout/builder/`, `activities/`, `calendar/`, `recovery/`, `athlete-profile/`).

### Database

PostgreSQL via SQLAlchemy 2. Supabase in production, `docker compose up db` locally.
Alembic head `z3c4d5e6f7a8` (adds the M2 planning tables).

Two project conventions apply to schema work:

- **Enums** are application-level, stored as `VARCHAR`. Do not create DB-native `ENUM` types.
- **Row-Level Security** must be enabled on every new `public` table in the same migration
  that creates it (the API connects as superuser and bypasses RLS; this is a Supabase
  requirement, not an authorization mechanism).

### Authentication / roles

- JWT HS256, `Authorization: Bearer`, token in `localStorage`. Claims: `sub`, `aud`, `exp`,
  `iss`, `iat`. Issuer/audience still carry legacy `shoe-tracker-*` values.
- Roles live in the `user_roles` table (`athlete`, `coach`); a user may hold both.
  `require_role(...)` gates endpoints.
- Coach access to athlete data requires an **active** `CoachAthleteRelation`, checked by
  `get_active_coach_athlete_relation` / `require_coach_athlete_access`. Authorization is
  binary: the `permissions` JSON column is stored, returned in API responses, and never
  written or enforced.
- Rate limiting exists only on auth endpoints, in-memory.
- Response envelope: `{success: true, ...}` / `{success: false, error: "..."}`.

### Training domain

`Workout` remains the single scheduled, executable unit: `athlete_id`, `scheduled_date`,
`workout_type`, `sport_id`, intent fields (`purpose`, `target_rpe`, `description`), and a
`steps` JSON array. `WorkoutTemplate` is a coach-owned reusable structure with the same step
shape and no scheduling.

Above it, M2 adds a planning hierarchy owned by `modules/planning/`:

```
TrainingPlan → Mesocycle → Microcycle → PlanItem ──(optional)──> Workout
```

A `PlanItem` is planning intent (placeholder or converted). Placement
(`null` | `relative_day` | `specific_date`) is the source of truth for calendar position;
`resolved_date` is derived and never persisted. Ad-hoc workouts (no PlanItem) still work.

Steps are JSON but carry **stable UUID identity** minted by `ensure_step_ids()` and preserved
across coach edits. This is the invariant everything downstream depends on.

### Activity / import domain

`POST /api/activities/import/fit` → `StoredFile` + `ActivityImport(pending)` →
`BackgroundTasks` → parse → `Activity` + `ActivityLap[]` + `ActivityTrackPoint[]` (~1 Hz) +
`ActivitySource` (device workout, events, developer fields as JSON).

Dedup is three-layered: SHA-256 checksum, semantic duplicate (date + start ±5 min +
duration ±5 s + distance ±10 m), and a unique index on `activities.activity_import_id`.
Stale imports are recovered on startup.

Strava produces **summary `Activity` rows only** — no laps, no streams.

### Execution domain

See [`execution-architecture.md`](./execution-architecture.md).

---

## 4. Execution architecture (summary)

```
FIT upload  or  POST /api/training/workouts/{id}/link-activity
  → parsing (FitParser) [FIT path only]
  → Activity
  → ActivityLap / ActivityTrackPoint
  → workout linking (auto or manual)
  → ExecutionMatchingService (match_from_normalized or match_persisted)
  → WorkoutExecution
  → WorkoutStepExecution
  → ExecutionIssue
  → Planned vs Actual (UI) / calendar execution_score / Workout Review (UI)
```

### Concepts that are true today

- **FIT is the only source capable of feeding structured execution matching.** The matcher
  needs laps and per-record streams; only the FIT import path persists them.
- **Strava cannot feed the matcher.** Its webhook creates a summary `Activity` with no
  `ActivityLap` and no `ActivityTrackPoint` rows.
- **Matching has several segmentation strategies**, selected first-match by capability:
  `device_step_index` → `lap_structure` → `signal`. A fourth, `manual`, is implemented but
  not registered.
- **Execution scoring already exists** — three independently nullable dimensions
  (completion, intensity adherence, execution quality) averaged over non-null parts.
- **Execution issues already exist** — 8 codes across 5 dimensions with real thresholds.
- **Workout Review already consumes real execution data** and persists athlete responses.

### Weak points remaining after M0

| Weak point | Consequence |
|---|---|
| Auto-link still returns `None` when two same-sport workouts share a day | Recoverable via `POST .../link-activity` (no silent guessing). |
| Strava activities have no laps or streams | Re-match returns 422 instead of a silent unmatched row. |
| Matching still runs in-process via `BackgroundTasks` | A real job runner remains an M3 prerequisite. |
| Plan snapshot created at match time, not assignment time | `WorkoutPlanSnapshot` is built from the **live** `workout.steps` when matching runs. Historical protection actually comes from workouts being uneditable once status leaves `scheduled`, not from the snapshot itself. |
| Nested repeats blocked by authoring validation | `RepeatBlockModel.steps` is typed `list[WorkoutStepModel]`, so a repeat can never contain a repeat — even though the resolver handles nesting. |
| Manual link UI is API-first | Recovery is operator-driven via the endpoint unless a later slice wires athlete/coach UI. |

---

## 5. Domain model

### Existing entities

```
User ──< UserRole (athlete | coach)
  │
  ├──< CoachAthleteRelation (pending | active | revoked | rejected; permissions JSON [unused])
  │
  ├──< TrainingPlan (athlete, coach?, dates, status, planning_timezone)
  │       └──< Mesocycle ──< Microcycle ──< PlanItem ──(workout_id?)──> Workout
  │              ├── CycleSystemAnalysis (immutable)
  │              └── CycleCoachReview (versioned draft/approved)
  │       └──< PlanChangeLog (append-only; entity_id is not an FK)
  │
  ├──< Workout (athlete_id, scheduled_date, slot_ordinal, workout_type, steps JSON, status, activity_id?)
  │       ├──< WorkoutPlanSnapshot (resolved_plan JSON)
  │       └──< WorkoutExecution ──< WorkoutStepExecution
  │                              └──< ExecutionIssue (+ athlete_reason / notes / responded_at)
  │
  ├──< Activity (date, start_time, distance, sport_id, source, activity_import_id?)
  │       ├──< ActivityLap
  │       ├──< ActivityTrackPoint      (~1 Hz — FIT imports only)
  │       └──< ActivitySource          (raw_metadata JSON: device_workout, events, dev fields)
  │
  ├──< RecoveryEntry (daily, unique per user+date, computed readiness_score)
  ├──< AthleteSportProfile ──< AthleteZone
  ├──── AthleteBaseline (1:1 — HRV min/max + resting HR only)
  └──< AthleteBodyMetric (time series: weight, height)

User (coach) ──< WorkoutTemplate (steps JSON — no FK from Workout back to template)
```

| Entity | Notes |
|---|---|
| `User` | `users`. Roles in a separate table; a user may be both athlete and coach. |
| `CoachAthleteRelation` | Unique `(coach_id, athlete_id)`. Only `status = 'active'` grants access. |
| `TrainingPlan` | Macrocycle container. Status `draft` / `active` / `completed` / `archived`. Only one active plan may overlap dates per athlete. |
| `Mesocycle` | Training block with focus, optional `anchor_date`, ordinal within the plan. |
| `Microcycle` | Coach-defined period (`duration_days` 1–28). Dates derived when the plan has a start date; duration mode when undated. |
| `PlanItem` | Planning intent inside a microcycle. Optional `workout_id` (placeholder vs converted). Placement: `placement_type` null \| `relative_day` \| `specific_date`, with `placement_day` / `placement_date`. Resolved calendar date is derived, never stored. |
| `CycleSystemAnalysis` | Immutable deterministic analysis snapshot per mesocycle. |
| `CycleCoachReview` | Versioned coach review (`draft` / `approved`); absence of a row = not reviewed. |
| `PlanChangeLog` | Append-only audit of plan mutations; `entity_id` is not an FK so rows survive deletes. |
| `Workout` | The single scheduled, executable unit. Editable only while `scheduled`. `slot_ordinal` orders multiple sessions on the same date; it does not make auto-link pick a winner. May exist without a PlanItem (ad-hoc). |
| `WorkoutTemplate` | Coach-owned reusable structure. **No lineage** — `templateStepId` exists in the schema and nothing populates it. |
| `WorkoutPlanSnapshot` | `resolved_plan` JSON = `ResolvedPlan` (tree + flat occurrences). Written at match time. |
| `Activity` | Defined in the `gear_track` module. Unique per import; partial unique on `(user_id, strava_activity_id)`. |
| `ActivityLap` | Carries the FIT execution evidence: `wkt_step_index`, `lap_trigger`, `intensity`, `message_index`. |
| `ActivityTrackPoint` | One row per FIT record. HR, speed, pace, power, cadence, altitude, position, temperature, running dynamics. Indexed on `activity_id` only. |
| `ActivitySource` | Provenance + `raw_metadata` JSON holding the device workout and events. |
| `WorkoutExecution` | Unique `(workout_id, activity_id, algorithm_version)`. |
| `WorkoutStepExecution` | Unique `(workout_execution_id, authored_step_id, occurrence_ordinal)`. Typed metric columns + `metrics` / `match_evidence` / `score_components` JSON. |
| `ExecutionIssue` | `code`, `severity`, `dimension`, `payload` JSON, plus five athlete-response columns. |
| `RecoveryEntry` | HRV, resting HR, body battery, fatigue, soreness, mood, sleep, notes. `readiness_score` is computed server-side. |
| `AthleteSportProfile` | Per-sport thresholds: pace, HR, FTP, CSS. Manual entry. |
| `AthleteZone` | Named ranges (`hr` / `pace` / `power`) under a sport profile. Manual — no derivation from thresholds. |
| `AthleteBaseline` | 1:1 with user. **Only** HRV min/max and resting HR. Not a performance baseline. |
| `AthleteBodyMetric` | Dated weight / height observations. |

### No domain model exists for

These are **`MISSING`**, not partial. Nothing in the schema represents them:

| Concept | Consequence |
|---|---|
| Race / Goal Event entity | `goal_event_date` on `TrainingPlan` is a date field only. `race_pace` remains a `WorkoutType` enum value, not a goal object. |
| Coach ↔ athlete conversation | No comment, message, or thread table. No issue resolution state. No coach-reviewed flag on executions. (M1) |
| Coach decision history (workout edits) | `Workout.steps` is still destructively overwritten on edit. Plan-structure changes are logged in `plan_change_log`; workout-step edits are not. |
| Activity-level performance metrics | No per-activity rollup table. HR drift and pace variability are computed **only inside matched workout step windows**; unmatched and unstructured activities produce nothing analyzable. |
| Performance trends | No trend, baseline sample, or performance event storage. |

### JSON that may need a relational model later

| Location | Why |
|---|---|
| `workouts.steps` / `workout_templates.steps` | Querying across steps, template lineage, step versioning. The seam already exists: `plan_source.py` defines a `PlanSource` interface reserving a relational implementation. |
| `execution_issues.payload` + athlete response columns | This is the coaching-knowledge substrate and is currently unqueryable. |
| `workout_step_executions.metrics` | Adequate for display, wrong for trend analysis. |
| `coach_athlete_relations.permissions` | Only if granular permissions are ever needed. |
| `activity_sources.raw_metadata` | Device workout and events could become queryable tables. |
| `workout_executions.extra_work` | Defined in the migration, never written by any code. |

---

## 6. Roadmap

### M0 — Execution Loop Integrity · `DONE`

**Goal:** make the existing plan → execute → match → review loop reliable enough for real
beta usage. Nothing here is a new feature; it finishes what is already built.

**Shipped**

| Item | Note |
|---|---|
| Production FIT storage | `SupabaseStorage` over `requests`. `build_storage_provider()` returns it in production and `LocalFilesystemStorage` otherwise. Config: `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`, `ACTIVITY_STORAGE_BUCKET` (default `activity-files`). |
| Manual activity ↔ workout link / unlink | `POST`/`DELETE /api/training/workouts/{id}/link-activity`. No silent overwrite; an activity cannot be linked twice. Unlink never deletes executions. |
| Re-match endpoint | `POST /api/activities/{id}/workout-execution/rematch` wraps `match_persisted()` with preconditions and an explicit commit. |
| Matching on link | Manual link and rematch share `rematch_workout_activity`. FIT import still uses `match_from_normalized`. |
| `Workout.slot_ordinal` | `INTEGER NOT NULL DEFAULT 0`. Calendar orders by `(scheduled_date, slot_ordinal, id)`. Auto-link orders candidates the same way but still returns `None` when more than one is eligible. |
| Safer auto-link | Candidates whose `sport_id` is set and differs from the activity are dropped. Null `sport_id` stays eligible. |
| Real execution score | `aggregate_execution_score` is the single session definition (mean of non-null step scores, 1 decimal). Calendar and `WorkoutExecutionOut` both use it. `HARDCODED_EXECUTION_SCORE` is gone. |
| Athlete complete / skip UI | `WorkoutDetailModal` `athleteActions` on Today, scheduled workouts only. |

**Decisions recorded in M0**

- Storage is Supabase Storage, not GCS/S3. `object_key` stays `fit-uploads/{sha256}.fit`.
- Session score is derived on read; there is no `WorkoutExecution.score` column.
- `slot_ordinal` does **not** make auto-link guess. Ambiguity is recovered by manual link.
- Unlink preserves history: `get_for_activity` only returns executions whose workout still points at that activity.

**Remaining limitations after M0**

- Manual link is API-first; athlete/coach UI for picking an activity is not wired.
- Strava activities still cannot be matched (no laps or streams); rematch says so with 422.
- Matching still runs in-process via `BackgroundTasks`; a real job runner remains an M3 prerequisite.
- SQLite test fixture is not byte-identical to Postgres (partial unique indexes degrade to plain unique indexes).

**Acceptance criterion**

An athlete and coach can complete
`Plan → Run → Upload FIT → Match → Planned vs Actual → Review`
without developer intervention. Ambiguous same-day sessions recover via the link API plus rematch.

Double days used to make auto-link return `None` permanently; that was why M0 had to land before the cycle builder.

---

### M1 — Coach ↔ Athlete Feedback · `FUTURE`

Close the Workout Review loop on the **coach side**. The athlete half already ships; M1 is
almost entirely the missing coach half — **not** nearly done.

```
ExecutionIssue  →  Athlete response  →  Coach response  →  Resolution / Outcome
       ▲                  ▲                    ✕                    ✕
   (exists)         (EXISTS — done)         (M1)                 (M1)
```

**Foundation already shipped (not counted as M1 remaining work)**

| Item | Reality |
|---|---|
| `ExecutionIssue` detection | 8 codes, real thresholds, persisted with executions |
| Athlete response | One response per issue (`athlete_reason` / `other` / `notes` / `responded_at`), overwritable via `POST .../athlete-responses` |
| Workout Review questionnaire UI | Athlete drawer renders real issues and saves responses |
| Coach read path | Coach can open the same activity page and see saved athlete responses |

**Still to build (actual M1 scope)**

| Item | Status | Note |
|---|---|---|
| Coaching comments | `MISSING` | Attachable to an execution, a step execution, or an issue. No comment/thread table or API today. |
| Coach replies in Discussion drawer | `MISSING` | Replace the "Discussion · coming soon" stub in `WorkoutReviewDrawer`. |
| Issue resolution state | `MISSING` | `open` / `acknowledged` / `resolved` / `dismissed` — no status column on `ExecutionIssue`. |
| Coach Today review queue | `MISSING` | Queue of **unreviewed executions** (with athlete responses waiting on coach). Today's attention queue is recovery/plan-based, not review-based. "Mark reviewed" remains disabled. |

**Why it matters:** this turns per-activity conversation into retained coaching history, and it
is the foundation M5 retrieves from. Without M1, the chain stops at the athlete response —
there is no coach side and no outcome.

*Do not implement now.*

---

### M2 — Training Plan / Cycle Builder · `DONE` (UI follow-ups remaining)

The main product feature after M0. Domain, API, and Cycle Designer UI are shipped.
Two small UI slices remain and will be followed up later (they do not block M1/M3).

**Hierarchy (as shipped)**

```
TrainingPlan
  → Mesocycle
      → Microcycle
          → PlanItem  (placeholder or converted; placement optional)
              → Workout            [existing, unchanged schema]
                  → WorkoutExecution
                      → WorkoutStepExecution
```

**Shipped**

| Item | Note |
|---|---|
| Planning module | `backend/src/modules/planning/` — models, enums, date reflow, lock/immutability, change log, cycle analysis/review, calendar bands / `cycle_context`. |
| Schema | Tables: `training_plans`, `mesocycles`, `microcycles`, `plan_items`, `cycle_system_analyses`, `cycle_coach_reviews`, `plan_change_log`. Migration `z3c4d5e6f7a8`. Purely additive — no columns added to `workouts` / execution. |
| PlanItem placement (domain/API) | Canonical: `placement_type` null \| `relative_day` \| `specific_date`, plus `placement_day` / `placement_date`. `resolved_date` derived at read time; never persisted. Relative days move with the microcycle; specific dates pin and surface `placement_conflict` when out of range. |
| Progressive refinement | Undated (duration-mode) plans, mesocycles without items, and unplaced PlanItems are valid. |
| Historical immutability | Lock states `locked` / `current` / `future` enforced on plan mutations; `plan_change_log` records every write. |
| Cycle Designer UI | Coach Cycle Designer + athlete cycle view, review panel, attach/convert PlanItem → Workout, builder-context integration. |
| Calendar cycle context | Executable workouts linked to a PlanItem expose `cycle_context` on the training calendar. |

**UI follow-ups (deferred — not blocking other milestones)**

| # | Item | Note |
|---|---|---|
| 1 | Placement UI in Designer | Coach must be able to set PlanItem placement as: **Not scheduled** (unplaced) · **Day N** (`relative_day`) · **Specific date** (`specific_date`). Domain/API already support this; Designer UI does not yet expose it. |
| 2 | Calendar presentation of placeholders | Show a placed PlanItem placeholder on its resolved planned date, clearly distinct from an executable/completed Workout. Placeholder is not executable until converted. Do not invent a separate CalendarEvent entity for placeholders. |

**Deliberate constraints that remain true**

- `Workout` stays the single executable entity; planning attaches via `plan_items.workout_id`.
- No execution-layer change was required for M2.
- Template lineage (`template_id` / `templateStepId`) was deferred.

---

### M3 — Activity Metrics & Baselines · `FUTURE`

**Intended pipeline**

```
Activity  →  ActivityMetrics  →  BaselineSamples  →  CurrentBaseline
```

- **`ActivityMetrics`** — one deterministic row per activity, for **all** activities, not only
  matched workouts. Today, HR drift and pace variability exist only inside matched step
  windows, so baseline history would have holes exactly where most training happens.
- **`BaselineSamples`** — **append-only** observations, each carrying its source activity,
  effective date, confidence, and algorithm version.
- **`CurrentBaseline`** — materialized best current estimate per athlete / sport / metric.

**Initial areas**

- pace relative to HR
- power relative to HR
- HR drift
- threshold performance
- durability
- recovery response

**Important principle: baseline observations are append-only.** Never overwrite a baseline.
Storing only the current value makes "when did this change?" permanently unanswerable, which
is the entire point of the layer.

Prerequisite work inside this milestone: persist the session-level FIT fields that are already
parsed and discarded (`avg_hr`, `max_hr`, `normalized_power`, `elevation_gain`, `moving_time`),
and normalize timestamp handling.

*Do not implement the algorithms now.*

---

### M4 — Progress Engine · `FUTURE`

```
Raw activities  →  normalized metrics  →  athlete baselines  →  trends  →  performance events
```

The system should eventually detect meaningful improvements and regressions automatically:

- improved pace at the same HR
- lower HR at the same pace or power
- threshold improvement
- declining aerobic efficiency
- reduced durability

Detection must be deterministic and explainable — a performance event should always be able to
name the activities and baseline samples that produced it.

*Do not implement now.*

---

### M5 — AI Coach · `FUTURE`

**Context the AI layer will need**

- training plan (M2)
- workout history
- `WorkoutExecution` / `WorkoutStepExecution`
- `ExecutionIssue`
- athlete feedback
- coach decisions (requires a decision log — see technical debt)
- outcomes (M1)
- baselines (M3)
- performance trends (M4)
- historical similar cases

**What the AI should do**

- retrieve relevant history
- identify patterns
- summarize evidence
- suggest possible explanations
- surface previous successful interventions
- help coaches identify patterns across athletes

**AI does not replace the coach.** Every output should be attributable to structured data a
human produced, and presented as evidence for a coach's decision rather than a decision.

Two foundations are **write-time** and cannot be backfilled: the coach decision log and coach
responses/outcomes. M2 now captures plan-structure changes in `plan_change_log`. Workout-step
edits and coach review replies (M1) are still not logged — if those are not captured as M1 lands,
that history will not exist when M5 arrives.

*Do not implement now.*

---

## 7. Dependency graph

```
                      M0 — Execution Loop Integrity   [DONE]
                                    │
              ┌─────────────────────┼─────────────────────┐
              │                     │                     │
   M1 — Coach ↔ Athlete    M2 — Training Plans /    M3 — Activity Metrics
        Feedback*               Cycles  [DONE]**          & Baselines
      (parallel foundation)         │                     │
              │                     └──────────┬──────────┘
              │                                │
              │                     M4 — Progress Engine
              │                                │
              └────────────────┬───────────────┘
                               │
                        M5 — AI Coach
```

\* M1 athlete-response foundation already ships. Remaining work is the coach half: comments,
Discussion replies, issue resolution states, unreviewed-execution review queue.

\*\* M2 domain/API/Designer are done. Remaining UI follow-ups: Placement UI in Designer;
Calendar placeholder presentation. These do not block M1/M3/M4.

Notes:

- **M0 and M2 (core) are done.** M1 (coach half) and M3 are mutually independent and may be reordered or parallelized.
- **M1 is a parallel foundation, not a blocker for M3.** It feeds M5 directly: without
  coach responses and outcomes, the AI has no coaching history to retrieve. Do not treat
  athlete responses alone as “M1 done.”
- **M4 requires both M2 and M3** — trends need metrics, and interpreting them needs plan
  context. M2's remaining UI follow-ups are not a prerequisite for starting M3 or M4 design.
- **M3 requires a scalable background job mechanism.** The current approach (FastAPI
  `BackgroundTasks` plus raw threads for stale-import recovery) cannot survive recomputing or
  backfilling metrics across every historical activity for every athlete. Treat the job runner
  as an explicit prerequisite of M3, not an implementation detail.

---

## 8. Open product decisions · `NEEDS DECISION`

Not decided in this task. Each one changes scope downstream.

| # | Decision | Why it matters |
|---|---|---|
| 1 | Remove Strava completely, or keep it as a summary-only feed? | Strava cannot feed the matcher, but it is currently the only **automatic** ingestion path. Removing it makes manual FIT upload the sole route in. |
| 2 | Running-only beta, or running + cycling? | Cycling authoring works; the cycling metric extractor is a thin wrapper over running with no dedicated tests. |
| 3 | Support nested repeats? | The resolver already handles them; only the authoring validator blocks them. Affects builder UX and plan expressiveness. |
| 4 | Plan templates — coach-owned, or platform-level? | Deferred past M2 v1; determines whether a `PlanTemplate` entity is needed or a copy operation is enough. |
| 5 | Step-level RPE? | Today RPE is workout-level only. Adding it changes the step schema and every consumer. |
| 6 | Can an athlete self-plan without a coach? | Every training write path currently requires the coach role. Affects onboarding and the addressable market. |
| 7 | Garmin Connect integration in future? | The natural answer to decision 1; changes how much effort manual FIT upload deserves. |
| 8 | Exact baseline metrics | Which metrics are first-class in M3, and their precise definitions. |
| 9 | Exact definition of progress events | What magnitude and confidence make a change worth telling an athlete about. |

---

## 9. Technical debt

Discovered during the 2026-08-13 audit. Items 1–5 (production storage, hardcoded score,
narrow auto-link, missing manual link, missing re-match) were fixed in M0. Item 18
(dead root `src/`, `migrations/`, `scripts/` directories containing only `__pycache__`)
was cleaned up.

| # | Item | Impact |
|---|---|---|
| 6 | Legacy shoe-tracker naming and structure | JWT issuer `shoe-tracker-backend`, audience `shoe-tracker-api`, DB defaults `shoe_tracker`; the `Activity` model lives in `gear_track`; live `/api/shoes` routes; `docs/SHOE_TRACKER_APP_PLAN.md` and `docs/update_gear_schema.md` describe a different product. |
| 7 | Stale module READMEs | `training/`, `coaching/`, and `recovery/` READMEs all say "Scaffold only — implementation deferred" for fully implemented modules. The root `README.md` repeats the claim. Actively misleading to agents. |
| 8 | No CI | No workflow config anywhere in the repository. Tests run only locally. |
| 9 | Mixed timestamp handling | FIT yields naive UTC, Strava stores naive local. No normalization policy. Any time-of-day analysis will be wrong. |
| 10 | Discarded FIT session-level metrics | `avg_hr`, `max_hr`, `avg_power`, `normalized_power`, `threshold_power`, `elevation_gain/loss`, `calories`, `moving_time` are all parsed into `ActivityMeta` and never persisted. Also lap `max_power` / `normalized_power` and trackpoint `accumulated_power` / `motor_power`. |
| 11 | Unreachable execution code | `insights.py` (the whole confidence-gating layer) has no route; `get_insights` has no caller; `WorkoutExecutionStatus.pending` / `.failed` and `StepExecutionStatus.partially_executed` / `.substituted` are never emitted. |
| 12 | `ManualStrategy` not registered | Fully implemented segmentation strategy absent from `default_registry()` — free capability once a UI exists. |
| 13 | Mock athlete context in coach UI | `coach/athlete/mockAthleteContext.ts` still supplies fake mesocycle labels on the roster; Cycle Designer itself uses live planning APIs. |
| 14 | No full FIT-import execution integration test | Persistence tests cover manual link, rematch idempotency, auto-link, and score aggregation. The FIT import hook itself still has no end-to-end test. `detect_issues` is imported by the matching test module but never exercised. |
| 15 | Row-by-row track point inserts | One `db.add()` per FIT record — thousands per import. No `(activity_id, timestamp)` composite index. |
| 16 | Unused schema | `coach_athlete_relations.permissions` (stored, returned, never enforced) and `workout_executions.extra_work` (never written). |
| 17 | Orphaned frontend components | `CreateWorkoutForm`, `EditWorkoutModal`, `CoachMonthCalendar`, and the legacy `WorkoutBuilder` have no route and no live importer. |
| 19 | Destructive coach edits (workout steps) | `Workout.steps` is overwritten in place with no version history. Plan-structure mutations are logged in `plan_change_log` (M2); step-level decision history for M5 remains open. |
