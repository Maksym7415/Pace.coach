import type { ExecutionIssue, IssueSeverity } from "./types";

export const SEVERITY_LABEL: Record<IssueSeverity, string> = {
  info: "Low",
  warning: "Medium",
  critical: "High",
};

export const SEVERITY_RANK_SORT: Record<IssueSeverity, number> = {
  info: 1,
  warning: 2,
  critical: 3,
};

const SEVERITY_RANK = SEVERITY_RANK_SORT;

export function maxSeverity(issues: ExecutionIssue[]): IssueSeverity | null {
  if (!issues.length) return null;
  return issues.reduce<IssueSeverity>((max, issue) => {
    return SEVERITY_RANK[issue.severity] > SEVERITY_RANK[max] ? issue.severity : max;
  }, issues[0].severity);
}
