import { Chip, MetricBar, SectionBox, SectionRow } from "../../shared/PageChrome";
import { AthleteTodayRecoverySection } from "../AthleteTodayRecoverySection";
import { useAthleteWorkspace } from "./AthleteWorkspaceLayout";
import { mockRecoveryTrends } from "./mockAthleteContext";

export function AthleteRecoveryPage() {
  const { athleteId } = useAthleteWorkspace();
  const trends = mockRecoveryTrends(athleteId);

  return (
    <div className="grid gap-3">
      <SectionBox label="Today" note="Readiness snapshot">
        <AthleteTodayRecoverySection athleteId={athleteId} embedded />
      </SectionBox>

      <SectionBox label="Trends" note="Rolling recovery signals">
        <div className="mb-2">
          <Chip className="border-amber-200 bg-amber-50 text-amber-700">Demo</Chip>
        </div>
        <p className="mb-3 text-[11px] text-slate-400">
          Coach recovery history is not on the backend yet — showing demo trends.
        </p>
        <SectionRow cols={3}>
          <div>
            <div className="mb-2 text-[11px] uppercase text-slate-400">Readiness</div>
            {trends.map((t) => (
              <MetricBar key={`r-${t.label}`} label={t.label} value={t.readiness} />
            ))}
          </div>
          <div>
            <div className="mb-2 text-[11px] uppercase text-slate-400">HRV</div>
            {trends.map((t) => (
              <MetricBar key={`h-${t.label}`} label={t.label} value={t.hrv} max={100} />
            ))}
          </div>
          <div>
            <div className="mb-2 text-[11px] uppercase text-slate-400">Sleep (h)</div>
            {trends.map((t) => (
              <MetricBar key={`s-${t.label}`} label={t.label} value={t.sleepHours} max={10} />
            ))}
          </div>
        </SectionRow>
      </SectionBox>
    </div>
  );
}
