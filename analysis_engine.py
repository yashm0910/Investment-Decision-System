from market_data import fetch_stock_data
from indicators import calculate_ema, calculate_rsi

# ==========STOCK ANALYSIS========
def analyze_stock(symbol: str):

    response = fetch_stock_data(symbol)

    data = response["data"]

    import pandas as pd

    df = pd.DataFrame(data)

    # --------------------------
    # INDICATORS
    # --------------------------

    ema_20 = calculate_ema(df, 20)

    rsi_14 = calculate_rsi(df, 14)

    # --------------------------
    # LATEST VALUES
    # --------------------------

    latest_close = df["Close"].iloc[-1]

    latest_ema = ema_20.iloc[-1]

    latest_rsi = rsi_14.iloc[-1]
    
    signals = []

    if latest_close > latest_ema:
        signals.append(
            "Price trading above EMA20"
        )
    else:
        signals.append(
            "Price trading below EMA20"
        )

    if latest_rsi < 30:
        signals.append(
            "RSI indicates oversold conditions"
        )

    elif latest_rsi > 70:
        signals.append(
            "RSI indicates overbought conditions"
        )

    # --------------------------
    # TREND INTERPRETATION
    # --------------------------

    if latest_close > latest_ema:
        trend = "bullish"

    else:
        trend = "bearish"

    # --------------------------
    # MOMENTUM INTERPRETATION
    # --------------------------

    if latest_rsi < 30:
        momentum = "oversold"

    elif latest_rsi > 70:
        momentum = "overbought"

    else:
        momentum = "neutral"

    # --------------------------
    # FINAL STRUCTURED OUTPUT
    # --------------------------

    return {
        "symbol": symbol,

        "latest_close": round(float(latest_close), 2),

        "ema_20": round(float(latest_ema), 2),

        "rsi_14": round(float(latest_rsi), 2),

        "trend_signal": trend,

        "momentum_signal": momentum,
        
        "signals" : signals
    }
    

# ==========MARKET ANALYSIS========

import pandas as pd

MARKET_INDICES = {
    "nifty": "^NSEI",
    "sensex": "^BSESN",
    "nasdaq": "^IXIC",
    "sp500": "^GSPC",
    "dowjones": "^DJI"
}

def analyze_market(index_name: str):

    symbol = MARKET_INDICES[index_name.lower()]

    symbol = MARKET_INDICES[index_name.lower()]

    response = fetch_stock_data(symbol)

    df = pd.DataFrame(
        response["data"]
    )

    ema_20 = calculate_ema(df, 20)

    rsi_14 = calculate_rsi(df, 14)

    latest_close = float(df["Close"].iloc[-1])
    latest_ema = float(ema_20.iloc[-1])
    latest_rsi = float(rsi_14.iloc[-1])

    # -------------------------
    # Trend
    # -------------------------

    trend = (
        "bullish"
        if latest_close > latest_ema
        else "bearish"
    )

    # -------------------------
    # Momentum
    # -------------------------

    if latest_rsi > 70:
        momentum = "strong_overbought"

    elif latest_rsi < 30:
        momentum = "oversold"

    else:
        momentum = "neutral"

    # -------------------------
    # Market Regime
    # -------------------------

    if trend == "bullish" and latest_rsi > 55:
        regime = "risk_on"

    elif trend == "bearish" and latest_rsi < 45:
        regime = "risk_off"

    else:
        regime = "mixed"

    return {

        "market": index_name,

        "index_symbol": symbol,

        "latest_close": round(latest_close, 2),

        "ema_20": round(latest_ema, 2),

        "rsi_14": round(latest_rsi, 2),

        "trend": trend,

        "momentum": momentum,

        "market_regime": regime
    }
    

