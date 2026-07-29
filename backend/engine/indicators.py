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


# --- NEW TREND / CHANNEL INDICATORS ---

def macd(close: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9):
    """Return (macd_line, signal_line, histogram)."""
    fast_e = ema(close, fast)
    slow_e = ema(close, slow)
    macd_line = fast_e - slow_e
    signal_line = ema(macd_line, signal)
    hist = macd_line - signal_line
    return macd_line, signal_line, hist


def parabolic_sar(df: pd.DataFrame, af: float = 0.02, max_af: float = 0.2) -> pd.Series:
    """Return Parabolic SAR line."""
    h, l = df["high"], df["low"]
    n = len(df)
    sar = pd.Series(index=df.index, dtype=float)
    if n == 0:
        return sar

    is_long = True
    ep = l.iloc[0]
    hp = h.iloc[0]
    lp = l.iloc[0]
    af_curr = af
    sar.iloc[0] = l.iloc[0]

    for i in range(1, n):
        prev_sar = sar.iloc[i - 1]
        if is_long:
            curr_sar = prev_sar + af_curr * (hp - prev_sar)
            curr_sar = min(curr_sar, l.iloc[i - 1], l.iloc[max(0, i - 2)])
            if l.iloc[i] < curr_sar:
                is_long = False
                curr_sar = hp
                lp = l.iloc[i]
                af_curr = af
            else:
                if h.iloc[i] > hp:
                    hp = h.iloc[i]
                    af_curr = min(af_curr + af, max_af)
        else:
            curr_sar = prev_sar + af_curr * (lp - prev_sar)
            curr_sar = max(curr_sar, h.iloc[i - 1], h.iloc[max(0, i - 2)])
            if h.iloc[i] > curr_sar:
                is_long = True
                curr_sar = lp
                hp = h.iloc[i]
                af_curr = af
            else:
                if l.iloc[i] < lp:
                    lp = l.iloc[i]
                    af_curr = min(af_curr + af, max_af)
        sar.iloc[i] = curr_sar

    return sar


def ichimoku(df: pd.DataFrame, tenkan_n: int = 9, kijun_n: int = 26, senkou_n: int = 52):
    """Return (tenkan, kijun, senkou_a, senkou_b, chikou)."""
    h, l, c = df["high"], df["low"], df["close"]
    tenkan = (h.rolling(tenkan_n).max() + l.rolling(tenkan_n).min()) / 2
    kijun = (h.rolling(kijun_n).max() + l.rolling(kijun_n).min()) / 2
    senkou_a = (tenkan + kijun) / 2
    senkou_b = (h.rolling(senkou_n).max() + l.rolling(senkou_n).min()) / 2
    chikou = c.shift(-kijun_n)
    return tenkan, kijun, senkou_a, senkou_b, chikou


def donchian(df: pd.DataFrame, n: int = 20):
    """Return (upper_channel, mid_channel, lower_channel)."""
    upper = df["high"].rolling(n).max()
    lower = df["low"].rolling(n).min()
    mid = (upper + lower) / 2
    return upper, mid, lower


def keltner(df: pd.DataFrame, ema_n: int = 20, atr_n: int = 10, mult: float = 2.0):
    """Return (upper, mid, lower) Keltner channels."""
    mid = ema(df["close"], ema_n)
    atr_val = atr(df, atr_n)
    upper = mid + mult * atr_val
    lower = mid - mult * atr_val
    return upper, mid, lower


def ema_ribbon(close: pd.Series, periods: list = None) -> dict:
    """Return dictionary of EMAs for specified periods."""
    if periods is None:
        periods = [8, 13, 21, 34, 55]
    return {p: ema(close, p) for p in periods}


def vortex(df: pd.DataFrame, n: int = 14):
    """Return (vi_plus, vi_minus)."""
    h, l = df["high"], df["low"]
    vm_plus = (h - l.shift(1)).abs()
    vm_minus = (l - h.shift(1)).abs()
    tr = true_range(df)
    vi_plus = vm_plus.rolling(n).sum() / tr.rolling(n).sum().replace(0, np.nan)
    vi_minus = vm_minus.rolling(n).sum() / tr.rolling(n).sum().replace(0, np.nan)
    return vi_plus, vi_minus


