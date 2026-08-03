import { useEffect, useMemo, useState } from "react";
import { Link, useNavigate, useParams, useSearchParams } from "react-router-dom";
import { listAthleteSports, listSports, type Sport } from "../../athlete-profile/api";
import {
  assignWorkouts,
  createWorkoutTemplate,
  getWorkout,
  getWorkoutTemplate,
  updateWorkout,
  updateWorkoutTemplate,
  type Workout,
  type WorkoutTemplate as SavedTemplate,
  type WorkoutType,
} from "../../training/api";
import { todayIso } from "../../shared/dates";
import { normalizeWorkoutSteps, validateWorkoutStepDuration } from "../normalize";
import { computeRollups } from "../rollup";
import {
  BUILDER_SPORT_CODES,
  isRepeatBlock,
  type StepType,
  type WorkoutStepItem,
  type WorkoutTemplate as BuiltinTemplate,
} from "../types";
import { useAthleteZones } from "../useAthleteZones";
import { AssignFooter } from "./AssignFooter";
import { CanvasPane } from "./CanvasPane";
import { IntentBar } from "./IntentBar";
import { InspectorPane, duplicateItem } from "./InspectorPane";
import { LibraryPane } from "./LibraryPane";
import { defaultRepeatBlock, defaultStepForType } from "../StepTypePicker";

export type BuilderMode = "create" | "edit" | "template";

type CoachWorkoutBuilderPageProps = {
  mode: BuilderMode;
};

