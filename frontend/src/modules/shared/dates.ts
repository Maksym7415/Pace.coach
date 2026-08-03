export function toIsoDate(year: number, month: number, day: number): string {
  return `${year}-${String(month + 1).padStart(2, "0")}-${String(day).padStart(2, "0")}`;
}

/** Normalize API date/datetime strings to YYYY-MM-DD for map keys and comparisons. */
export function toDateKey(value: string): string {
  return value.slice(0, 10);
}

export function todayIso(): string {
  const d = new Date();
  return toIsoDate(d.getFullYear(), d.getMonth(), d.getDate());
}

/** Monday–Sunday week containing `iso` (local). */
export function weekBounds(iso: string): { start: string; end: string; days: string[] } {
  const [y, m, d] = toDateKey(iso).split("-").map(Number);
  const date = new Date(y, m - 1, d);
  const day = date.getDay(); // 0 Sun … 6 Sat
  const mondayOffset = day === 0 ? -6 : 1 - day;
  const monday = new Date(y, m - 1, d + mondayOffset);
  const days: string[] = [];
  for (let i = 0; i < 7; i++) {
    const cur = new Date(monday.getFullYear(), monday.getMonth(), monday.getDate() + i);
    days.push(toIsoDate(cur.getFullYear(), cur.getMonth(), cur.getDate()));
  }
  return { start: days[0], end: days[6], days };
}

export function addDaysIso(iso: string, delta: number): string {
  const [y, m, d] = toDateKey(iso).split("-").map(Number);
  const date = new Date(y, m - 1, d + delta);
  return toIsoDate(date.getFullYear(), date.getMonth(), date.getDate());
}

export function monthBounds(year: number, month: number): { start: string; end: string } {
  const daysInMonth = new Date(year, month + 1, 0).getDate();
  return {
    start: toIsoDate(year, month, 1),
    end: toIsoDate(year, month, daysInMonth),
  };
}

export function formatDate(iso: string): string {
  const [y, m, d] = toDateKey(iso).split("-").map(Number);
  return new Date(y, m - 1, d).toLocaleDateString(undefined, {
    weekday: "short",
    month: "short",
    day: "numeric",
  });
}

export function formatMonthYear(year: number, month: number): string {
  return new Date(year, month, 1).toLocaleDateString(undefined, { month: "long", year: "numeric" });
}