def heikin_ashi(df: pd.DataFrame) -> pd.DataFrame:
    """Return DataFrame with ha_open, ha_high, ha_low, ha_close."""
    o, h, l, c = df["open"], df["high"], df["low"], df["close"]
    ha_close = (o + h + l + c) / 4
    ha_open = pd.Series(index=df.index, dtype=float)
    if len(df) > 0:
        ha_open.iloc[0] = (o.iloc[0] + c.iloc[0]) / 2
        for i in range(1, len(df)):
            ha_open.iloc[i] = (ha_open.iloc[i - 1] + ha_close.iloc[i - 1]) / 2

    ha_high = pd.concat([h, ha_open, ha_close], axis=1).max(axis=1)
    ha_low = pd.concat([l, ha_open, ha_close], axis=1).min(axis=1)

    return pd.DataFrame({
        "ha_open": ha_open,
        "ha_high": ha_high,
        "ha_low": ha_low,
        "ha_close": ha_close
    }, index=df.index)


def linreg_slope(close: pd.Series, n: int = 20) -> pd.Series:
    """Rolling linear regression slope of close price."""
    x = np.arange(n)
    x_mean = x.mean()
    x_var = ((x - x_mean) ** 2).sum()

    def calc_slope(window):
        if len(window) < n:
            return np.nan
        y = window
        y_mean = y.mean()
        cov = ((x - x_mean) * (y - y_mean)).sum()
        return cov / x_var

    return close.rolling(n).apply(calc_slope, raw=True)


def pivot_points(df: pd.DataFrame):
    """Return (pp, r1, s1, r2, s2) based on prior bar H/L/C."""
    prev_h = df["high"].shift(1)
    prev_l = df["low"].shift(1)
    prev_c = df["close"].shift(1)

    pp = (prev_h + prev_l + prev_c) / 3
    r1 = 2 * pp - prev_l
    s1 = 2 * pp - prev_h
    r2 = pp + (prev_h - prev_l)
    s2 = pp - (prev_h - prev_l)

    return pp, r1, s1, r2, s2


# --- OSCILLATORS & MOMENTUM ---

def stochastic(df: pd.DataFrame, k: int = 14, d: int = 3, smooth: int = 3):
    """Return (stoch_k, stoch_d)."""
    h, l, c = df["high"], df["low"], df["close"]
    ll = l.rolling(k).min()
    hh = h.rolling(k).max()
    stoch_raw = 100 * (c - ll) / (hh - ll).replace(0, np.nan)
    stoch_k = stoch_raw.rolling(smooth).mean()
    stoch_d = stoch_k.rolling(d).mean()
    return stoch_k, stoch_d


def stoch_rsi(close: pd.Series, n: int = 14, k: int = 3, d: int = 3):
    """Return (stoch_rsi_k, stoch_rsi_d)."""
    rsi_val = rsi(close, n)
    rsi_min = rsi_val.rolling(n).min()
    rsi_max = rsi_val.rolling(n).max()
    stoch_rsi_raw = (rsi_val - rsi_min) / (rsi_max - rsi_min).replace(0, np.nan)
    stoch_k = stoch_rsi_raw.rolling(k).mean()
    stoch_d = stoch_k.rolling(d).mean()
    return stoch_k, stoch_d


def cci(df: pd.DataFrame, n: int = 20) -> pd.Series:
    """Commodity Channel Index."""
    h, l, c = df["high"], df["low"], df["close"]
    tp = (h + l + c) / 3
    tp_sma = tp.rolling(n).mean()
    mad = tp.rolling(n).apply(lambda x: np.mean(np.abs(x - np.mean(x))), raw=True)
    return (tp - tp_sma) / (0.015 * mad.replace(0, np.nan))


def williams_r(df: pd.DataFrame, n: int = 14) -> pd.Series:
    """Williams %R."""
    h, l, c = df["high"], df["low"], df["close"]
    hh = h.rolling(n).max()
    ll = l.rolling(n).min()
    return -100 * (hh - c) / (hh - ll).replace(0, np.nan)


def roc(close: pd.Series, n: int = 12) -> pd.Series:
    """Rate of Change."""
    return 100 * (close - close.shift(n)) / close.shift(n).replace(0, np.nan)


def trix(close: pd.Series, n: int = 15):
    """Return (trix_line, signal_line)."""
    e1 = ema(close, n)
    e2 = ema(e1, n)
    e3 = ema(e2, n)
    trix_line = e3.pct_change() * 100
    signal_line = sma(trix_line, 9)
    return trix_line, signal_line


