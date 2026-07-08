from __future__ import annotations

import numpy as np


def softmax_percentages(scores: np.ndarray) -> np.ndarray:
    """
    Convert raw scores into percentages using softmax.
    """
    if scores.size != 3:
        raise ValueError("scores must contain BUY, HOLD, SELL only")

    max_score = float(np.max(scores))
    exp_scores = np.exp(scores - max_score)
    total = float(np.sum(exp_scores))

    if total <= 0:
        raise ValueError("softmax total is invalid")

    return (exp_scores / total) * 100.0


def confidence_gap_penalty(scores: np.ndarray) -> float:
    """
    If the top 2 raw scores are too close, reduce confidence a bit.
    """
    if scores.size != 3:
        raise ValueError("scores must contain BUY, HOLD, SELL only")

    ordered = sorted(float(x) for x in scores)[::-1]
    gap = ordered[0] - ordered[1]

    if gap < 0.25:
        return 0.88
    if gap < 0.50:
        return 0.94
    return 1.0


def normalize_confidence(buy: float, hold: float, sell: float) -> dict[str, float]:
    scores = np.array([buy, hold, sell], dtype=float)

    pct = softmax_percentages(scores)
    penalty = confidence_gap_penalty(scores)

    pct = pct * penalty

    total = float(np.sum(pct))
    if total <= 0:
        raise ValueError("normalized confidence total is invalid")

    pct = (pct / total) * 100.0

    return {
        "buy": round(float(pct[0]), 2),
        "hold": round(float(pct[1]), 2),
        "sell": round(float(pct[2]), 2),
    }