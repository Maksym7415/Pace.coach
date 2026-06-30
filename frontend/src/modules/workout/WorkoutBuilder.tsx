import {
  DndContext,
  closestCenter,
  type DragEndEvent,
  KeyboardSensor,
  PointerSensor,
  useSensor,
  useSensors,
} from "@dnd-kit/core";
import {
  SortableContext,
  arrayMove,
  sortableKeyboardCoordinates,
  useSortable,
  verticalListSortingStrategy,
} from "@dnd-kit/sortable";
import { CSS } from "@dnd-kit/utilities";
import { FormEvent, useEffect, useMemo, useState } from "react";
import { listAthleteSports, type AthleteSport } from "../athlete-profile/api";
import { WORKOUT_TYPES, type Workout, type WorkoutType } from "../training/api";
import { todayIso } from "../shared/dates";
import { RepeatBlockEditor } from "./RepeatBlockEditor";
import { defaultRepeatBlock, defaultStepForType, StepTypePicker } from "./StepTypePicker";
import { templatesForSport } from "./templates";
import {
  BUILDER_SPORT_CODES,
  isRepeatBlock,
  type StepType,
  type WorkoutStepItem,
} from "./types";
import { useAthleteZones } from "./useAthleteZones";
import { WorkoutPreview } from "./WorkoutPreview";
import { WorkoutStepCard } from "./WorkoutStepCard";
import { normalizeWorkoutSteps, validateWorkoutStepDuration } from "./normalize";
import { computeRollups } from "./rollup";

type WorkoutBuilderProps = {
  athleteId: number;
  mode: "create" | "edit";
  initialWorkout?: Workout | null;
  submitLabel?: string;
  onSubmit: (payload: {
    scheduled_date: string;
    sport_id: number;
    workout_type: WorkoutType;
    title: string;
    description: string | null;
    steps: WorkoutStepItem[];
  }) => Promise<{ success: boolean; error?: string }>;
  onCancel?: () => void;
};

type SortableItemProps = {
  id: string;
  children: (dragHandle: React.ReactNode) => React.ReactNode;
};

function SortableItem({ id, children }: SortableItemProps) {
  const { attributes, listeners, setNodeRef, transform, transition, isDragging } = useSortable({
    id,
  });
  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
    opacity: isDragging ? 0.6 : 1,
  };
  const dragHandle = (
    <button type="button" className="drag-handle secondary" {...attributes} {...listeners}>
      ⠿
    </button>
  );
  return (
    <div ref={setNodeRef} style={style}>
      {children(dragHandle)}
    </div>
  );
}

