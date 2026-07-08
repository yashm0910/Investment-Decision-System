import yfinance as yf
import pandas as pd


def fetch_stock_data(
    symbol: str,
    period: str = "6mo",
    interval: str = "1d"
):
    """
    Fetch OHLCV stock market data from Yahoo Finance
    """

    ticker = yf.Ticker(symbol)

    df = ticker.history(
        period=period,
        interval=interval
    )

    if df.empty:
        raise ValueError(
            f"No market data found for symbol: {symbol}"
        )

    df.reset_index(inplace=True)

    return {
        "status": "success",
        "symbol": symbol,
        "rows_fetched": len(df),
        "data": df.to_dict(orient="records")
    }