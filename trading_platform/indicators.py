"""Technical indicators - pure pandas/numpy, no TA-Lib dependency (fully portable).

Every indicator here is backward-looking: it uses only the current bar and past
bars. That is what keeps the backtest free of look-ahead bias.
"""
import numpy as np
import pandas as pd


def ema(s: pd.Series, n: int) -> pd.Series:
    return s.ewm(span=n, adjust=False).mean()


def sma(s: pd.Series, n: int) -> pd.Series:
    return s.rolling(n).mean()


def rsi(close: pd.Series, n: int = 14) -> pd.Series:
    delta = close.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(alpha=1 / n, adjust=False, min_periods=n).mean()   # Wilder
    avg_loss = loss.ewm(alpha=1 / n, adjust=False, min_periods=n).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    return 100 - (100 / (1 + rs))


def true_range(df: pd.DataFrame) -> pd.Series:
    h, l, c = df["high"], df["low"], df["close"]
    prev_c = c.shift(1)
    return pd.concat([(h - l), (h - prev_c).abs(), (l - prev_c).abs()], axis=1).max(axis=1)


def atr(df: pd.DataFrame, n: int = 14) -> pd.Series:
    return true_range(df).ewm(alpha=1 / n, adjust=False, min_periods=n).mean()


def adx(df: pd.DataFrame, n: int = 14):
    """Return (adx, plus_di, minus_di) using Wilder smoothing."""
    h, l = df["high"], df["low"]
    up = h.diff()
    down = -l.diff()
    plus_dm = pd.Series(np.where((up > down) & (up > 0), up, 0.0), index=df.index)
    minus_dm = pd.Series(np.where((down > up) & (down > 0), down, 0.0), index=df.index)
    atr_ = true_range(df).ewm(alpha=1 / n, adjust=False, min_periods=n).mean()
    plus_di = 100 * plus_dm.ewm(alpha=1 / n, adjust=False, min_periods=n).mean() / atr_
    minus_di = 100 * minus_dm.ewm(alpha=1 / n, adjust=False, min_periods=n).mean() / atr_
    dx = 100 * (plus_di - minus_di).abs() / (plus_di + minus_di).replace(0, np.nan)
    adx_ = dx.ewm(alpha=1 / n, adjust=False, min_periods=n).mean()
    return adx_, plus_di, minus_di


def supertrend(df: pd.DataFrame, period: int = 10, multiplier: float = 3.0):
    """Return (supertrend_line, direction); direction = 1 (up/long) or -1 (down/short)."""
    atr_ = atr(df, period)
    hl2 = (df["high"] + df["low"]) / 2
    upper = hl2 + multiplier * atr_
    lower = hl2 - multiplier * atr_
    close = df["close"]
    st = pd.Series(index=df.index, dtype=float)
    direction = pd.Series(index=df.index, dtype=float)
    fu, fl = upper.copy(), lower.copy()
    for i in range(len(df)):
        if i == 0:
            direction.iloc[i] = 1
            st.iloc[i] = lower.iloc[i]
            continue
        fu.iloc[i] = min(upper.iloc[i], fu.iloc[i - 1]) if close.iloc[i - 1] <= fu.iloc[i - 1] else upper.iloc[i]
        fl.iloc[i] = max(lower.iloc[i], fl.iloc[i - 1]) if close.iloc[i - 1] >= fl.iloc[i - 1] else lower.iloc[i]
        if direction.iloc[i - 1] == 1:
            direction.iloc[i] = -1 if close.iloc[i] < fl.iloc[i] else 1
        else:
            direction.iloc[i] = 1 if close.iloc[i] > fu.iloc[i] else -1
        st.iloc[i] = fl.iloc[i] if direction.iloc[i] == 1 else fu.iloc[i]
    return st, direction


def bollinger(close: pd.Series, n: int = 20, k: float = 2.0):
    mid = close.rolling(n).mean()
    sd = close.rolling(n).std()
    return mid + k * sd, mid, mid - k * sd
