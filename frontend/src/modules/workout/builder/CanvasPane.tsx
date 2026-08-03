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
import { formatStepSummary } from "../format";
import type { WorkoutStepItem } from "../types";
import { isRepeatBlock, stepTypeLabel } from "../types";

type CanvasPaneProps = {
  steps: WorkoutStepItem[];
  sportCode: string | null;
  selectedIndex: number | null;
  durationMin: number | null;
  distanceM: number | null;
  onSelect: (index: number) => void;
  onReorder: (steps: WorkoutStepItem[]) => void;
};

function SortableChip({
  id,
  selected,
  children,
  onSelect,
}: {
  id: string;
  selected: boolean;
  children: React.ReactNode;
  onSelect: () => void;
}) {
  const { attributes, listeners, setNodeRef, transform, transition, isDragging } = useSortable({
    id,
  });
  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
    opacity: isDragging ? 0.6 : 1,
  };

  return (
    <div
      ref={setNodeRef}
      style={style}
      className={`builder-canvas-chip ${selected ? "selected" : ""}`}
      onClick={onSelect}
    >
      <button type="button" className="drag-handle secondary" {...attributes} {...listeners}>
        ⠿
      </button>
      <div className="builder-canvas-chip-body">{children}</div>
    </div>
  );
}

function sectionForIndex(steps: WorkoutStepItem[], index: number): string | null {
  const item = steps[index];
  if (!item) return null;
  if (isRepeatBlock(item)) return index === 0 || !isRepeatBlock(steps[index - 1]!) ? "Main set" : null;
  if (item.type === "warmup") {
    const isFirstWarmup = !steps.slice(0, index).some((s) => !isRepeatBlock(s) && s.type === "warmup");
    return isFirstWarmup ? "Warmup" : null;
  }
  if (item.type === "cooldown") {
    const isFirstCooldown = !steps
      .slice(0, index)
      .some((s) => !isRepeatBlock(s) && s.type === "cooldown");
    return isFirstCooldown ? "Cooldown" : null;
  }
  if (!isRepeatBlock(item) && (item.type === "run" || item.type === "ride" || item.type === "interval")) {
    const prev = steps[index - 1];
    if (!prev || isRepeatBlock(prev) || prev.type === "warmup") return "Main set";
  }
  return null;
}

export function CanvasPane({
  steps,
  sportCode,
  selectedIndex,
  durationMin,
  distanceM,
  onSelect,
  onReorder,
}: CanvasPaneProps) {
  const sensors = useSensors(
    useSensor(PointerSensor),
    useSensor(KeyboardSensor, { coordinateGetter: sortableKeyboardCoordinates }),
  );
  const sortableIds = steps.map((_, index) => `step-${index}`);

  function handleDragEnd(event: DragEndEvent) {
    const { active, over } = event;
    if (!over || active.id === over.id) return;
    const oldIndex = sortableIds.indexOf(String(active.id));
    const newIndex = sortableIds.indexOf(String(over.id));
    if (oldIndex >= 0 && newIndex >= 0) {
      onReorder(arrayMove(steps, oldIndex, newIndex));
    }
  }

  return (
    <div className="builder-pane builder-canvas card stack">
      <div className="row-between">
        <h3>Canvas · Structure</h3>
        <span className="muted">warmup → main → cooldown</span>
      </div>
      {steps.length === 0 ? (
        <p className="muted">Add blocks from the library to structure the workout.</p>
      ) : (
        <DndContext sensors={sensors} collisionDetection={closestCenter} onDragEnd={handleDragEnd}>
          <SortableContext items={sortableIds} strategy={verticalListSortingStrategy}>
            <div className="stack">
              {steps.map((item, index) => {
                const section = sectionForIndex(steps, index);
                const id = `step-${index}`;
                return (
                  <div key={id} className="stack">
                    {section && <div className="builder-section-label">{section}</div>}
                    <SortableChip
                      id={id}
                      selected={selectedIndex === index}
                      onSelect={() => onSelect(index)}
                    >
                      {isRepeatBlock(item) ? (
                        <>
                          <strong>Repeat × {item.repeatCount}</strong>
                          <span className="muted">
                            {item.steps.map((s) => stepTypeLabel(s.type)).join(" → ")}
                          </span>
                        </>
                      ) : (
                        <>
                          <strong>{stepTypeLabel(item.type)}</strong>
                          <span className="muted">{formatStepSummary(item, sportCode)}</span>
                        </>
                      )}
                    </SortableChip>
                  </div>
                );
              })}
            </div>
          </SortableContext>
        </DndContext>
      )}

      <div className="builder-canvas-rollup muted">
        Total{" "}
        {durationMin != null ? `${durationMin} min` : "—"}
        {distanceM != null ? ` · ${(distanceM / 1000).toFixed(1)} km` : ""}
      </div>
    </div>
  );
}
