/** Demo fixtures for surfaces without backend support (mesocycle, trend charts). */

const BLOCKS = [
  { name: "Marathon block", week: 4, weeksTotal: 12, goal: "Sub-3:30 marathon" },
  { name: "Base building", week: 6, weeksTotal: 8, goal: "Aerobic volume" },
  { name: "Speed focus", week: 2, weeksTotal: 6, goal: "5K PR prep" },
  { name: "Recovery block", week: 1, weeksTotal: 3, goal: "Absorb load" },
] as const;

export type MockMesocycle = {
  name: string;
  week: number;
  weeksTotal: number;
  goal: string;
  progressPct: number;
  subtitle: string;
};

export function mockMesocycle(athleteId: number): MockMesocycle {
  const block = BLOCKS[Math.abs(athleteId) % BLOCKS.length];
  const progressPct = Math.round((block.week / block.weeksTotal) * 100);
  return {
    name: block.name,
    week: block.week,
    weeksTotal: block.weeksTotal,
    goal: block.goal,
    progressPct,
    subtitle: `${block.name} · week ${block.week}`,
  };
}

export type MockTrendPoint = { label: string; value: number };

export type MockPerformanceTrends = {
  fitness: MockTrendPoint[];
  efficiency: MockTrendPoint[];
  trainingLoad: MockTrendPoint[];
  raceReadiness: MockTrendPoint[];
};

function series(seed: number, base: number, drift: number): MockTrendPoint[] {
  return Array.from({ length: 8 }, (_, i) => ({
    label: `W${i + 1}`,
    value: Math.max(20, Math.min(100, Math.round(base + i * drift + ((seed + i) % 5) - 2))),
  }));
}

export function mockPerformanceTrends(athleteId: number): MockPerformanceTrends {
  const seed = Math.abs(athleteId);
  return {
    fitness: series(seed, 55, 3),
    efficiency: series(seed + 1, 48, 2),
    trainingLoad: series(seed + 2, 62, -1),
    raceReadiness: series(seed + 3, 40, 4),
  };
}

export type MockRecoveryTrend = {
  label: string;
  readiness: number;
  hrv: number;
  sleepHours: number;
};

export function mockRecoveryTrends(athleteId: number): MockRecoveryTrend[] {
  const seed = Math.abs(athleteId);
  return Array.from({ length: 7 }, (_, i) => ({
    label: ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"][i],
    readiness: 50 + ((seed + i * 3) % 40),
    hrv: 40 + ((seed + i * 5) % 35),
    sleepHours: 6 + ((seed + i) % 4) * 0.5,
  }));
}
