import { ActivitiesView } from "../../activities/ActivitiesView";
import { useAthleteWorkspace } from "./AthleteWorkspaceLayout";

export function AthleteActivitiesPage() {
  const { athleteId, detail } = useAthleteWorkspace();

  return (
    <ActivitiesView
      scope={{ type: "athlete", athleteId }}
      heading={`${detail.athlete.name} · Activities`}
      subheading="Was it executed well?"
      coachPlanning
      coachMode
    />
  );
}
