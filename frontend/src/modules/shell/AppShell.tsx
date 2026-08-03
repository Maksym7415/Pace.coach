import { Link, useLocation } from "react-router-dom";
import type { ReactNode } from "react";
import { useAuth } from "../auth/AuthContext";
import type { UserRole } from "../shared/api";
import { cn } from "@/lib/utils";

type NavItem = {
  to: string;
  label: string;
  phase: string;
  question: string;
  match?: (path: string) => boolean;
};

const athleteNav: NavItem[] = [
  { to: "/today", label: "Today", phase: "Execute", question: "What should I do today?" },
  { to: "/plan", label: "Plan", phase: "Plan", question: "What's coming?" },
  {
    to: "/activities",
    label: "Activities",
    phase: "Analyze",
    question: "Was it executed well?",
    match: (path) => path.startsWith("/activities"),
  },
  {
    to: "/performance",
    label: "Performance",
    phase: "Analyze",
    question: "Am I improving?",
    match: (path) => path.startsWith("/performance") || path.startsWith("/athlete/profile"),
  },
  { to: "/recovery", label: "Recovery", phase: "Analyze", question: "Am I ready to train?" },
];

const coachNav: NavItem[] = [
  { to: "/today", label: "Today", phase: "Execute", question: "Who needs me today?" },
  {
    to: "/athletes",
    label: "Athletes",
    phase: "Manage",
    question: "Who am I coaching?",
    match: (path) => path.startsWith("/athletes") || path.startsWith("/coach/athletes"),
  },
  {
    to: "/planning",
    label: "Planning",
    phase: "Plan",
    question: "What should happen next?",
    match: (path) => path.startsWith("/planning"),
  },
  { to: "/activities", label: "Activities", phase: "Analyze", question: "Was it executed well?" },
  { to: "/analysis", label: "Analysis", phase: "Analyze", question: "Who needs intervention?" },
  {
    to: "/templates",
    label: "Templates",
    phase: "Plan",
    question: "Reusable building blocks",
    match: (path) => path.startsWith("/templates"),
  },
];

const activityHeader: NavItem = {
  to: "/activity",
  label: "Activity",
  phase: "Analyze",
  question: "Was this workout executed well?",
};

function isActive(item: NavItem, path: string): boolean {
  if (item.match) return item.match(path);
  return path === item.to || path.startsWith(`${item.to}/`);
}

function resolveNavRole(hasRole: (role: UserRole) => boolean, preferred: UserRole | null): UserRole {
  if (preferred && hasRole(preferred)) return preferred;
  if (hasRole("athlete")) return "athlete";
  if (hasRole("coach")) return "coach";
  return "athlete";
}

type AppShellProps = {
  children: ReactNode;
  viewRole: UserRole;
  onViewRoleChange?: (role: UserRole) => void;
};

export function AppShell({ children, viewRole, onViewRoleChange }: AppShellProps) {
  const { hasRole, logout } = useAuth();
  const location = useLocation();
  const path = location.pathname;

  const dualRole = hasRole("athlete") && hasRole("coach");
  const role = resolveNavRole(hasRole, dualRole ? viewRole : null);
  const nav = role === "coach" ? coachNav : athleteNav;

  const onActivity = path.startsWith("/activity/");
  const current = onActivity
    ? activityHeader
    : (nav.find((item) => isActive(item, path)) ?? nav[0]);

  return (
    <div className="flex min-h-screen bg-white text-slate-900">
      <aside className="flex w-60 shrink-0 flex-col border-r border-slate-200 bg-slate-50/80">
        <div className="px-5 py-5">
          <Link to="/today" className="block text-sm font-semibold tracking-tight text-slate-900">
            Pace<span className="text-slate-400">.coach</span>
          </Link>
          <p className="mt-0.5 text-[11px] uppercase tracking-wider text-slate-400">
            Plan · Execute · Analyze · Improve
          </p>
        </div>

        <nav className="flex-1 px-2">
          {nav.map((item) => {
            const selected = onActivity
              ? role === "athlete"
                ? item.to === "/activities"
                : item.to === "/today"
              : isActive(item, path);

            return (
              <Link
                key={item.to}
                to={item.to}
                className={cn(
                  "mb-0.5 flex flex-col rounded-md px-3 py-2 text-sm transition-colors hover:bg-slate-100",
                  selected && "bg-slate-200/80 text-slate-900",
                )}
              >
                <span className="font-medium">{item.label}</span>
                <span className="text-[11px] text-slate-400">{item.phase}</span>
              </Link>
            );
          })}
        </nav>

        <div className="border-t border-slate-200 p-3">
          {dualRole && onViewRoleChange && (
            <div className="mb-3 rounded-md border border-slate-200 p-1">
              <div className="mb-1 px-1 text-[10px] uppercase tracking-wider text-slate-400">Role</div>
              <div className="grid grid-cols-2 gap-1">
                {(["athlete", "coach"] as const).map((r) => (
                  <button
                    key={r}
                    type="button"
                    onClick={() => onViewRoleChange(r)}
                    className={cn(
                      "rounded px-2 py-1 text-xs capitalize",
                      role === r
                        ? "!bg-slate-900 !text-white hover:!bg-slate-800"
                        : "!bg-transparent !text-slate-500 hover:!text-slate-900",
                    )}
                  >
                    {r}
                  </button>
                ))}
              </div>
            </div>
          )}
          <div className="space-y-0.5">
            {hasRole("athlete") && (
              <>
                <Link
                  to="/athlete/profile"
                  className="block rounded-md px-2 py-1.5 text-xs text-slate-500 hover:text-slate-900"
                >
                  Profile
                </Link>
                <Link
                  to="/settings"
                  className="block rounded-md px-2 py-1.5 text-xs text-slate-500 hover:text-slate-900"
                >
                  Settings
                </Link>
              </>
            )}
            <button
              type="button"
              onClick={logout}
              className="block w-full rounded-md px-2 py-1.5 text-left text-xs !bg-transparent !text-slate-500 hover:!text-slate-900"
            >
              Log out
            </button>
          </div>
        </div>
      </aside>

      <div className="flex min-w-0 flex-1 flex-col">
        <header className="flex items-center justify-between border-b border-slate-200 px-8 py-4">
          <div>
            <div className="text-[11px] uppercase tracking-wider text-slate-400">{current.phase}</div>
            <h1 className="mt-0.5 text-lg font-semibold tracking-tight">{current.label}</h1>
            <p className="text-sm text-slate-500">{current.question}</p>
          </div>
          <div className="flex items-center gap-2">
            <button
              type="button"
              className="rounded-md border border-slate-200 bg-white px-3 py-1.5 text-xs text-slate-500 hover:text-slate-900"
              onClick={() => window.alert("Command bar (⌘K) — coming soon")}
            >
              ⌘K
            </button>
            <button
              type="button"
              className="rounded-md border border-slate-200 bg-white px-3 py-1.5 text-xs text-slate-500 hover:text-slate-900"
              onClick={() => window.alert("AI Coach panel — coming soon")}
            >
              AI Coach
            </button>
          </div>
        </header>

        <main className="min-w-0 flex-1 overflow-auto px-8 py-6">{children}</main>
      </div>
    </div>
  );
}