def awesome_oscillator(df: pd.DataFrame) -> pd.Series:
    """Awesome Oscillator (SMA5 - SMA34 of median price)."""
    mp = (df["high"] + df["low"]) / 2
    return sma(mp, 5) - sma(mp, 34)


# --- VOLUME INDICATORS ---

def obv(df: pd.DataFrame) -> pd.Series:
    """On-Balance Volume."""
    c, v = df["close"], df["volume"]
    sign = np.sign(c.diff()).fillna(0)
    return (sign * v).cumsum()


def mfi(df: pd.DataFrame, n: int = 14) -> pd.Series:
    """Money Flow Index."""
    h, l, c, v = df["high"], df["low"], df["close"], df["volume"]
    tp = (h + l + c) / 3
    raw_mf = tp * v
    tp_diff = tp.diff()
    pos_mf = pd.Series(np.where(tp_diff > 0, raw_mf, 0.0), index=df.index)
    neg_mf = pd.Series(np.where(tp_diff < 0, raw_mf, 0.0), index=df.index)

    pos_sum = pos_mf.rolling(n).sum()
    neg_sum = neg_mf.rolling(n).sum()
    mfr = pos_sum / neg_sum.replace(0, np.nan)
    return 100 - (100 / (1 + mfr))


def cmf(df: pd.DataFrame, n: int = 20) -> pd.Series:
    """Chaikin Money Flow."""
    h, l, c, v = df["high"], df["low"], df["close"], df["volume"]
    mfv = ((c - l) - (h - c)) / (h - l).replace(0, np.nan)
    mfv = mfv.fillna(0)
    return (mfv * v).rolling(n).sum() / v.rolling(n).sum().replace(0, np.nan)


def vol_sma(volume: pd.Series, n: int = 20) -> pd.Series:
    return volume.rolling(n).mean()


def rel_volume(volume: pd.Series, n: int = 20) -> pd.Series:
    return volume / vol_sma(volume, n).replace(0, np.nan)


# --- STATS & CANDLESTICKS ---

def zscore(close: pd.Series, n: int = 20) -> pd.Series:
    mean = close.rolling(n).mean()
    std = close.rolling(n).std().replace(0, np.nan)
    return (close - mean) / std


def bullish_engulfing(df: pd.DataFrame) -> pd.Series:
    o, c = df["open"], df["close"]
    prev_o, prev_c = o.shift(1), c.shift(1)
    is_bullish_curr = c > o
    is_bearish_prev = prev_c < prev_o
    engulfs = (c >= prev_o) & (o <= prev_c)
    return is_bullish_curr & is_bearish_prev & engulfs


def bearish_engulfing(df: pd.DataFrame) -> pd.Series:
    o, c = df["open"], df["close"]
    prev_o, prev_c = o.shift(1), c.shift(1)
    is_bearish_curr = c < o
    is_bullish_prev = prev_c > prev_o
    engulfs = (c <= prev_o) & (o >= prev_c)
    return is_bearish_curr & is_bullish_prev & engulfs


def hammer(df: pd.DataFrame) -> pd.Series:
    o, h, l, c = df["open"], df["high"], df["low"], df["close"]
    body = (c - o).abs()
    lower_shadow = np.minimum(o, c) - l
    upper_shadow = h - np.maximum(o, c)
    return (lower_shadow >= 2 * body) & (upper_shadow <= 0.2 * body) & (body > 0)


def shooting_star(df: pd.DataFrame) -> pd.Series:
    o, h, l, c = df["open"], df["high"], df["low"], df["close"]
    body = (c - o).abs()
    upper_shadow = h - np.maximum(o, c)
    lower_shadow = np.minimum(o, c) - l
    return (upper_shadow >= 2 * body) & (lower_shadow <= 0.2 * body) & (body > 0)


def doji(df: pd.DataFrame) -> pd.Series:
    o, h, l, c = df["open"], df["high"], df["low"], df["close"]
    body = (c - o).abs()
    range_val = h - l
    return (body <= 0.1 * range_val) & (range_val > 0)


def inside_bar(df: pd.DataFrame) -> pd.Series:
    h, l = df["high"], df["low"]
    return (h <= h.shift(1)) & (l >= l.shift(1))


def nr7(df: pd.DataFrame) -> pd.Series:
    range_val = df["high"] - df["low"]
    return range_val == range_val.rolling(7).min()
