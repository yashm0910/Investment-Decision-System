from __future__ import annotations

from typing import Any

import numpy as np

from .schemas import StockSituation

BUY = 0
HOLD = 1
SELL = 2


def _norm(value: Any) -> str:
    return str(value or "").strip().lower()


def _pick(data: dict[str, Any], *keys: str, default=None):
    for key in keys:
        if key in data and data[key] is not None:
            return data[key]
    return default


def normalize_stock_situation(payload: dict[str, Any] | StockSituation) -> StockSituation:
    """
    Accept either:
    - the raw analyzer response, or
    - the inner 'data' object
    and turn it into a stable StockSituation model.
    """
    if isinstance(payload, StockSituation):
        return payload

    if not isinstance(payload, dict):
        raise TypeError("stock payload must be a dict or StockSituation")

    data = payload.get("data") if isinstance(payload.get("data"), dict) else payload

    return StockSituation(
        symbol=_pick(data, "symbol"),
        latest_close=_pick(data, "latest_close", "close"),
        ema_20=_pick(data, "ema_20", "ema20"),
        rsi_14=_pick(data, "rsi_14", "rsi14"),
        trend_signal=_pick(data, "trend_signal", "trend"),
        trend_strength=_pick(data, "trend_strength"),
        momentum_signal=_pick(data, "momentum_signal", "momentum"),
        structure_signal=_pick(data, "structure_signal"),
        volume_signal=_pick(data, "volume_signal"),
        market_regime=_pick(data, "market_regime", "regime"),
        latest_volume=_pick(data, "latest_volume"),
        avg_volume_20=_pick(data, "avg_volume_20"),
        recent_low_20=_pick(data, "recent_low_20"),
        recent_high_20=_pick(data, "recent_high_20"),
        signals=list(_pick(data, "signals", default=[])),
        raw=payload,
    )


def trend_vector(situation: StockSituation) -> tuple[np.ndarray, list[str]]:
    vec = np.array([0.0, 0.0, 0.0], dtype=float)
    reasons: list[str] = []

    trend = _norm(situation.trend_signal)
    strength = _norm(situation.trend_strength)
    signals = [_norm(s) for s in situation.signals]
    joined = " | ".join(signals)

    if "bull" in trend:
        vec[BUY] += 2.0
        vec[HOLD] += 0.2
        reasons.append("trend is bullish")
        if strength == "strong":
            vec[BUY] += 0.8
            reasons.append("trend strength is strong")
        elif strength == "moderate":
            vec[BUY] += 0.4
            reasons.append("trend strength is moderate")
    elif "bear" in trend:
        vec[SELL] += 2.0
        vec[HOLD] += 0.2
        reasons.append("trend is bearish")
        if strength == "strong":
            vec[SELL] += 0.8
            reasons.append("trend strength is strong")
        elif strength == "moderate":
            vec[SELL] += 0.4
            reasons.append("trend strength is moderate")
    else:
        vec[HOLD] += 1.0
        reasons.append("trend is neutral or mixed")

    if "above ema" in joined:
        vec[BUY] += 0.8
        reasons.append("price is above EMA")
    if "below ema" in joined:
        vec[SELL] += 0.8
        reasons.append("price is below EMA")

    return vec, reasons


def momentum_vector(situation: StockSituation) -> tuple[np.ndarray, list[str]]:
    vec = np.array([0.0, 0.0, 0.0], dtype=float)
    reasons: list[str] = []

    rsi = situation.rsi_14
    if rsi is None:
        vec[HOLD] += 1.0
        reasons.append("RSI is missing")
        return vec, reasons

    if rsi < 30:
        vec[BUY] += 2.0
        vec[HOLD] += 0.4
        reasons.append("RSI is oversold")
    elif rsi > 70:
        vec[SELL] += 2.0
        vec[HOLD] += 0.4
        reasons.append("RSI is overbought")
    else:
        vec[HOLD] += 1.2
        reasons.append("RSI is neutral")

    return vec, reasons


def structure_vector(situation: StockSituation) -> tuple[np.ndarray, list[str]]:
    vec = np.array([0.0, 0.0, 0.0], dtype=float)
    reasons: list[str] = []

    structure = _norm(situation.structure_signal)

    if structure == "near_support":
        vec[BUY] += 1.8
        vec[HOLD] += 0.3
        reasons.append("price is near support")
    elif structure == "near_resistance":
        vec[SELL] += 1.8
        vec[HOLD] += 0.3
        reasons.append("price is near resistance")
    elif structure == "range_middle":
        vec[HOLD] += 1.2
        reasons.append("price is in the middle of the range")
    else:
        vec[HOLD] += 1.0
        reasons.append("structure is unclear")

    return vec, reasons


def volume_vector(situation: StockSituation) -> tuple[np.ndarray, list[str]]:
    vec = np.array([0.0, 0.0, 0.0], dtype=float)
    reasons: list[str] = []

    volume = _norm(situation.volume_signal)

    if volume == "above_average":
        vec[BUY] += 1.3
        vec[HOLD] += 0.2
        reasons.append("volume confirms the move")
    elif volume == "below_average":
        vec[HOLD] += 1.2
        reasons.append("volume is weak")
    else:
        vec[HOLD] += 0.8
        reasons.append("volume is neutral")

    return vec, reasons


def get_market_weights(situation: StockSituation) -> dict[str, float]:
    """
    Very small regime-based weighting.

    Trending market:
        trust trend more.

    Mixed market:
        trust momentum/structure a bit more.
    """
    regime = _norm(situation.market_regime)

    weights = {
        "trend": 1.0,
        "momentum": 1.0,
        "structure": 1.0,
        "volume": 1.0,
    }

    if regime in {"risk_on", "bullish", "uptrend"}:
        weights["trend"] = 1.35
        weights["momentum"] = 0.90
        weights["structure"] = 1.00
        weights["volume"] = 1.10
    elif regime in {"risk_off", "bearish", "downtrend"}:
        weights["trend"] = 1.20
        weights["momentum"] = 1.00
        weights["structure"] = 1.10
        weights["volume"] = 0.90
    else:
        weights["trend"] = 0.90
        weights["momentum"] = 1.10
        weights["structure"] = 1.10
        weights["volume"] = 1.00

    return weights


def build_evidence_vectors(situation: StockSituation) -> tuple[np.ndarray, list[str]]:
    """
    Combine the 4 families into one BUY/HOLD/SELL evidence vector.
    """
    weights = get_market_weights(situation)

    t_vec, t_reason = trend_vector(situation)
    m_vec, m_reason = momentum_vector(situation)
    s_vec, s_reason = structure_vector(situation)
    v_vec, v_reason = volume_vector(situation)

    evidence = (
        weights["trend"] * t_vec
        + weights["momentum"] * m_vec
        + weights["structure"] * s_vec
        + weights["volume"] * v_vec
    )

    reasons = t_reason + m_reason + s_reason + v_reason

    # HOLD logic:
    # If buy and sell both have some weight, uncertainty should increase.
    if evidence[BUY] > 0 and evidence[SELL] > 0:
        evidence[HOLD] += 0.6
        reasons.append("signals conflict, so HOLD increases")

    # If buy and sell are too close, this is also uncertainty.
    if abs(float(evidence[BUY]) - float(evidence[SELL])) < 0.75:
        evidence[HOLD] += 0.8
        reasons.append("buy and sell are close, so HOLD increases")

    if _norm(situation.market_regime) == "mixed":
        evidence[HOLD] += 0.5
        reasons.append("market regime is mixed")

    return evidence, reasons