import { Link } from "react-router-dom";
import type { CoachAthleteListItem } from "../coaching/api";
import { formatDate } from "../shared/dates";

type AthleteListProps = {
  athletes: CoachAthleteListItem[];
};

export function AthleteList({ athletes }: AthleteListProps) {
  if (athletes.length === 0) {
    return (
      <p className="muted">
        No active athletes yet. Search below to invite an athlete — they must accept before appearing
        here.
      </p>
    );
  }

  return (
    <div className="stack">
      {athletes.map((item) => (
        <Link
          key={item.relation_id}
          to={`/coach/athletes/${item.athlete.id}`}
          className="athlete-list-row card"
        >
          <div className="row-between">
            <div>
              <strong>{item.athlete.name}</strong>
              <p className="muted">@{item.athlete.username}</p>
            </div>
            {item.created_at && (
              <span className="muted">Since {formatDate(item.created_at.slice(0, 10))}</span>
            )}
          </div>
        </Link>
      ))}
    </div>
  );
}
