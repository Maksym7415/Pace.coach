import { ActivitiesView } from "../activities/ActivitiesView";
import { SettingsTab } from "./tabs/SettingsTab";

/** Athlete activities workspace (calendar-first + list). */
export function ActivitiesPage() {
  return <ActivitiesView scope={{ type: "self" }} />;
}

/** Athlete settings (Strava + profile link). */
export function AthleteSettingsPage() {
  return <SettingsTab />;
}
