import { MonthCalendar } from "../../calendar/MonthCalendar";

type CoachMonthCalendarProps = {
  athleteId: number;
  refreshKey?: number;
  onCalendarChanged?: () => void;
};

/** Thin wrapper preserving coach athlete-detail call sites. */
export function CoachMonthCalendar({
  athleteId,
  refreshKey = 0,
  onCalendarChanged,
}: CoachMonthCalendarProps) {
  return (
    <MonthCalendar
      scope={{ type: "athlete", athleteId }}
      showWorkouts
      showActivities
      coachPlanning={{ enabled: true, refreshKey, onCalendarChanged }}
    />
  );
}
