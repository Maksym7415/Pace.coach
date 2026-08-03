const MAX_VISIBLE_EVENTS = 3;

type CalendarEventChipProps = {
  label: string;
  className: string;
  onClick?: () => void;
};

export function CalendarEventChip({ label, className, onClick }: CalendarEventChipProps) {
  if (onClick) {
    return (
      <button
        type="button"
        className={`calendar-event-chip ${className}`}
        title={label}
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
    <span className={`calendar-event-chip ${className}`} title={label}>
      {label}
    </span>
  );
}

export function CalendarDayEvents({
  workouts,
  activities,
  onWorkoutClick,
  onActivityClick,
}: {
  workouts: { id: number; title: string; status: string }[];
  activities: { id: number; name: string }[];
  onWorkoutClick?: (workoutId: number) => void;
  onActivityClick?: (activityId: number) => void;
}) {
  const events: { key: string; label: string; className: string; onClick?: () => void }[] = [
    ...workouts.map((w) => ({
      key: `w-${w.id}`,
      label: w.title,
      className: `chip-workout status-${w.status}`,
      onClick:
        onWorkoutClick && w.status !== "completed"
          ? () => onWorkoutClick(w.id)
          : undefined,
    })),
    ...activities.map((a) => ({
      key: `a-${a.id}`,
      label: a.name,
      className: "chip-activity",
      onClick: onActivityClick ? () => onActivityClick(a.id) : undefined,
    })),
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
          onClick={event.onClick}
        />
      ))}
      {overflow > 0 && <span className="calendar-event-more">+{overflow} more</span>}
    </div>
  );
}
