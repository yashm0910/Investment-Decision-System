from __future__ import annotations

from typing import Any

import pandas as pd

from market_data import fetch_stock_data
from indicators import calculate_ema, calculate_rsi


def _status_response(status: str, code: int, message: str, data: dict[str, Any] | None = None):
    return {
        "status": status,
        "code": code,
        "message": message,
        "data": data,
    }


def analyze_stock_situation(symbol: str) -> dict[str, Any]:
    """
    Build a richer technical snapshot for the decision engine.

    This is still stock-only.
    No research/news is used here.
    """
    try:
        symbol = (symbol or "").strip()
        if not symbol:
            return _status_response("error", 400, "symbol is empty")

        response = fetch_stock_data(symbol)
        raw_rows = response.get("data") or []
        if not raw_rows:
            return _status_response("error", 404, f"No market data found for symbol: {symbol}")

        df = pd.DataFrame(raw_rows)
        if df.empty:
            return _status_response("error", 404, f"No market data found for symbol: {symbol}")

        # Core indicators
        ema_20 = calculate_ema(df, 20)
        rsi_14 = calculate_rsi(df, 14)

        latest_close = float(df["Close"].iloc[-1])
        latest_ema = float(ema_20.iloc[-1])
        latest_rsi = float(rsi_14.iloc[-1])

        # Optional fields
        latest_volume = float(df["Volume"].iloc[-1]) if "Volume" in df.columns else None
        avg_volume_20 = float(df["Volume"].tail(20).mean()) if "Volume" in df.columns else None
        recent_low_20 = float(df["Low"].tail(20).min()) if "Low" in df.columns else None
        recent_high_20 = float(df["High"].tail(20).max()) if "High" in df.columns else None

        # Trend
        if latest_close > latest_ema:
            trend_signal = "bullish"
            trend_strength = "strong" if latest_close > latest_ema * 1.02 else "moderate"
        else:
            trend_signal = "bearish"
            trend_strength = "strong" if latest_close < latest_ema * 0.98 else "moderate"

        # Momentum
        if latest_rsi < 30:
            momentum_signal = "oversold"
        elif latest_rsi > 70:
            momentum_signal = "overbought"
        else:
            momentum_signal = "neutral"

        # Structure
        structure_signal = "unclear"
        if recent_low_20 is not None and latest_close <= recent_low_20 * 1.02:
            structure_signal = "near_support"
        elif recent_high_20 is not None and latest_close >= recent_high_20 * 0.98:
            structure_signal = "near_resistance"
        elif recent_low_20 is not None and recent_high_20 is not None:
            structure_signal = "range_middle"

        # Volume / participation
        volume_signal = "neutral"
        if latest_volume is not None and avg_volume_20 not in (None, 0):
            if latest_volume >= avg_volume_20 * 1.25:
                volume_signal = "above_average"
            elif latest_volume <= avg_volume_20 * 0.80:
                volume_signal = "below_average"
            else:
                volume_signal = "average"

        # Very simple market mood
        if trend_signal == "bullish" and momentum_signal in {"neutral", "oversold"}:
            market_regime = "risk_on"
        elif trend_signal == "bearish" and momentum_signal in {"neutral", "overbought"}:
            market_regime = "risk_off"
        else:
            market_regime = "mixed"

        signals = [
            f"Price {'above' if latest_close > latest_ema else 'below'} EMA20",
            f"RSI {latest_rsi:.2f}",
            f"Trend is {trend_signal}",
            f"Momentum is {momentum_signal}",
            f"Structure is {structure_signal}",
            f"Volume is {volume_signal}",
        ]

        data = {
            "symbol": symbol,
            "latest_close": round(latest_close, 2),
            "ema_20": round(latest_ema, 2),
            "rsi_14": round(latest_rsi, 2),
            "trend_signal": trend_signal,
            "trend_strength": trend_strength,
            "momentum_signal": momentum_signal,
            "structure_signal": structure_signal,
            "volume_signal": volume_signal,
            "market_regime": market_regime,
            "latest_volume": round(latest_volume, 2) if latest_volume is not None else None,
            "avg_volume_20": round(avg_volume_20, 2) if avg_volume_20 is not None else None,
            "recent_low_20": round(recent_low_20, 2) if recent_low_20 is not None else None,
            "recent_high_20": round(recent_high_20, 2) if recent_high_20 is not None else None,
            "signals": signals,
            "raw": response,
        }

        return _status_response(
            "success",
            200,
            "Stock situation analyzed successfully",
            data,
        )

    except Exception as e:
        return _status_response(
            "error",
            500,
            f"Failed to analyze stock situation: {e}",
            None,
        )