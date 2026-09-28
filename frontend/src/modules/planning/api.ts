import { apiDelete, apiGet, apiPost, apiPut } from "../shared/api";
import type { Workout, WorkoutCreateInput } from "../training/api";

export type TrainingPlanStatus = "draft" | "active" | "completed" | "archived";
export type MesocycleFocus =
  | "base"
  | "build"
  | "peak"
  | "taper"
  | "recovery"
  | "race"
  | "other";
export type LockState = "locked" | "current" | "future";
export type CoachReviewStatus = "draft" | "approved";

export type PlanMutationOpts = {
  reason?: string | null;
  strict?: boolean;
};

export type AnchorConflict = {
  meso_id: number;
  meso_name: string;
  anchor_date: string;
  would_start: string;
  overrun_days: number;
  kind: "overlap" | "historical";
  message: string;
};

export type PlanGap = {
  meso_id: number;
  from: string;
  to: string;
  days: number;
};

export type PlacementType = "relative_day" | "specific_date";

export type PlacementInfo = {
  type: PlacementType;
  day?: number | null;
  date?: string | null;
  resolved_date: string | null;
  conflict: boolean;
};

export type PlanItem = {
  id: number;
  microcycle_id: number;
  ordinal: number;
  placement: PlacementInfo | null;
  workout_id: number | null;
  is_placeholder: boolean;
  title: string;
  intent: string | null;
  planned_workout_type: string | null;
  planned_sport_id: number | null;
  planned_duration_min: number | null;
  planned_distance_m: number | null;
  converted_at?: string | null;
  converted_by_id?: number | null;
  created_at?: string | null;
  updated_at?: string | null;
};

export type Microcycle = {
  id: number;
  mesocycle_id: number;
  name: string | null;
  intent: string | null;
  start_date: string | null;
  end_date: string | null;
  duration_days: number;
  ordinal: number;
  lock_state: LockState | null;
  items?: PlanItem[];
  created_at?: string | null;
  updated_at?: string | null;
};

export type SystemAnalysis = {
  id: number;
  mesocycle_id: number;
  generated_at: string | null;
  generator: string | null;
  generator_version: string | null;
  data_cutoff_date: string | null;
  summary: string | null;
  metrics: unknown;
  source_refs: unknown;
};

export type CoachReview = {
  id: number;
  mesocycle_id: number;
  status: CoachReviewStatus;
  content: string | null;
  next_cycle_focus: string | null;
  version: number;
  approved_at: string | null;
  coach_id?: number;
  source_analysis_id?: number | null;
  superseded_by_id?: number | null;
  approved_by_id?: number | null;
  created_at?: string | null;
  updated_at?: string | null;
};

export type Mesocycle = {
  id: number;
  training_plan_id: number;
  name: string;
  focus: MesocycleFocus | null;
  intent: string | null;
  start_date: string | null;
  end_date: string | null;
  anchor_date: string | null;
  duration_days: number;
  ordinal: number;
  lock_state: LockState | null;
  conflict: AnchorConflict | null;
  microcycles?: Microcycle[];
  coach_review?: CoachReview | null;
  created_at?: string | null;
  updated_at?: string | null;
};

export type TrainingPlan = {
  id: number;
  athlete_id: number;
  coach_id?: number;
  name: string;
  goal: string | null;
  goal_event_date: string | null;
  start_date: string | null;
  end_date: string | null;
  status: TrainingPlanStatus;
  planning_timezone: string | null;
  notes?: string | null;
  gaps: PlanGap[];
  conflicts: AnchorConflict[];
  mesocycles?: Mesocycle[];
  created_at: string | null;
  updated_at: string | null;
};

export type TrainingPlanCreateInput = PlanMutationOpts & {
  athlete_id: number;
  name: string;
  goal?: string | null;
  goal_event_date?: string | null;
  start_date?: string | null;
  planning_timezone?: string | null;
  notes?: string | null;
};

export type TrainingPlanUpdateInput = PlanMutationOpts & {
  name?: string;
  goal?: string | null;
  goal_event_date?: string | null;
  status?: TrainingPlanStatus;
  notes?: string | null;
  planning_timezone?: string | null;
  start_date?: string | null;
};

export type MesocycleCreateInput = PlanMutationOpts & {
  name: string;
  focus?: MesocycleFocus | null;
  intent?: string | null;
  anchor_date?: string | null;
  duration_days?: number | null;
  microcycle_count?: number | null;
  microcycle_duration_days?: number | null;
  insert_at_ordinal?: number | null;
};

export type MesocycleUpdateInput = PlanMutationOpts & {
  name?: string;
  focus?: MesocycleFocus | null;
  intent?: string | null;
  anchor_date?: string | null;
};

export type MicrocycleCreateInput = PlanMutationOpts & {
  duration_days?: number;
  name?: string | null;
  intent?: string | null;
  insert_at_ordinal?: number | null;
};

export type MicrocycleUpdateInput = PlanMutationOpts & {
  name?: string | null;
  intent?: string | null;
  duration_days?: number | null;
};

