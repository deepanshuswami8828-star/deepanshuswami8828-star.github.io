"""The strategy library. Each strategy emits entry/exit signals plus a
human-readable reason for every signal, so each trade in the report carries
the exact rule that triggered it.
"""
import pandas as pd

from .base import Strategy, register
from indicators import ema, rsi, supertrend, bollinger


@register
class EmaCrossover(Strategy):
    name = "EMA Crossover"
    fast, slow = 9, 21
    sl_atr_mult, rr_ratio = 2.0, 2.0

    def generate_signals(self, df):
        out = self._blank(df)
        ef, es = ema(df["close"], self.fast), ema(df["close"], self.slow)
        up = (ef > es) & (ef.shift(1) <= es.shift(1))
        dn = (ef < es) & (ef.shift(1) >= es.shift(1))
        out["enter_long"], out["enter_short"], out["exit"] = up, dn, dn
        for ts in df.index[up]:
            out.at[ts, "reason"] = f"EMA{self.fast}={ef[ts]:.2f} crossed ABOVE EMA{self.slow}={es[ts]:.2f} (bullish)"
        for ts in df.index[dn]:
            out.at[ts, "reason"] = f"EMA{self.fast}={ef[ts]:.2f} crossed BELOW EMA{self.slow}={es[ts]:.2f} (bearish)"
        return out


@register
class SuperTrendStrategy(Strategy):
    name = "SuperTrend"
    period, mult = 10, 3.0
    sl_atr_mult, rr_ratio = 2.5, 2.0

    def generate_signals(self, df):
        out = self._blank(df)
        st, direction = supertrend(df, self.period, self.mult)
        up = (direction == 1) & (direction.shift(1) == -1)
        dn = (direction == -1) & (direction.shift(1) == 1)
        out["enter_long"], out["enter_short"], out["exit"] = up, dn, dn
        for ts in df.index[up]:
            out.at[ts, "reason"] = f"Price flipped ABOVE SuperTrend line ({st[ts]:.2f}) - uptrend"
        for ts in df.index[dn]:
            out.at[ts, "reason"] = f"Price flipped BELOW SuperTrend line ({st[ts]:.2f}) - downtrend"
        return out


@register
class RsiReversion(Strategy):
    name = "RSI Mean-Reversion"
    period, oversold, overbought = 14, 30, 70
    sl_atr_mult, rr_ratio = 2.0, 1.5

    def generate_signals(self, df):
        out = self._blank(df)
        r = rsi(df["close"], self.period)
        long_in = (r < self.oversold) & (r.shift(1) >= self.oversold)
        short_in = (r > self.overbought) & (r.shift(1) <= self.overbought)
        exit_mid = ((r > 50) & (r.shift(1) <= 50)) | ((r < 50) & (r.shift(1) >= 50))
        out["enter_long"], out["enter_short"], out["exit"] = long_in, short_in, exit_mid
        for ts in df.index[long_in]:
            out.at[ts, "reason"] = f"RSI={r[ts]:.1f} fell below {self.oversold} (oversold) - long"
        for ts in df.index[short_in]:
            out.at[ts, "reason"] = f"RSI={r[ts]:.1f} rose above {self.overbought} (overbought) - short"
        return out


@register
class BollingerBreakout(Strategy):
    name = "Bollinger Breakout"
    period, k = 20, 2.0
    sl_atr_mult, rr_ratio = 2.0, 2.5

    def generate_signals(self, df):
        out = self._blank(df)
        upper, mid, lower = bollinger(df["close"], self.period, self.k)
        c = df["close"]
        long_in = (c > upper) & (c.shift(1) <= upper.shift(1))
        short_in = (c < lower) & (c.shift(1) >= lower.shift(1))
        exit_mid = ((c < mid) & (c.shift(1) >= mid)) | ((c > mid) & (c.shift(1) <= mid))
        out["enter_long"], out["enter_short"], out["exit"] = long_in, short_in, exit_mid
        for ts in df.index[long_in]:
            out.at[ts, "reason"] = f"Close {c[ts]:.2f} broke ABOVE upper band {upper[ts]:.2f} - breakout"
        for ts in df.index[short_in]:
            out.at[ts, "reason"] = f"Close {c[ts]:.2f} broke BELOW lower band {lower[ts]:.2f} - breakdown"
        return out
