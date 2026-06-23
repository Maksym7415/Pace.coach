type ReadinessBadgeProps = {
  score: number | null;
};

export function ReadinessBadge({ score }: ReadinessBadgeProps) {
  if (score === null) {
    return <span className="badge badge-muted">No readiness score</span>;
  }

  let level = "badge-ok";
  if (score < 50) level = "badge-low";
  else if (score < 70) level = "badge-mid";

  return (
    <span className={`badge ${level}`} title="Readiness score">
      Readiness {score}
    </span>
  );
}