export function CoachWorkoutBuilderPage({ mode }: CoachWorkoutBuilderPageProps) {
  const navigate = useNavigate();
  const params = useParams<{ workoutId?: string; templateId?: string }>();
  const [searchParams] = useSearchParams();

  const workoutId =
    mode === "edit" && params.workoutId && Number.isFinite(Number(params.workoutId))
      ? Number(params.workoutId)
      : null;
  const templateId =
    mode === "template" && params.templateId && Number.isFinite(Number(params.templateId))
      ? Number(params.templateId)
      : null;

  const prefAthleteId = Number(searchParams.get("athleteId")) || null;
  const prefDate = searchParams.get("date");
  const prefTemplateId = Number(searchParams.get("templateId")) || null;

  const [loading, setLoading] = useState(true);
  const [sports, setSports] = useState<Sport[]>([]);
  const [sportId, setSportId] = useState<number | null>(null);
  const [purpose, setPurpose] = useState("");
  const [workoutType, setWorkoutType] = useState<WorkoutType>("easy");
  const [targetRpe, setTargetRpe] = useState<number | null>(null);
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [steps, setSteps] = useState<WorkoutStepItem[]>([]);
  const [selectedIndex, setSelectedIndex] = useState<number | null>(null);
  const [athleteIds, setAthleteIds] = useState<number[]>(prefAthleteId ? [prefAthleteId] : []);
  const [dates, setDates] = useState<string[]>([prefDate || todayIso()]);
  const [lockedAthleteId, setLockedAthleteId] = useState<number | null>(null);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  const primaryAthleteId = lockedAthleteId ?? athleteIds[0] ?? prefAthleteId ?? 0;
  const selectedSport = sports.find((s) => s.id === sportId) ?? null;
  const sportCode = selectedSport?.code ?? null;
  const { zones, profile } = useAthleteZones(primaryAthleteId, sportId);
  const rollups = useMemo(() => computeRollups(steps), [steps]);

  useEffect(() => {
    let cancelled = false;

    async function bootstrap() {
      setLoading(true);
      setError(null);

      if (mode === "edit" && workoutId) {
        const result = await getWorkout(workoutId);
        if (cancelled) return;
        if (!result.success || !result.workout) {
          setError(result.error ?? "Failed to load workout");
          setLoading(false);
          return;
        }
        applyWorkout(result.workout);
        const enrolled = await listAthleteSports(result.workout.athlete_id);
        if (cancelled) return;
        const builderSports = (enrolled.success ? (enrolled.sports ?? []) : [])
          .map((s) => s.sport)
          .filter((s) => BUILDER_SPORT_CODES.has(s.code));
        if (builderSports.length > 0) {
          setSports(builderSports);
        } else if (result.workout.sport_id && result.workout.sport_code && result.workout.sport_name) {
          setSports([
            {
              id: result.workout.sport_id,
              code: result.workout.sport_code,
              name: result.workout.sport_name,
            },
          ]);
        }
        setLoading(false);
        return;
      }

      if (mode === "template" && templateId) {
        const result = await getWorkoutTemplate(templateId);
        if (cancelled) return;
        if (!result.success || !result.template) {
          setError(result.error ?? "Failed to load template");
          setLoading(false);
          return;
        }
        applySavedTemplate(result.template);
        const sportsResult = await listSports();
        if (cancelled) return;
        setSports((sportsResult.sports ?? []).filter((s) => BUILDER_SPORT_CODES.has(s.code)));
        setLoading(false);
        return;
      }

      if (mode === "template") {
        const sportsResult = await listSports();
        if (cancelled) return;
        const builderSports = (sportsResult.sports ?? []).filter((s) =>
          BUILDER_SPORT_CODES.has(s.code),
        );
        setSports(builderSports);
        if (builderSports.length > 0) setSportId(builderSports[0]!.id);
        setLoading(false);
        return;
      }

      // create mode
      const sportsResult = await listSports();
      if (cancelled) return;
      const builderSports = (sportsResult.sports ?? []).filter((s) =>
        BUILDER_SPORT_CODES.has(s.code),
      );
      setSports(builderSports);
      if (builderSports.length > 0) {
        setSportId(builderSports[0]!.id);
      }

      if (prefTemplateId) {
        const tpl = await getWorkoutTemplate(prefTemplateId);
        if (!cancelled && tpl.success && tpl.template) {
          applySavedTemplate(tpl.template);
        }
      }

      if (prefAthleteId) {
        const enrolled = await listAthleteSports(prefAthleteId);
        if (!cancelled && enrolled.success && enrolled.sports) {
          const athleteSports = enrolled.sports
            .map((s) => s.sport)
            .filter((s) => BUILDER_SPORT_CODES.has(s.code));
          if (athleteSports.length > 0) {
            setSports(athleteSports);
            const primary =
              enrolled.sports.find((s) => s.is_primary && BUILDER_SPORT_CODES.has(s.sport.code))
                ?.sport ?? athleteSports[0];
            if (primary) setSportId(primary.id);
          }
        }
      }

      setLoading(false);
    }

    bootstrap();
    return () => {
      cancelled = true;
    };
  }, [mode, workoutId, templateId, prefAthleteId, prefTemplateId]);

  function applyWorkout(workout: Workout) {
    setLockedAthleteId(workout.athlete_id);
    setAthleteIds([workout.athlete_id]);
    setDates([workout.scheduled_date]);
    setSportId(workout.sport_id);
    setWorkoutType(workout.workout_type);
    setTitle(workout.title);
    setPurpose(workout.purpose ?? "");
    setTargetRpe(workout.target_rpe);
    setDescription(workout.description ?? "");
    setSteps(normalizeWorkoutSteps((workout.steps as WorkoutStepItem[] | null) ?? []));
  }

  function applySavedTemplate(template: SavedTemplate) {
    setSportId(template.sport_id);
    setWorkoutType(template.workout_type);
    setTitle(template.title);
    setPurpose(template.purpose ?? "");
    setTargetRpe(template.target_rpe);
    setDescription(template.description ?? "");
    setSteps(normalizeWorkoutSteps(template.steps ?? []));
  }

  function applyBuiltin(template: BuiltinTemplate) {
    if (steps.length > 0 && !window.confirm("Replace current steps with this template?")) return;
    const match = sports.find((s) => s.code === template.sportCode);
    if (match) setSportId(match.id);
    setTitle(template.title);
    setWorkoutType(template.workoutType);
    setSteps(normalizeWorkoutSteps(structuredClone(template.steps)));
  }

  function applySavedFromLibrary(template: SavedTemplate) {
    if (steps.length > 0 && !window.confirm("Replace current steps with this template?")) return;
    applySavedTemplate(template);
  }

  function updateSelected(item: WorkoutStepItem) {
    if (selectedIndex == null) return;
    const next = [...steps];
    next[selectedIndex] = item;
    setSteps(next);
  }

  function removeSelected() {
    if (selectedIndex == null) return;
    setSteps(steps.filter((_, i) => i !== selectedIndex));
    setSelectedIndex(null);
  }

  function duplicateSelected() {
    if (selectedIndex == null) return;
    const item = steps[selectedIndex];
    if (!item) return;
    const next = [...steps];
    next.splice(selectedIndex + 1, 0, duplicateItem(item));
    setSteps(next);
    setSelectedIndex(selectedIndex + 1);
  }

  function validate(): string | null {
    if (!title.trim()) return "Title is required";
    if (!sportId) return "Select a sport";
    if (steps.length === 0) return "Add at least one step";
    for (const item of steps) {
      if (!isRepeatBlock(item)) {
        const err = validateWorkoutStepDuration(item);
        if (err) return err;
      } else {
        for (const step of item.steps) {
          const err = validateWorkoutStepDuration(step);
          if (err) return err;
        }
      }
    }
    if (mode === "create") {
      if (athleteIds.length === 0) return "Select at least one athlete";
      if (dates.length === 0) return "Select at least one date";
    }
    return null;
  }

  async function handlePrimaryAction() {
    setError(null);
    setSuccess(null);
    const validationError = validate();
    if (validationError) {
      setError(validationError);
      return;
    }
    if (!sportId) return;

    setSaving(true);

    if (mode === "template") {
      const payload = {
        sport_id: sportId,
        workout_type: workoutType,
        title: title.trim(),
        purpose: purpose.trim() || null,
        target_rpe: targetRpe,
        description: description.trim() || null,
        steps,
      };
      const result = templateId
        ? await updateWorkoutTemplate(templateId, payload)
        : await createWorkoutTemplate(payload);
      setSaving(false);
      if (!result.success) {
        setError(result.error ?? "Failed to save template");
        return;
      }
      setSuccess("Template saved");
      navigate("/templates");
      return;
    }

    if (mode === "edit" && workoutId) {
      const result = await updateWorkout(workoutId, {
        scheduled_date: dates[0]!,
        sport_id: sportId,
        workout_type: workoutType,
        title: title.trim(),
        purpose: purpose.trim() || null,
        target_rpe: targetRpe,
        description: description.trim() || null,
        steps,
      });
      setSaving(false);
      if (!result.success) {
        setError(result.error ?? "Failed to save workout");
        return;
      }
      setSuccess("Workout updated");
      navigate(`/coach/athletes/${lockedAthleteId ?? athleteIds[0]}`);
      return;
    }

    const result = await assignWorkouts({
      athlete_ids: athleteIds,
      scheduled_dates: dates,
      sport_id: sportId,
      workout_type: workoutType,
      title: title.trim(),
      purpose: purpose.trim() || null,
      target_rpe: targetRpe,
      description: description.trim() || null,
      steps,
    });
    setSaving(false);
    if (!result.success) {
      setError(result.error ?? "Failed to assign workout");
      return;
    }
    setSuccess(`Assigned ${result.count ?? 0} workout(s)`);
    if (athleteIds.length === 1) {
      navigate(`/coach/athletes/${athleteIds[0]}`);
    } else {
      navigate("/planning");
    }
  }

  async function handleSaveTemplate() {
    setError(null);
    setSuccess(null);
    if (!title.trim()) {
      setError("Title is required");
      return;
    }
    if (!sportId) {
      setError("Select a sport");
      return;
    }
    if (steps.length === 0) {
      setError("Add at least one step");
      return;
    }
    for (const item of steps) {
      if (!isRepeatBlock(item)) {
        const err = validateWorkoutStepDuration(item);
        if (err) {
          setError(err);
          return;
        }
      } else {
        for (const step of item.steps) {
          const err = validateWorkoutStepDuration(step);
          if (err) {
            setError(err);
            return;
          }
        }
      }
    }

    setSaving(true);
    const result = await createWorkoutTemplate({
      sport_id: sportId,
      workout_type: workoutType,
      title: title.trim(),
      purpose: purpose.trim() || null,
      target_rpe: targetRpe,
      description: description.trim() || null,
      steps,
    });
    setSaving(false);
    if (!result.success) {
      setError(result.error ?? "Failed to save template");
      return;
    }
    setSuccess("Template saved");
  }

  if (loading) return <p className="muted">Loading builder…</p>;

  if (sports.length === 0) {
    return (
      <p className="error">
        No running or cycling sports available. Add sports in the athlete performance profile first.
      </p>
    );
  }

  const selectedItem = selectedIndex != null ? steps[selectedIndex] ?? null : null;

  return (
    <div className="stack builder-page">
      <p>
        <Link to={mode === "template" ? "/templates" : "/planning"}>← Back</Link>
      </p>

      <IntentBar
        purpose={purpose}
        sportId={sportId}
        sports={sports}
        workoutType={workoutType}
        targetRpe={targetRpe}
        title={title}
        onPurposeChange={setPurpose}
        onSportChange={setSportId}
        onWorkoutTypeChange={setWorkoutType}
        onTargetRpeChange={setTargetRpe}
        onTitleChange={setTitle}
      />

      {primaryAthleteId > 0 && athleteIds.length > 1 && (
        <p className="muted">
          Zone targets are based on the primary selected athlete’s profile.
        </p>
      )}

      <div className="builder-panes">
        <LibraryPane
          sportCode={sportCode}
          onAddStep={(type: StepType) => {
            setSteps([...steps, defaultStepForType(type)]);
            setSelectedIndex(steps.length);
          }}
          onAddRepeat={() => {
            setSteps([...steps, defaultRepeatBlock()]);
            setSelectedIndex(steps.length);
          }}
          onApplyBuiltin={applyBuiltin}
          onApplySaved={applySavedFromLibrary}
        />
        <CanvasPane
          steps={steps}
          sportCode={sportCode}
          selectedIndex={selectedIndex}
          durationMin={rollups.durationMin}
          distanceM={rollups.distanceM}
          onSelect={setSelectedIndex}
          onReorder={(next) => {
            setSteps(next);
            setSelectedIndex(null);
          }}
        />
        <InspectorPane
          item={selectedItem}
          sportCode={sportCode}
          zones={zones}
          profile={profile}
          onChange={updateSelected}
          onRemove={removeSelected}
          onDuplicate={duplicateSelected}
        />
      </div>

      <AssignFooter
        mode={mode}
        athleteIds={athleteIds}
        dates={dates}
        description={description}
        saving={saving}
        error={error}
        success={success}
        onAthleteIdsChange={setAthleteIds}
        onDatesChange={setDates}
        onDescriptionChange={setDescription}
        onAssign={handlePrimaryAction}
        onSaveTemplate={handleSaveTemplate}
        onCancel={() => navigate(-1)}
      />
    </div>
  );
}

export function NewWorkoutBuilderPage() {
  return <CoachWorkoutBuilderPage mode="create" />;
}

export function EditWorkoutBuilderPage() {
  return <CoachWorkoutBuilderPage mode="edit" />;
}

export function TemplateBuilderPage() {
  return <CoachWorkoutBuilderPage mode="template" />;
}