export function WorkoutBuilder({
  athleteId,
  mode,
  initialWorkout,
  submitLabel,
  onSubmit,
  onCancel,
}: WorkoutBuilderProps) {
  const [athleteSports, setAthleteSports] = useState<AthleteSport[]>([]);
  const [loadingSports, setLoadingSports] = useState(true);
  const [scheduledDate, setScheduledDate] = useState(initialWorkout?.scheduled_date ?? todayIso());
  const [sportId, setSportId] = useState<number | null>(initialWorkout?.sport_id ?? null);
  const [workoutType, setWorkoutType] = useState<WorkoutType>(
    initialWorkout?.workout_type ?? "easy",
  );
  const [title, setTitle] = useState(initialWorkout?.title ?? "");
  const [description, setDescription] = useState(initialWorkout?.description ?? "");
  const [steps, setSteps] = useState<WorkoutStepItem[]>(() =>
    normalizeWorkoutSteps((initialWorkout?.steps as WorkoutStepItem[] | null) ?? []),
  );
  const [templateId, setTemplateId] = useState("");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const sensors = useSensors(
    useSensor(PointerSensor),
    useSensor(KeyboardSensor, { coordinateGetter: sortableKeyboardCoordinates }),
  );

  useEffect(() => {
    listAthleteSports(athleteId).then((result) => {
      if (result.success && result.sports) {
        const builderSports = result.sports.filter((s) =>
          BUILDER_SPORT_CODES.has(s.sport.code),
        );
        setAthleteSports(builderSports);
        setSportId((current) => {
          if (current) return current;
          if (builderSports.length === 0) return null;
          const primary = builderSports.find((s) => s.is_primary) ?? builderSports[0];
          return primary.sport.id;
        });
      }
      setLoadingSports(false);
    });
  }, [athleteId]);

  const selectedSport = athleteSports.find((s) => s.sport.id === sportId)?.sport ?? null;
  const sportCode = selectedSport?.code ?? null;
  const { zones, profile } = useAthleteZones(athleteId, sportId);
  const rollups = useMemo(() => computeRollups(steps), [steps]);
  const sortableIds = steps.map((_, index) => `step-${index}`);
  const templates = templatesForSport(sportCode);

  function moveStep(index: number, direction: -1 | 1) {
    const next = index + direction;
    if (next < 0 || next >= steps.length) return;
    setSteps(arrayMove(steps, index, next));
  }

  function handleDragEnd(event: DragEndEvent) {
    const { active, over } = event;
    if (!over || active.id === over.id) return;
    const oldIndex = sortableIds.indexOf(String(active.id));
    const newIndex = sortableIds.indexOf(String(over.id));
    if (oldIndex >= 0 && newIndex >= 0) {
      setSteps(arrayMove(steps, oldIndex, newIndex));
    }
  }

  function applyTemplate(id: string) {
    const template = templates.find((t) => t.id === id);
    if (!template) return;
    if (steps.length > 0 && !window.confirm("Replace current steps with this template?")) {
      setTemplateId("");
      return;
    }
    setTitle(template.title);
    setWorkoutType(template.workoutType);
    setSteps(normalizeWorkoutSteps(structuredClone(template.steps)));
    setTemplateId(id);
  }

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setError(null);

    const trimmedTitle = title.trim();
    if (!trimmedTitle) {
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
    const result = await onSubmit({
      scheduled_date: scheduledDate,
      sport_id: sportId,
      workout_type: workoutType,
      title: trimmedTitle,
      description: description.trim() || null,
      steps,
    });
    setSaving(false);
    if (!result.success) {
      setError(result.error ?? "Failed to save workout");
    }
  }

  if (loadingSports) {
    return <p className="muted">Loading sports…</p>;
  }

  if (athleteSports.length === 0) {
    return (
      <p className="error">
        Athlete has no running or cycling sports enrolled. Add sports in the performance profile
        first.
      </p>
    );
  }

  return (
    <form className="card stack workout-builder" onSubmit={handleSubmit}>
      <h3>{mode === "create" ? "Schedule workout" : "Edit workout"}</h3>

      <div className="form-grid">
        <label>
          Date
          <input
            type="date"
            value={scheduledDate}
            onChange={(e) => setScheduledDate(e.target.value)}
            required
          />
        </label>
        <label>
          Sport
          <select
            value={sportId ?? ""}
            onChange={(e) => setSportId(Number(e.target.value))}
            required
          >
            {athleteSports.map((item) => (
              <option key={item.sport.id} value={item.sport.id}>
                {item.sport.name}
              </option>
            ))}
          </select>
        </label>
        <label>
          Workout type
          <select
            value={workoutType}
            onChange={(e) => setWorkoutType(e.target.value as WorkoutType)}
          >
            {WORKOUT_TYPES.map((type) => (
              <option key={type.value} value={type.value}>
                {type.label}
              </option>
            ))}
          </select>
        </label>
        <label>
          Title
          <input value={title} onChange={(e) => setTitle(e.target.value)} required />
        </label>
      </div>

      <label>
        Coach notes
        <textarea
          rows={2}
          value={description}
          onChange={(e) => setDescription(e.target.value)}
          placeholder="Optional notes for the athlete"
        />
      </label>

      {templates.length > 0 && (
        <label className="template-picker">
          Start from template
          <select value={templateId} onChange={(e) => applyTemplate(e.target.value)}>
            <option value="">— Select template —</option>
            {templates.map((t) => (
              <option key={t.id} value={t.id}>
                {t.label}
              </option>
            ))}
          </select>
        </label>
      )}

      <StepTypePicker
        sportCode={sportCode}
        onAddStep={(type: StepType) => setSteps([...steps, defaultStepForType(type)])}
        onAddRepeat={() => setSteps([...steps, defaultRepeatBlock()])}
      />

      <DndContext sensors={sensors} collisionDetection={closestCenter} onDragEnd={handleDragEnd}>
        <SortableContext items={sortableIds} strategy={verticalListSortingStrategy}>
          <div className="stack">
            {steps.map((item, index) => {
              const id = `step-${index}`;
              return (
                <SortableItem key={id} id={id}>
                  {(dragHandle) =>
                    isRepeatBlock(item) ? (
                      <RepeatBlockEditor
                        block={item}
                        sportCode={sportCode}
                        zones={zones}
                        profile={profile}
                        dragHandle={dragHandle}
                        onChange={(updated) => {
                          const next = [...steps];
                          next[index] = updated;
                          setSteps(next);
                        }}
                        onRemove={() => setSteps(steps.filter((_, i) => i !== index))}
                        onMoveUp={index > 0 ? () => moveStep(index, -1) : undefined}
                        onMoveDown={index < steps.length - 1 ? () => moveStep(index, 1) : undefined}
                      />
                    ) : (
                      <WorkoutStepCard
                        step={item}
                        sportCode={sportCode}
                        zones={zones}
                        profile={profile}
                        dragHandle={dragHandle}
                        onChange={(updated) => {
                          const next = [...steps];
                          next[index] = updated;
                          setSteps(next);
                        }}
                        onRemove={() => setSteps(steps.filter((_, i) => i !== index))}
                        onMoveUp={index > 0 ? () => moveStep(index, -1) : undefined}
                        onMoveDown={index < steps.length - 1 ? () => moveStep(index, 1) : undefined}
                      />
                    )
                  }
                </SortableItem>
              );
            })}
          </div>
        </SortableContext>
      </DndContext>

      <WorkoutPreview
        title={title}
        steps={steps}
        sportCode={sportCode}
        durationMin={rollups.durationMin}
        distanceM={rollups.distanceM}
      />

      {error && <p className="error">{error}</p>}

      <div className="row-between">
        {onCancel && (
          <button type="button" className="secondary" onClick={onCancel} disabled={saving}>
            Cancel
          </button>
        )}
        <button type="submit" disabled={saving}>
          {saving ? "Saving…" : (submitLabel ?? (mode === "create" ? "Add to calendar" : "Save changes"))}
        </button>
      </div>
    </form>
  );
}
