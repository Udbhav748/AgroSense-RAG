"""Human evaluation aggregation: per-dimension mean/median/stdev, and
Inter-Annotator Agreement ONLY when 2+ reviewers actually scored the same
items — never fabricated, never silently assumed.

Reuses docs/HUMAN_EVAL.md's own 7-dimension rubric (Correctness,
Helpfulness, Completeness, Safety, Tone, Groundedness, Citation Quality) —
this module just aggregates scores, it does not redefine the rubric.
"""

from __future__ import annotations

import statistics
from dataclasses import dataclass

RUBRIC_DIMENSIONS = [
    "correctness",
    "helpfulness",
    "completeness",
    "safety",
    "tone",
    "groundedness",
    "citation_quality",
]

__all__ = ["RUBRIC_DIMENSIONS", "ReviewerScore", "aggregate_scores", "inter_annotator_agreement"]


@dataclass
class ReviewerScore:
    case_id: str
    reviewer_id: str
    scores: dict[str, float | None]  # dimension -> 1-5, or None for N/A (e.g. conversational)


def aggregate_scores(scores: list[ReviewerScore]) -> dict:
    """Mean/median/stdev per dimension across every scored (case, reviewer)
    pair. stdev requires >=2 data points for a dimension or is reported as
    None (statistics.stdev raises on n<2 — caught explicitly, not
    swallowed into a fabricated 0.0)."""
    per_dimension: dict[str, list[float]] = {d: [] for d in RUBRIC_DIMENSIONS}
    for s in scores:
        for dim, value in s.scores.items():
            if value is not None and dim in per_dimension:
                per_dimension[dim].append(value)

    result = {}
    for dim, values in per_dimension.items():
        if not values:
            result[dim] = {"mean": None, "median": None, "stdev": None, "n": 0}
            continue
        result[dim] = {
            "mean": round(statistics.mean(values), 3),
            "median": round(statistics.median(values), 3),
            "stdev": round(statistics.stdev(values), 3) if len(values) >= 2 else None,
            "n": len(values),
        }
    return result


def inter_annotator_agreement(scores: list[ReviewerScore]) -> dict:
    """Per-dimension IAA (mean absolute pairwise score difference, and its
    complement as a 0-1 'agreement' figure: 1 - avg_diff/4, since scores
    are 1-5) computed ONLY over case_ids that have 2+ distinct reviewers.
    If no case has 2+ reviewers (the common situation in this project per
    docs/HUMAN_EVAL.md), returns the honest "not available" shape rather
    than a fabricated number — matching this project's existing, explicit
    convention (docs/HUMAN_EVAL.md: 'IAA = not available, reason = one
    reviewer')."""
    by_case: dict[str, list[ReviewerScore]] = {}
    for s in scores:
        by_case.setdefault(s.case_id, []).append(s)

    multi_reviewer_cases = {cid: group for cid, group in by_case.items() if len({s.reviewer_id for s in group}) >= 2}

    if not multi_reviewer_cases:
        reviewers = {s.reviewer_id for s in scores}
        return {
            "iaa": "not available",
            "reason": f"one reviewer ({len(reviewers)} reviewer(s) total, 0 cases with 2+ independent scores)",
        }

    per_dimension_diffs: dict[str, list[float]] = {d: [] for d in RUBRIC_DIMENSIONS}
    for _cid, group in multi_reviewer_cases.items():
        for dim in RUBRIC_DIMENSIONS:
            values = [s.scores.get(dim) for s in group if s.scores.get(dim) is not None]
            if len(values) < 2:
                continue
            # mean absolute pairwise difference across all reviewer pairs for this case+dimension
            diffs = [abs(a - b) for i, a in enumerate(values) for b in values[i + 1 :]]
            per_dimension_diffs[dim].extend(diffs)

    per_dimension_iaa = {}
    for dim, diffs in per_dimension_diffs.items():
        if not diffs:
            per_dimension_iaa[dim] = None
            continue
        avg_diff = sum(diffs) / len(diffs)
        per_dimension_iaa[dim] = round(1 - (avg_diff / 4), 4)  # 4 = max possible diff on a 1-5 scale

    return {
        "iaa": "computed",
        "n_multi_reviewer_cases": len(multi_reviewer_cases),
        "per_dimension_agreement": per_dimension_iaa,
    }
