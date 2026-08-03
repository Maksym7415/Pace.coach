import { toDateKey, toIsoDate } from "../shared/dates";

export type MonthGridCell = {
  iso: string;
  inMonth: boolean;
};

/** Monday-first month grid including muted prev/next month days. */
export function buildMonthGrid(year: number, month: number): MonthGridCell[] {
  const first = new Date(year, month, 1);
  const lead = (first.getDay() + 6) % 7; // Monday = 0
  const daysInMonth = new Date(year, month + 1, 0).getDate();
  const prevMonthLastDay = new Date(year, month, 0).getDate();
  const prevMonth = month === 0 ? 11 : month - 1;
  const prevYear = month === 0 ? year - 1 : year;
  const nextMonth = month === 11 ? 0 : month + 1;
  const nextYear = month === 11 ? year + 1 : year;

  const cells: MonthGridCell[] = [];

  for (let i = lead - 1; i >= 0; i -= 1) {
    cells.push({
      iso: toIsoDate(prevYear, prevMonth, prevMonthLastDay - i),
      inMonth: false,
    });
  }

  for (let day = 1; day <= daysInMonth; day += 1) {
    cells.push({ iso: toIsoDate(year, month, day), inMonth: true });
  }

  let nextDay = 1;
  while (cells.length % 7 !== 0) {
    cells.push({
      iso: toIsoDate(nextYear, nextMonth, nextDay),
      inMonth: false,
    });
    nextDay += 1;
  }

  return cells;
}

export function groupByDate<T extends { date?: string; scheduled_date?: string }>(
  items: T[],
  dateKey: "date" | "scheduled_date",
): Map<string, T[]> {
  const map = new Map<string, T[]>();
  for (const item of items) {
    const raw =
      dateKey === "date"
        ? (item as { date: string }).date
        : (item as { scheduled_date: string }).scheduled_date;
    const iso = toDateKey(raw);
    const list = map.get(iso) ?? [];
    list.push(item);
    map.set(iso, list);
  }
  return map;
}

export function unlinkedActivitiesForDay<
  TWorkout extends { activity_id: number | null },
  TActivity extends { id: number },
>(workouts: TWorkout[], activities: TActivity[]): TActivity[] {
  const linkedIds = new Set(
    workouts.map((w) => w.activity_id).filter((id): id is number => id !== null),
  );
  return activities.filter((a) => !linkedIds.has(a.id));
}
