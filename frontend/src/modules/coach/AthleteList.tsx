import { Link } from "react-router-dom";
import type { CoachAthleteListItem } from "../coaching/api";
import { Chip } from "../shared/PageChrome";
import { formatDate } from "../shared/dates";
import { mockMesocycle } from "./athlete/mockAthleteContext";

type AthleteListProps = {
  athletes: CoachAthleteListItem[];
};

export function AthleteList({ athletes }: AthleteListProps) {
  if (athletes.length === 0) {
    return (
      <p className="text-sm text-slate-500">
        No active athletes yet. Search below to invite an athlete — they must accept before appearing
        here.
      </p>
    );
  }

  return (
    <ul className="divide-y divide-slate-100 text-sm">
      {athletes.map((item) => {
        const meso = mockMesocycle(item.athlete.id);
        return (
          <li key={item.relation_id} className="flex items-center justify-between gap-3 py-2.5">
            <div className="min-w-0">
              <div className="font-medium text-slate-900">{item.athlete.name}</div>
              <div className="mt-0.5 flex flex-wrap items-center gap-1.5 text-xs text-slate-500">
                <span>@{item.athlete.username}</span>
                <span aria-hidden>·</span>
                <span>{meso.subtitle}</span>
                <Chip className="border-amber-200 bg-amber-50 text-amber-700">Demo</Chip>
              </div>
              {item.created_at ? (
                <div className="mt-0.5 text-[11px] text-slate-400">
                  Since {formatDate(item.created_at.slice(0, 10))}
                </div>
              ) : null}
            </div>
            <Link
              to={`/coach/athletes/${item.athlete.id}`}
              className="shrink-0 text-xs font-medium text-slate-700 hover:underline"
            >
              Open →
            </Link>
          </li>
        );
      })}
    </ul>
  );
}
