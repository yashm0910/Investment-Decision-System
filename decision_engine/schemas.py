from __future__ import annotations

from typing import Any, Literal
from pydantic import BaseModel, Field


class StockSituation(BaseModel):
    # Cleaned stock-situation object that the decision engine reads.
    symbol: str | None = None
    latest_close: float | None = None
    ema_20: float | None = None
    rsi_14: float | None = None

    trend_signal: str | None = None
    trend_strength: str | None = None
    momentum_signal: str | None = None
    structure_signal: str | None = None
    volume_signal: str | None = None
    market_regime: str | None = None

    latest_volume: float | None = None
    avg_volume_20: float | None = None
    recent_low_20: float | None = None
    recent_high_20: float | None = None

    signals: list[str] = Field(default_factory=list)
    raw: dict[str, Any] | None = None


class DecisionConfidence(BaseModel):
    buy: float
    hold: float
    sell: float
    dominant_action: Literal["BUY", "HOLD", "SELL"]
    regime: str | None = None
    reasons: list[str] = Field(default_factory=list)
    raw_scores: dict[str, float] = Field(default_factory=dict)


class ToolResponse(BaseModel):
    # MCP-friendly wrapper with explicit status and code.
    status: str
    code: int
    message: str
    data: dict[str, Any] | None = None