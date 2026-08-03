import { ActivityList } from "../athlete/activities/ActivityList";
import { SettingsTab } from "../athlete/tabs/SettingsTab";

/** Athlete activities list (displaced from former dashboard tabs). */
export function ActivitiesPage() {
  return (
    <div className="stack">
      <ActivityList />
    </div>
  );
}

/** Athlete settings (Strava + profile link). */
export function AthleteSettingsPage() {
  return <SettingsTab />;
}
