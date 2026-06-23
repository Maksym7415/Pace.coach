const MAX_VISIBLE_EVENTS = 3;

type CalendarEventChipProps = {
  label: string;
  className: string;
};

export function CalendarEventChip({ label, className }: CalendarEventChipProps) {
  return (
    <span className={`calendar-event-chip ${className}`} title={label}>
      {label}
    </span>
  );
}

export function CalendarDayEvents({
  workouts,
  activities,
}: {
  workouts: { id: number; title: string; status: string }[];
  activities: { id: number; name: string }[];
}) {
  const events: { key: string; label: string; className: string }[] = [
    ...workouts.map((w) => ({
      key: `w-${w.id}`,
      label: w.title,
      className: `chip-workout status-${w.status}`,
    })),
    ...activities.map((a) => ({
      key: `a-${a.id}`,
      label: a.name,
      className: "chip-activity",
    })),
  ];

  const visible = events.slice(0, MAX_VISIBLE_EVENTS);
  const overflow = events.length - visible.length;

  if (events.length === 0) return null;

  return (
    <div className="calendar-events">
      {visible.map((event) => (
        <CalendarEventChip key={event.key} label={event.label} className={event.className} />
      ))}
      {overflow > 0 && <span className="calendar-event-more">+{overflow} more</span>}
    </div>
  );
}
