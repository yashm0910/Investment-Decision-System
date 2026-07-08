import pandas as pd
import numpy as np


def calculate_ema(df, window=20):

    ema = (
        df["Close"]
        .ewm(span=window, adjust=False)
        .mean()
    )

    return ema

def calculate_rsi(df, window=14):

    delta = df["Close"].diff()

    gain = np.where(delta > 0, delta, 0)
    loss = np.where(delta < 0, -delta, 0)

    avg_gain = (
        pd.Series(gain)
        .rolling(window=window)
        .mean()
    )

    avg_loss = (
        pd.Series(loss)
        .rolling(window=window)
        .mean()
    )

    rs = avg_gain / avg_loss

    rsi = 100 - (100 / (1 + rs))

    return rsi