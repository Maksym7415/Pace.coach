import { useEffect, useState } from "react";
import {
  formatPaceValue,
  getAthleteSportProfile,
  listAthleteSports,
  listAthleteZones,
  type AthleteSport,
  type SportProfile,
  type Zone,
} from "../../athlete-profile/api";
import { Chip, MetricBar, SectionBox, SectionRow } from "../../shared/PageChrome";
import { CoachAthleteProfileSection } from "../CoachAthleteProfileSection";
import { useAthleteWorkspace } from "./AthleteWorkspaceLayout";
import { mockPerformanceTrends, type MockTrendPoint } from "./mockAthleteContext";

const TREND_CARDS: Array<{
  key: keyof ReturnType<typeof mockPerformanceTrends>;
  title: string;
  hint: string;
}> = [
  { key: "fitness", title: "Fitness", hint: "Is fitness building?" },
  { key: "efficiency", title: "Efficiency", hint: "More output from same effort?" },
  { key: "trainingLoad", title: "Training Load", hint: "Is load sustainable?" },
  { key: "raceReadiness", title: "Race Readiness", hint: "On track for the goal?" },
];

export function AthletePerformancePage() {
  const { athleteId } = useAthleteWorkspace();
  const trends = mockPerformanceTrends(athleteId);

  const [sports, setSports] = useState<AthleteSport[]>([]);
  const [profile, setProfile] = useState<SportProfile | null>(null);
  const [zones, setZones] = useState<Zone[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    listAthleteSports(athleteId).then(async (sportsResult) => {
      if (cancelled) return;
      if (!sportsResult.success) {
        setError(sportsResult.error ?? "Failed to load sports");
        setSports([]);
        setProfile(null);
        setZones([]);
        setLoading(false);
        return;
      }
      const list = sportsResult.sports ?? [];
      setSports(list);
      const primary = list.find((s) => s.is_primary) ?? list[0];
      if (!primary) {
        setProfile(null);
        setZones([]);
        setLoading(false);
        return;
      }
      const [profileResult, zonesResult] = await Promise.all([
        getAthleteSportProfile(athleteId, primary.sport.id),
        listAthleteZones(athleteId, primary.sport.id),
      ]);
      if (cancelled) return;
      setProfile(profileResult.success ? profileResult.profile ?? null : null);
      setZones(zonesResult.success ? zonesResult.zones ?? [] : []);
      if (!profileResult.success && profileResult.error !== "Sport profile not found") {
        setError(profileResult.error ?? null);
      } else {
        setError(null);
      }
      setLoading(false);
    });
    return () => {
      cancelled = true;
    };
  }, [athleteId]);

  return (
    <div className="grid gap-3">
      {TREND_CARDS.map((card) => (
        <SectionBox key={card.key} label={card.title} note={card.hint}>
          <div className="mb-2">
            <Chip className="border-amber-200 bg-amber-50 text-amber-700">Demo</Chip>
          </div>
          <TrendSparkline points={trends[card.key]} />
        </SectionBox>
      ))}

      <SectionBox label="Thresholds & zones" note="Live athlete profile">
        {loading && <p className="text-sm text-slate-500">Loading profile…</p>}
        {error && <p className="text-sm text-red-600">{error}</p>}
        {!loading && sports.length === 0 && (
          <p className="text-sm text-slate-500">No sports configured for this athlete.</p>
        )}
        {!loading && profile && (
          <SectionRow cols={2}>
            <dl className="detail-list text-sm">
              <div>
                <dt>Sport</dt>
                <dd>{profile.sport.name}</dd>
              </div>
              <div>
                <dt>Threshold pace</dt>
                <dd>{formatPaceValue(profile.threshold_pace_sec_per_km, "km")}</dd>
              </div>
              <div>
                <dt>Threshold HR</dt>
                <dd>{profile.threshold_hr != null ? `${profile.threshold_hr} bpm` : "—"}</dd>
              </div>
              <div>
                <dt>FTP</dt>
                <dd>{profile.ftp_watts != null ? `${profile.ftp_watts} W` : "—"}</dd>
              </div>
            </dl>
            <div>
              <div className="mb-1 text-[11px] uppercase text-slate-400">Zones</div>
              {zones.length === 0 ? (
                <p className="text-sm text-slate-500">No zones set.</p>
              ) : (
                <ul className="divide-y divide-slate-100 text-xs">
                  {zones.map((z) => (
                    <li key={z.id} className="flex justify-between gap-2 py-1">
                      <span>
                        {z.zone_category} · {z.zone_name}
                      </span>
                      <span className="text-slate-500">
                        {z.min_value}–{z.max_value}
                      </span>
                    </li>
                  ))}
                </ul>
              )}
            </div>
          </SectionRow>
        )}
      </SectionBox>

      <CoachAthleteProfileSection athleteId={athleteId} />
    </div>
  );
}

function TrendSparkline({ points }: { points: MockTrendPoint[] }) {
  const latest = points[points.length - 1]?.value ?? null;
  return (
    <div className="space-y-2">
      <div className="flex h-16 items-end gap-1">
        {points.map((p) => (
          <div key={p.label} className="flex h-full flex-1 flex-col items-center justify-end gap-1">
            <div
              className="w-full rounded-sm bg-slate-400"
              style={{ height: `${Math.max(8, p.value)}%` }}
              title={`${p.label}: ${p.value}`}
            />
            <span className="text-[9px] text-slate-400">{p.label}</span>
          </div>
        ))}
      </div>
      <MetricBar label="Now" value={latest} />
    </div>
  );
}
