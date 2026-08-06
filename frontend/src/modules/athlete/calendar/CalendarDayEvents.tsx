import type { Activity } from "../../activities/api";
import type { Workout } from "../../training/api";
import {
  chipClassForStatus,
  displayStatusForActivity,
  displayStatusForWorkout,
  STATUS_BADGE_LABEL,
  type CalendarDisplayStatus,
} from "../../calendar/eventStatus";

const MAX_VISIBLE_EVENTS = 3;

type CalendarEventChipProps = {
  label: string;
  className: string;
  title?: string;
  onClick?: () => void;
};

export function CalendarEventChip({ label, className, title, onClick }: CalendarEventChipProps) {
  if (onClick) {
    return (
      <button
        type="button"
        className={`calendar-event-chip ${className}`}
        title={title ?? label}
        onClick={(e) => {
          e.stopPropagation();
          onClick();
        }}
      >
        {label}
      </button>
    );
  }

  return (
    <span className={`calendar-event-chip ${className}`} title={title ?? label}>
      {label}
    </span>
  );
}

export function CalendarDayEvents({
  workouts,
  activities,
  today,
  onWorkoutClick,
  onActivityClick,
}: {
  workouts: Workout[];
  activities: Activity[];
  today: string;
  onWorkoutClick?: (workoutId: number) => void;
  onActivityClick?: (activityId: number) => void;
}) {
  const events: {
    key: string;
    label: string;
    className: string;
    title: string;
    onClick?: () => void;
  }[] = [
    ...workouts.map((w) => {
      const status: CalendarDisplayStatus = displayStatusForWorkout(w, today);
      return {
        key: `w-${w.id}`,
        label: w.title,
        className: chipClassForStatus(status),
        title: `${w.title} · ${STATUS_BADGE_LABEL[status]}`,
        onClick: onWorkoutClick ? () => onWorkoutClick(w.id) : undefined,
      };
    }),
    ...activities.map((a) => {
      const status = displayStatusForActivity();
      return {
        key: `a-${a.id}`,
        label: a.name,
        className: chipClassForStatus(status),
        title: `${a.name} · ${STATUS_BADGE_LABEL[status]}`,
        onClick: onActivityClick ? () => onActivityClick(a.id) : undefined,
      };
    }),
  ];

  const visible = events.slice(0, MAX_VISIBLE_EVENTS);
  const overflow = events.length - visible.length;

  if (events.length === 0) return null;

  return (
    <div className="calendar-events">
      {visible.map((event) => (
        <CalendarEventChip
          key={event.key}
          label={event.label}
          className={event.className}
          title={event.title}
          onClick={event.onClick}
        />
      ))}
      {overflow > 0 && <span className="calendar-event-more">+{overflow} more</span>}
    </div>
  );
}