export type PlanItemCreateInput = PlanMutationOpts & {
  title: string;
  intent?: string | null;
  placement_type?: PlacementType | null;
  placement_day?: number | null;
  placement_date?: string | null;
  planned_workout_type?: string | null;
  planned_sport_id?: number | null;
  planned_duration_min?: number | null;
  planned_distance_m?: number | null;
  insert_at_ordinal?: number | null;
};

export type PlanItemUpdateInput = PlanMutationOpts & {
  title?: string;
  intent?: string | null;
  placement_type?: PlacementType | null;
  placement_day?: number | null;
  placement_date?: string | null;
  planned_workout_type?: string | null;
  planned_sport_id?: number | null;
  planned_duration_min?: number | null;
  planned_distance_m?: number | null;
};

export type CoachReviewCreateInput = PlanMutationOpts & {
  source_analysis_id?: number | null;
  content?: string | null;
  next_cycle_focus?: string | null;
};

export type CoachReviewUpdateInput = PlanMutationOpts & {
  content?: string | null;
  next_cycle_focus?: string | null;
};

export type AthletePosition = {
  plan: {
    id: number;
    name: string;
    goal: string | null;
    start_date: string | null;
    end_date: string | null;
    status: TrainingPlanStatus;
  } | null;
  mesocycle: {
    id: number;
    name: string;
    intent: string | null;
    start_date: string | null;
    end_date: string | null;
  } | null;
  microcycle: {
    id: number;
    name: string | null;
    intent: string | null;
    ordinal: number;
    start_date: string | null;
    end_date: string | null;
  } | null;
  upcoming_items: PlanItem[];
  coach_review: CoachReview | null;
};

export type BuilderContext = {
  plan_item_id: number;
  athlete_id: number;
  title: string;
  intent: string | null;
  training_plan: { id: number; name: string; goal: string | null };
  mesocycle: { id: number; name: string; intent: string | null };
  microcycle: {
    id: number;
    ordinal: number;
    name: string | null;
    intent: string | null;
    start_date: string | null;
    end_date: string | null;
  };
  suggested: {
    sport_id: number | null;
    workout_type: string | null;
    scheduled_date: string | null;
    duration_min: number | null;
    distance_m: number | null;
  };
};

export type PlanDepth = "plan" | "mesocycles" | "microcycles" | "items";

export async function createPlan(input: TrainingPlanCreateInput) {
  return apiPost<{ plan: TrainingPlan }>("/api/planning/plans", input);
}

export async function listAthletePlans(athleteId: number) {
  return apiGet<{ plans: TrainingPlan[]; count: number }>(
    `/api/planning/athletes/${athleteId}/plans`,
  );
}

export async function getPlan(planId: number, depth: PlanDepth = "items") {
  const params = new URLSearchParams({ depth });
  return apiGet<{ plan: TrainingPlan }>(`/api/planning/plans/${planId}?${params}`);
}

export async function updatePlan(planId: number, input: TrainingPlanUpdateInput) {
  return apiPut<{ plan: TrainingPlan }>(`/api/planning/plans/${planId}`, input);
}

export async function deletePlan(planId: number) {
  return apiDelete<{ deleted: boolean; plan_id: number }>(`/api/planning/plans/${planId}`);
}

export async function listChangeLog(
  planId: number,
  opts?: { entity_type?: string; entity_id?: number; limit?: number; offset?: number },
) {
  const params = new URLSearchParams();
  if (opts?.entity_type) params.set("entity_type", opts.entity_type);
  if (opts?.entity_id != null) params.set("entity_id", String(opts.entity_id));
  if (opts?.limit != null) params.set("limit", String(opts.limit));
  if (opts?.offset != null) params.set("offset", String(opts.offset));
  const qs = params.toString();
  return apiGet<{ entries: unknown[]; count: number }>(
    `/api/planning/plans/${planId}/change-log${qs ? `?${qs}` : ""}`,
  );
}

export async function createMesocycle(planId: number, input: MesocycleCreateInput) {
  return apiPost<{ mesocycle: Mesocycle; plan: TrainingPlan }>(
    `/api/planning/plans/${planId}/mesocycles`,
    input,
  );
}

export async function updateMesocycle(mesocycleId: number, input: MesocycleUpdateInput) {
  return apiPut<{ mesocycle: Mesocycle; plan?: TrainingPlan }>(
    `/api/planning/mesocycles/${mesocycleId}`,
    input,
  );
}

export async function deleteMesocycle(mesocycleId: number) {
  return apiDelete<{ deleted: boolean; mesocycle_id: number; plan?: TrainingPlan }>(
    `/api/planning/mesocycles/${mesocycleId}`,
  );
}

export async function reorderMesocycles(
  planId: number,
  orderedIds: number[],
  opts?: PlanMutationOpts,
) {
  return apiPost<{ plan: TrainingPlan }>(`/api/planning/plans/${planId}/mesocycles/reorder`, {
    ordered_ids: orderedIds,
    ...opts,
  });
}

export async function createMicrocycle(mesocycleId: number, input: MicrocycleCreateInput) {
  return apiPost<{ microcycle: Microcycle; plan?: TrainingPlan }>(
    `/api/planning/mesocycles/${mesocycleId}/microcycles`,
    input,
  );
}

