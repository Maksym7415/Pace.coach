import { useCallback } from "react";
import { getAthleteBaselines } from "../athlete-profile/api";
import { RecoveryBaselinesSection } from "../athlete-profile/RecoveryBaselinesSection";

type CoachAthleteProfileSectionProps = {
  athleteId: number;
};

export function CoachAthleteProfileSection({ athleteId }: CoachAthleteProfileSectionProps) {
  const getBaselines = useCallback(() => getAthleteBaselines(athleteId), [athleteId]);

  return (
    <RecoveryBaselinesSection
      athleteId={athleteId}
      coachMode
      getBaselines={getBaselines}
    />
  );
}
