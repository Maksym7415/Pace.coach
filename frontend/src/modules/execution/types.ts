/** Types mirroring the WorkoutExecution read API (snake_case). */

export type IssueSeverity = "info" | "warning" | "critical";

export type IssueDimension =
  | "completion"
  | "intensity"
  | "quality"
  | "matching"
  | "structure";

export type StepExecutionStatus =
  | "executed"
  | "partially_executed"
  | "not_executed"
  | "not_attempted"
  | "substituted"
  | "unmatched";

export type WorkoutExecutionStatus =
  | "pending"
  | "matched"
  | "partial"
  | "unmatched"
  | "failed";

export type PlannedStep = {
  step_type: string;
  duration_type: string | null;
  duration_min: number | null;
  distance_m: number | null;
  target_type: string | null;
  target_min: number | null;
  target_max: number | null;
  target_zone_name: string | null;
  notes: string | null;
};

export type AthleteIssueResponse = {
  reason: string | null;
  reason_other: string | null;
  notes: string | null;
  responded_at: string | null;
};

export type ExecutionIssue = {
  id: number;
  code: string;
  severity: IssueSeverity;
  dimension: IssueDimension;
  athlete_response?: AthleteIssueResponse | null;
};

export type StepExecution = {
  authored_step_id: string;
  occurrence_path: string;
  occurrence_ordinal: number;
  status: StepExecutionStatus;
  planned: PlannedStep;
  duration_moving_s: number | null;
  distance_m: number | null;
  target_metric: string | null;
  time_in_target_pct: number | null;
  target_deviation_pct: number | null;
  score: number | null;
  issues: ExecutionIssue[];
};

export type WorkoutStub = {
  id: number;
  title: string;
  sport_code: string | null;
  scheduled_date: string;
};

export type WorkoutExecution = {
  id: number;
  workout_id: number;
  activity_id: number;
  status: WorkoutExecutionStatus;
  overall_confidence: number | null;
  algorithm_version: string;
  execution_score: number | null;
  issue_count: number;
  responded_issue_count?: number;
  workout: WorkoutStub;
  step_executions: StepExecution[];
};
