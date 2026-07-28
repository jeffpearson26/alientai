from __future__ import annotations

"""Small dependency-free calibration helpers for research model scores."""

from bisect import bisect_left, bisect_right
from typing import Iterable, Sequence


def fit_isotonic(scores: Sequence[float], labels: Sequence[int]) -> list[dict[str, float]]:
    if len(scores) != len(labels) or not scores:
        raise ValueError("scores and labels must be nonempty and have equal length")
    grouped: list[dict[str, float]] = []
    for score, label in sorted(zip(scores, labels)):
        if grouped and grouped[-1]["upper_score"] == float(score):
            grouped[-1]["successes"] += int(bool(label))
            grouped[-1]["count"] += 1
        else:
            grouped.append({
                "lower_score": float(score),
                "upper_score": float(score),
                "successes": int(bool(label)),
                "count": 1,
            })
    blocks: list[dict[str, float]] = []
    for group in grouped:
        blocks.append(group)
        while len(blocks) >= 2:
            left, right = blocks[-2], blocks[-1]
            if left["successes"] / left["count"] <= right["successes"] / right["count"]:
                break
            blocks[-2:] = [{
                "lower_score": left["lower_score"],
                "upper_score": right["upper_score"],
                "successes": left["successes"] + right["successes"],
                "count": left["count"] + right["count"],
            }]
    return [{
        **block,
        "probability": block["successes"] / block["count"],
    } for block in blocks]


def calibrated_probability(score: float, blocks: Sequence[dict[str, float]]) -> float:
    if not blocks:
        raise ValueError("calibration blocks are required")
    uppers = [float(block["upper_score"]) for block in blocks]
    index = min(bisect_left(uppers, float(score)), len(blocks) - 1)
    return float(blocks[index]["probability"])


def percentile_rank(score: float, reference_scores: Sequence[float]) -> int:
    if not reference_scores:
        raise ValueError("reference scores are required")
    ordered = sorted(float(value) for value in reference_scores)
    rank = 100.0 * bisect_right(ordered, float(score)) / len(ordered)
    return max(1, min(100, int(round(rank))))


def brier_score(probabilities: Iterable[float], labels: Iterable[int]) -> float:
    pairs = list(zip(probabilities, labels))
    if not pairs:
        raise ValueError("probabilities and labels are required")
    return sum((float(probability) - int(bool(label))) ** 2 for probability, label in pairs) / len(pairs)


def expected_calibration_error(
    probabilities: Sequence[float], labels: Sequence[int], bins: int = 10,
) -> float:
    if len(probabilities) != len(labels) or not probabilities:
        raise ValueError("probabilities and labels must be nonempty and have equal length")
    if bins < 2:
        raise ValueError("bins must be at least two")
    total, error = len(labels), 0.0
    for index in range(bins):
        lower, upper = index / bins, (index + 1) / bins
        selected = [
            position for position, value in enumerate(probabilities)
            if lower <= float(value) < upper or (index == bins - 1 and float(value) == 1.0)
        ]
        if not selected:
            continue
        predicted = sum(float(probabilities[position]) for position in selected) / len(selected)
        observed = sum(int(bool(labels[position])) for position in selected) / len(selected)
        error += len(selected) / total * abs(predicted - observed)
    return error
