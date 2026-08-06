"""Confidence-gated, evidence-aware insight claims.

Athlete feedback UX is deferred — only the stable identity contract is reserved:
(workout_execution_id, authored_step_id, occurrence_ordinal).
"""
from __future__ import annotations

from src.modules.execution.domain import (
    ExecutionIssueDraft,
    InsightClaim,
    MatchEvidence,
    SegmentMatch,
)


# Minimum match confidence required to assert intensity/quality claims
_MIN_CONFIDENCE_FOR_QUALITY = 0.6
_MIN_CONFIDENCE_FOR_INTENSITY = 0.5


def build_insights(
    matches: list[SegmentMatch],
    issues: list[ExecutionIssueDraft],
) -> list[InsightClaim]:
    evidence_by_key: dict[tuple[str, int], MatchEvidence] = {}
    confidence_by_key: dict[tuple[str, int], float] = {}
    for match in matches:
        key = (match.occurrence.authored_step_id, match.occurrence.occurrence_ordinal)
        evidence_by_key[key] = match.evidence
        if match.window is not None:
            confidence_by_key[key] = match.window.confidence

    claims: list[InsightClaim] = []
    for issue in issues:
        if issue.authored_step_id is None or issue.occurrence_ordinal is None:
            claims.append(
                InsightClaim(
                    code=issue.code,
                    claim_type="issue",
                    payload=issue.payload,
                    text_key=f"insight.{issue.code}",
                )
            )
            continue

        key = (issue.authored_step_id, issue.occurrence_ordinal)
        evidence = evidence_by_key.get(key)
        confidence = confidence_by_key.get(key, 0.0)
        suppressed, reason = _should_suppress(issue, evidence, confidence)

        claims.append(
            InsightClaim(
                code=issue.code,
                claim_type="issue",
                authored_step_id=issue.authored_step_id,
                occurrence_ordinal=issue.occurrence_ordinal,
                suppressed=suppressed,
                suppression_reason=reason,
                payload=issue.payload,
                text_key=f"insight.{issue.code}",
            )
        )

    return claims


def _should_suppress(
    issue: ExecutionIssueDraft,
    evidence: MatchEvidence | None,
    confidence: float,
) -> tuple[bool, str | None]:
    if evidence is None:
        return False, None

    if issue.dimension == "quality":
        if evidence.strategy_id == "signal" or evidence.details.get("approximate"):
            return True, "approximate_boundaries"
        if confidence < _MIN_CONFIDENCE_FOR_QUALITY:
            return True, "low_match_confidence"

    if issue.dimension == "intensity":
        if confidence < _MIN_CONFIDENCE_FOR_INTENSITY:
            return True, "low_match_confidence"
        if evidence.negative_claim:
            return True, "negative_match_claim"

    return False, None
