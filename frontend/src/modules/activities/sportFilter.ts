export type SportFilterId = "run" | "bike" | "swim" | "other";

export const SPORT_FILTERS: { id: SportFilterId; label: string }[] = [
  { id: "run", label: "Run" },
  { id: "bike", label: "Bike" },
  { id: "swim", label: "Swim" },
  { id: "other", label: "Other" },
];

export function toSportFilterId(sportCode: string | null): SportFilterId {
  switch (sportCode) {
    case "running":
      return "run";
    case "cycling":
      return "bike";
    case "swimming":
      return "swim";
    default:
      return "other";
  }
}

export function activityMatchesSportFilter(
  activity: { sport_code: string | null },
  selected: SportFilterId[],
): boolean {
  if (selected.length === 0) return true;
  return selected.includes(toSportFilterId(activity.sport_code));
}