export async function updateMicrocycle(microcycleId: number, input: MicrocycleUpdateInput) {
  return apiPut<{ microcycle: Microcycle; plan?: TrainingPlan }>(
    `/api/planning/microcycles/${microcycleId}`,
    input,
  );
}

export async function deleteMicrocycle(microcycleId: number) {
  return apiDelete<{ deleted: boolean; microcycle_id: number; plan?: TrainingPlan }>(
    `/api/planning/microcycles/${microcycleId}`,
  );
}

export async function reorderMicrocycles(
  mesocycleId: number,
  orderedIds: number[],
  opts?: PlanMutationOpts,
) {
  return apiPost<{ plan?: TrainingPlan }>(
    `/api/planning/mesocycles/${mesocycleId}/microcycles/reorder`,
    { ordered_ids: orderedIds, ...opts },
  );
}

export async function createPlanItem(microcycleId: number, input: PlanItemCreateInput) {
  return apiPost<{ item: PlanItem }>(`/api/planning/microcycles/${microcycleId}/items`, input);
}

export async function updatePlanItem(itemId: number, input: PlanItemUpdateInput) {
  return apiPut<{ item: PlanItem }>(`/api/planning/items/${itemId}`, input);
}

export async function deletePlanItem(itemId: number) {
  return apiDelete<{ deleted: boolean; item_id: number }>(`/api/planning/items/${itemId}`);
}

export async function reorderPlanItems(
  microcycleId: number,
  orderedIds: number[],
  opts?: PlanMutationOpts,
) {
  return apiPost<{ items?: PlanItem[] }>(
    `/api/planning/microcycles/${microcycleId}/items/reorder`,
    { ordered_ids: orderedIds, ...opts },
  );
}

export async function attachWorkout(
  itemId: number,
  workoutId: number,
  opts?: PlanMutationOpts,
) {
  return apiPost<{ item: PlanItem; workout?: Workout }>(
    `/api/planning/items/${itemId}/attach-workout`,
    { workout_id: workoutId, ...opts },
  );
}

export async function detachWorkout(itemId: number) {
  return apiDelete<{ item: PlanItem }>(`/api/planning/items/${itemId}/attach-workout`);
}

export async function getBuilderContext(itemId: number) {
  return apiGet<BuilderContext>(`/api/planning/items/${itemId}/builder-context`);
}

export async function createWorkoutForItem(itemId: number, input: WorkoutCreateInput) {
  return apiPost<{ item: PlanItem; workout: Workout }>(
    `/api/planning/items/${itemId}/workout`,
    input,
  );
}

export async function generateSystemAnalysis(mesocycleId: number) {
  return apiPost<{ system_analysis: SystemAnalysis }>(
    `/api/planning/mesocycles/${mesocycleId}/system-analysis`,
    {},
  );
}

export async function getSystemAnalysis(mesocycleId: number, all = false) {
  const params = all ? "?all=true" : "";
  return apiGet<{
    system_analysis?: SystemAnalysis | null;
    system_analyses?: SystemAnalysis[];
    count?: number;
  }>(`/api/planning/mesocycles/${mesocycleId}/system-analysis${params}`);
}

export async function createCoachReview(mesocycleId: number, input: CoachReviewCreateInput) {
  return apiPost<{ coach_review: CoachReview }>(
    `/api/planning/mesocycles/${mesocycleId}/coach-review`,
    input,
  );
}

export async function updateCoachReview(reviewId: number, input: CoachReviewUpdateInput) {
  return apiPut<{ coach_review: CoachReview }>(`/api/planning/coach-reviews/${reviewId}`, input);
}

export async function newCoachReviewVersion(reviewId: number) {
  return apiPost<{ coach_review: CoachReview }>(
    `/api/planning/coach-reviews/${reviewId}/new-version`,
    {},
  );
}

export async function approveCoachReview(reviewId: number) {
  return apiPost<{ coach_review: CoachReview }>(
    `/api/planning/coach-reviews/${reviewId}/approve`,
    {},
  );
}

export async function getCoachReview(mesocycleId: number, history = false) {
  const params = history ? "?history=true" : "";
  return apiGet<{ coach_review: CoachReview | null; history?: CoachReview[] }>(
    `/api/planning/mesocycles/${mesocycleId}/coach-review${params}`,
  );
}

export async function listMyPlans() {
  return apiGet<{ plans: TrainingPlan[]; count: number }>("/api/planning/my/plans");
}

export async function getMyPlan(planId: number) {
  return apiGet<{ plan: TrainingPlan }>(`/api/planning/my/plans/${planId}`);
}

export async function getMyPosition() {
  return apiGet<AthletePosition>("/api/planning/my/position");
}

export async function getPlanningContext(
  athleteId: number,
  startDate: string,
  endDate: string,
) {
  const params = new URLSearchParams({
    athlete_id: String(athleteId),
    start_date: startDate,
    end_date: endDate,
  });
  return apiGet<{ bands: unknown[] }>(`/api/planning/context?${params}`);
}
