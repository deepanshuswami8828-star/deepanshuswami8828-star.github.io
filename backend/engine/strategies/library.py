"""The comprehensive strategy library.

Contains 40+ built-in strategies organized across 7 categories:
1. Trend-following
2. Mean-reversion
3. Momentum
4. Breakout / volatility
5. Volume-based
6. Multi-indicator combos
7. Candlestick / price-action

Each strategy carries rich metadata (category, description, rules_text, params) and generates
a human-readable reason with live indicator values for every trade signal.
"""
import pandas as pd
import numpy as np

from .base import Strategy, register
from indicators import (
    ema, sma, rsi, true_range, atr, adx, supertrend, bollinger, macd,
    parabolic_sar, ichimoku, donchian, keltner, ema_ribbon, vortex,
    heikin_ashi, linreg_slope, pivot_points, stochastic, stoch_rsi, cci,
    williams_r, roc, trix, awesome_oscillator, obv, mfi, cmf, vol_sma,
    rel_volume, zscore, bullish_engulfing, bearish_engulfing, hammer,
    shooting_star, doji, inside_bar, nr7
)


# =====================================================================
# A. TREND-FOLLOWING
# =====================================================================

@register
class EmaCrossover(Strategy):
    name = "EMA Crossover"
    category = "Trend-following"
    description = "Classic exponential moving average crossover trading momentum shifts."
    rules_text = "Long: EMA9 crosses above EMA21. Short/Exit: EMA9 crosses below EMA21."
    params = {"fast": 9, "slow": 21}
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
class SmaGoldenCross(Strategy):
    name = "SMA Golden/Death Cross"
    category = "Trend-following"
    description = "Slow, delivery-style macro trend follower using 50 and 200 period SMAs."
    rules_text = "Long: SMA50 crosses above SMA200 (Golden Cross). Short/Exit: SMA50 crosses below SMA200 (Death Cross)."
    params = {"fast": 50, "slow": 200}
    fast, slow = 50, 200
    sl_atr_mult, rr_ratio = 3.0, 3.0

    def generate_signals(self, df):
        out = self._blank(df)
        sf, ss = sma(df["close"], self.fast), sma(df["close"], self.slow)
        up = (sf > ss) & (sf.shift(1) <= ss.shift(1))
        dn = (sf < ss) & (sf.shift(1) >= ss.shift(1))
        out["enter_long"], out["enter_short"], out["exit"] = up, dn, dn
        for ts in df.index[up]:
            out.at[ts, "reason"] = f"Golden Cross: SMA50={sf[ts]:.2f} crossed ABOVE SMA200={ss[ts]:.2f}"
        for ts in df.index[dn]:
            out.at[ts, "reason"] = f"Death Cross: SMA50={sf[ts]:.2f} crossed BELOW SMA200={ss[ts]:.2f}"
        return out


@register
class MacdCrossover(Strategy):
    name = "MACD Crossover"
    category = "Trend-following"
    description = "Standard MACD line crossing above signal line with positive histogram confirmation."
    rules_text = "Long: MACD line crosses above signal line AND histogram > 0. Short/Exit: MACD line crosses below signal line."
    params = {"fast": 12, "slow": 26, "signal": 9}
    fast, slow, signal = 12, 26, 9
    sl_atr_mult, rr_ratio = 2.0, 2.0

    def generate_signals(self, df):
        out = self._blank(df)
        m_line, s_line, hist = macd(df["close"], self.fast, self.slow, self.signal)
        up = (m_line > s_line) & (m_line.shift(1) <= s_line.shift(1)) & (hist > 0)
        dn = (m_line < s_line) & (m_line.shift(1) >= s_line.shift(1))
        out["enter_long"], out["enter_short"], out["exit"] = up, dn, dn
        for ts in df.index[up]:
            out.at[ts, "reason"] = f"MACD={m_line[ts]:.2f} crossed ABOVE Signal={s_line[ts]:.2f} with Hist={hist[ts]:.2f}>0"
        for ts in df.index[dn]:
            out.at[ts, "reason"] = f"MACD={m_line[ts]:.2f} crossed BELOW Signal={s_line[ts]:.2f}"
        return out


@register
class SuperTrendStrategy(Strategy):
    name = "SuperTrend"
    category = "Trend-following"
    description = "ATR-based volatility trailing stop indicator riding strong directional moves."
    rules_text = "Long: Price flips above SuperTrend line. Short/Exit: Price flips below SuperTrend line."
    params = {"period": 10, "multiplier": 3.0}
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
class AdxDiTrend(Strategy):
    name = "ADX + DI Trend"
    category = "Trend-following"
    description = "Trend strength filter (ADX>=25) combined with directional indicator (+DI / -DI) crosses."
    rules_text = "Long: ADX >= 25 AND +DI crosses above -DI. Short: ADX >= 25 AND -DI crosses above +DI. Exit: DI cross back or ADX < 20."
    params = {"adx_period": 14, "adx_min": 25.0}
    adx_period, adx_min = 14, 25.0
    sl_atr_mult, rr_ratio = 2.0, 2.0

    def generate_signals(self, df):
        out = self._blank(df)
        adx_val, p_di, m_di = adx(df, self.adx_period)
        long_in = (adx_val >= self.adx_min) & (p_di > m_di) & (p_di.shift(1) <= m_di.shift(1))
        short_in = (adx_val >= self.adx_min) & (m_di > p_di) & (m_di.shift(1) <= p_di.shift(1))
        exit_sig = (adx_val < 20) | ((p_di < m_di) & (p_di.shift(1) >= m_di.shift(1)))
        out["enter_long"], out["enter_short"], out["exit"] = long_in, short_in, exit_sig
        for ts in df.index[long_in]:
            out.at[ts, "reason"] = f"+DI ({p_di[ts]:.1f}) crossed ABOVE -DI ({m_di[ts]:.1f}) with ADX={adx_val[ts]:.1f}>=25"
        for ts in df.index[short_in]:
            out.at[ts, "reason"] = f"-DI ({m_di[ts]:.1f}) crossed ABOVE +DI ({p_di[ts]:.1f}) with ADX={adx_val[ts]:.1f}>=25"
        return out


@register
class ParabolicSarFlip(Strategy):
    name = "Parabolic SAR Flip"
    category = "Trend-following"
    description = "Stop-and-reverse trailing indicator following price acceleration."
    rules_text = "Long: PSAR flips below price. Short/Exit: PSAR flips above price."
    params = {"af": 0.02, "max_af": 0.2}
    af, max_af = 0.02, 0.2
    sl_atr_mult, rr_ratio = 2.0, 2.0

    def generate_signals(self, df):
        out = self._blank(df)
        sar = parabolic_sar(df, self.af, self.max_af)
        c = df["close"]
        long_in = (c > sar) & (c.shift(1) <= sar.shift(1))
        short_in = (c < sar) & (c.shift(1) >= sar.shift(1))
        out["enter_long"], out["enter_short"], out["exit"] = long_in, short_in, short_in
        for ts in df.index[long_in]:
            out.at[ts, "reason"] = f"Price ({c[ts]:.2f}) flipped ABOVE Parabolic SAR ({sar[ts]:.2f})"
        for ts in df.index[short_in]:
            out.at[ts, "reason"] = f"Price ({c[ts]:.2f}) flipped BELOW Parabolic SAR ({sar[ts]:.2f})"
        return out


@register
class IchimokuCloud(Strategy):
    name = "Ichimoku Cloud"
    category = "Trend-following"
    description = "Comprehensive Japanese trend system utilizing Tenkan/Kijun cross confirmed by Kumo Cloud."
    rules_text = "Long: Close above cloud (max Senkou A/B) AND Tenkan crosses above Kijun. Short: Close below cloud AND Tenkan below Kijun. Exit: Price enters cloud."
    params = {"tenkan": 9, "kijun": 26, "senkou": 52}
    tenkan_n, kijun_n, senkou_n = 9, 26, 52
    sl_atr_mult, rr_ratio = 2.5, 2.0

    def generate_signals(self, df):
        out = self._blank(df)
        tenkan, kijun, senk_a, senk_b, _ = ichimoku(df, self.tenkan_n, self.kijun_n, self.senkou_n)
        c = df["close"]
        cloud_top = np.maximum(senk_a, senk_b)
        cloud_bot = np.minimum(senk_a, senk_b)

        long_in = (c > cloud_top) & (tenkan > kijun) & (tenkan.shift(1) <= kijun.shift(1))
        short_in = (c < cloud_bot) & (tenkan < kijun) & (tenkan.shift(1) >= kijun.shift(1))
        exit_sig = (c <= cloud_top) & (c >= cloud_bot)
        out["enter_long"], out["enter_short"], out["exit"] = long_in, short_in, exit_sig
        for ts in df.index[long_in]:
            out.at[ts, "reason"] = f"Tenkan ({tenkan[ts]:.2f}) crossed ABOVE Kijun ({kijun[ts]:.2f}) with Close ({c[ts]:.2f}) ABOVE Cloud ({cloud_top[ts]:.2f})"
        for ts in df.index[short_in]:
            out.at[ts, "reason"] = f"Tenkan ({tenkan[ts]:.2f}) crossed BELOW Kijun ({kijun[ts]:.2f}) with Close ({c[ts]:.2f}) BELOW Cloud ({cloud_bot[ts]:.2f})"
        return out


@register
class DonchianBreakout(Strategy):
    name = "Donchian Breakout (Turtle)"
    category = "Trend-following"
    description = "Classic Turtle Trading channel breakout system on 20-bar price extremes."
    rules_text = "Long: Close breaks above prior 20-bar high. Short/Exit: Close breaks below prior 20-bar low."
    params = {"period": 20}
    period = 20
    sl_atr_mult, rr_ratio = 2.0, 3.0

    def generate_signals(self, df):
        out = self._blank(df)
        upper, mid, lower = donchian(df, self.period)
        c = df["close"]
        prev_upper = upper.shift(1)
        prev_lower = lower.shift(1)

        long_in = (c > prev_upper) & (c.shift(1) <= prev_upper.shift(1))
        short_in = (c < prev_lower) & (c.shift(1) >= prev_lower.shift(1))
        out["enter_long"], out["enter_short"], out["exit"] = long_in, short_in, short_in
        for ts in df.index[long_in]:
            out.at[ts, "reason"] = f"Close ({c[ts]:.2f}) broke ABOVE 20-bar Donchian High ({prev_upper[ts]:.2f})"
        for ts in df.index[short_in]:
            out.at[ts, "reason"] = f"Close ({c[ts]:.2f}) broke BELOW 20-bar Donchian Low ({prev_lower[ts]:.2f})"
        return out


@register
class MaRibbon(Strategy):
    name = "Moving Average Ribbon"
    category = "Trend-following"
    description = "Multi-EMA ribbon alignment trading pristine multi-timeframe trend expansions."
    rules_text = "Long: EMAs fully stacked bullish (8>13>21>34>55). Short: EMAs fully stacked bearish. Exit: Ribbon order breaks."
    params = {"periods": [8, 13, 21, 34, 55]}
    sl_atr_mult, rr_ratio = 2.0, 2.5

    def generate_signals(self, df):
        out = self._blank(df)
        ribbon = ema_ribbon(df["close"], [8, 13, 21, 34, 55])
        e8, e13, e21, e34, e55 = ribbon[8], ribbon[13], ribbon[21], ribbon[34], ribbon[55]

        bull_stack = (e8 > e13) & (e13 > e21) & (e21 > e34) & (e34 > e55)
        bear_stack = (e8 < e13) & (e13 < e21) & (e21 < e34) & (e34 < e55)

        long_in = bull_stack & (~bull_stack.shift(1).fillna(False))
        short_in = bear_stack & (~bear_stack.shift(1).fillna(False))
        exit_sig = (~bull_stack) & (~bear_stack)

        out["enter_long"], out["enter_short"], out["exit"] = long_in, short_in, exit_sig
        for ts in df.index[long_in]:
            out.at[ts, "reason"] = f"EMA Ribbon fully stacked BULLISH (8={e8[ts]:.2f} > 13={e13[ts]:.2f} > ... > 55={e55[ts]:.2f})"
        for ts in df.index[short_in]:
            out.at[ts, "reason"] = f"EMA Ribbon fully stacked BEARISH (8={e8[ts]:.2f} < 13={e13[ts]:.2f} < ... < 55={e55[ts]:.2f})"
        return out


@register
class VortexCrossover(Strategy):
    name = "Vortex Crossover"
    category = "Trend-following"
    description = "Positive (+VI) and negative (-VI) vortex indicator trend direction crossover."
    rules_text = "Long: VI+ crosses above VI-. Short/Exit: VI- crosses above VI+."
    params = {"period": 14}
    period = 14
    sl_atr_mult, rr_ratio = 2.0, 2.0

    def generate_signals(self, df):
        out = self._blank(df)
        vi_p, vi_m = vortex(df, self.period)
        long_in = (vi_p > vi_m) & (vi_p.shift(1) <= vi_m.shift(1))
        short_in = (vi_m > vi_p) & (vi_m.shift(1) <= vi_p.shift(1))
        out["enter_long"], out["enter_short"], out["exit"] = long_in, short_in, short_in
        for ts in df.index[long_in]:
            out.at[ts, "reason"] = f"Vortex VI+ ({vi_p[ts]:.2f}) crossed ABOVE VI- ({vi_m[ts]:.2f})"
        for ts in df.index[short_in]:
            out.at[ts, "reason"] = f"Vortex VI- ({vi_m[ts]:.2f}) crossed ABOVE VI+ ({vi_p[ts]:.2f})"
        return out


@register
class HeikinAshiTrend(Strategy):
    name = "Heikin-Ashi Trend"
    category = "Trend-following"
    description = "Smoothed Heikin-Ashi candle color flips riding sustained price momentum."
    rules_text = "Long: HA candle turns green (HA_Close > HA_Open). Short/Exit: HA candle turns red."
    params = {}
    sl_atr_mult, rr_ratio = 2.0, 2.0

    def generate_signals(self, df):
        out = self._blank(df)
        ha_df = heikin_ashi(df)
        ha_c, ha_o = ha_df["ha_close"], ha_df["ha_open"]

        green = ha_c > ha_o
        red = ha_c < ha_o

        long_in = green & (red.shift(1).fillna(False))
        short_in = red & (green.shift(1).fillna(False))

        out["enter_long"], out["enter_short"], out["exit"] = long_in, short_in, short_in
        for ts in df.index[long_in]:
            out.at[ts, "reason"] = f"Heikin-Ashi turned GREEN (HA_Close={ha_c[ts]:.2f} > HA_Open={ha_o[ts]:.2f})"
        for ts in df.index[short_in]:
            out.at[ts, "reason"] = f"Heikin-Ashi turned RED (HA_Close={ha_c[ts]:.2f} < HA_Open={ha_o[ts]:.2f})"
        return out


@register
class LinRegSlopeStrategy(Strategy):
    name = "Linear Regression Slope"
    category = "Trend-following"
    description = "Mathematical linear regression slope of price crossing zero."
    rules_text = "Long: 20-bar Linear Regression Slope crosses above 0. Short/Exit: Slope crosses below 0."
    params = {"period": 20}
    period = 20
    sl_atr_mult, rr_ratio = 2.0, 2.0

    def generate_signals(self, df):
        out = self._blank(df)
        slope = linreg_slope(df["close"], self.period)
        long_in = (slope > 0) & (slope.shift(1) <= 0)
        short_in = (slope < 0) & (slope.shift(1) >= 0)
        out["enter_long"], out["enter_short"], out["exit"] = long_in, short_in, short_in
        for ts in df.index[long_in]:
            out.at[ts, "reason"] = f"LinReg Slope ({slope[ts]:.4f}) crossed ABOVE 0 (uptrend)"
        for ts in df.index[short_in]:
            out.at[ts, "reason"] = f"LinReg Slope ({slope[ts]:.4f}) crossed BELOW 0 (downtrend)"
        return out


# =====================================================================
# B. MEAN-REVERSION
# =====================================================================

@register
class RsiReversion(Strategy):
    name = "RSI Mean-Reversion"
    category = "Mean-reversion"
    description = "Oscillator oversold/overbought mean reversion strategy."
    rules_text = "Long: RSI < 30. Short: RSI > 70. Exit: RSI crosses 50."
    params = {"period": 14, "oversold": 30, "overbought": 70}
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
class Rsi2Connors(Strategy):
    name = "RSI-2 (Connors)"
    category = "Mean-reversion"
    description = "Larry Connors' aggressive short-term pullback buyer in a long-term uptrend."
    rules_text = "Long: Close > SMA200 AND RSI(2) < 10. Exit: Close > SMA5."
    params = {"rsi_period": 2, "trend_sma": 200, "exit_sma": 5}
    rsi_period, trend_sma, exit_sma = 2, 200, 5
    sl_atr_mult, rr_ratio = 2.0, 2.0

    def generate_signals(self, df):
        out = self._blank(df)
        c = df["close"]
        r2 = rsi(c, self.rsi_period)
        s200 = sma(c, self.trend_sma)
        s5 = sma(c, self.exit_sma)

        long_in = (c > s200) & (r2 < 10) & (r2.shift(1) >= 10)
        exit_sig = (c > s5) & (c.shift(1) <= s5.shift(1))

        out["enter_long"], out["exit"] = long_in, exit_sig
        for ts in df.index[long_in]:
            out.at[ts, "reason"] = f"Close ({c[ts]:.2f}) > SMA200 ({s200[ts]:.2f}) AND RSI(2)={r2[ts]:.1f} < 10 (extreme pullback)"
        return out


@register
class BollingerReversion(Strategy):
    name = "Bollinger Band Reversion"
    category = "Mean-reversion"
    description = "Counter-trend fade strategy trading price touches of outer Bollinger bands back to mean."
    rules_text = "Long: Close closes below lower band. Short: Close closes above upper band. Exit: Touch of mid SMA band."
    params = {"period": 20, "k": 2.0}
    period, k = 20, 2.0
    sl_atr_mult, rr_ratio = 1.5, 1.5

    def generate_signals(self, df):
        out = self._blank(df)
        upper, mid, lower = bollinger(df["close"], self.period, self.k)
        c = df["close"]
        long_in = (c < lower) & (c.shift(1) >= lower.shift(1))
        short_in = (c > upper) & (c.shift(1) <= upper.shift(1))
        exit_mid = ((c >= mid) & (c.shift(1) < mid.shift(1))) | ((c <= mid) & (c.shift(1) > mid.shift(1)))
        out["enter_long"], out["enter_short"], out["exit"] = long_in, short_in, exit_mid
        for ts in df.index[long_in]:
            out.at[ts, "reason"] = f"Close ({c[ts]:.2f}) closed BELOW lower band ({lower[ts]:.2f}) - mean reversion long"
        for ts in df.index[short_in]:
            out.at[ts, "reason"] = f"Close ({c[ts]:.2f}) closed ABOVE upper band ({upper[ts]:.2f}) - mean reversion short"
        return out


@register
class StochasticReversal(Strategy):
    name = "Stochastic Reversal"
    category = "Mean-reversion"
    description = "Stochastic %K and %D crossover in extreme oversold (<20) or overbought (>80) zones."
    rules_text = "Long: %K crosses above %D while both < 20. Short: %K crosses below %D while both > 80. Exit: Cross back through 50."
    params = {"k": 14, "d": 3, "smooth": 3}
    k, d_period, smooth = 14, 3, 3
    sl_atr_mult, rr_ratio = 2.0, 2.0

    def generate_signals(self, df):
        out = self._blank(df)
        stoch_k, stoch_d = stochastic(df, self.k, self.d_period, self.smooth)

        long_in = (stoch_k > stoch_d) & (stoch_k.shift(1) <= stoch_d.shift(1)) & (stoch_k < 20) & (stoch_d < 20)
        short_in = (stoch_k < stoch_d) & (stoch_k.shift(1) >= stoch_d.shift(1)) & (stoch_k > 80) & (stoch_d > 80)
        exit_sig = ((stoch_k > 50) & (stoch_k.shift(1) <= 50)) | ((stoch_k < 50) & (stoch_k.shift(1) >= 50))

        out["enter_long"], out["enter_short"], out["exit"] = long_in, short_in, exit_sig
        for ts in df.index[long_in]:
            out.at[ts, "reason"] = f"Stoch %K ({stoch_k[ts]:.1f}) crossed ABOVE %D ({stoch_d[ts]:.1f}) in oversold zone (<20)"
        for ts in df.index[short_in]:
            out.at[ts, "reason"] = f"Stoch %K ({stoch_k[ts]:.1f}) crossed BELOW %D ({stoch_d[ts]:.1f}) in overbought zone (>80)"
        return out


@register
class WilliamsRReversion(Strategy):
    name = "Williams %R Reversion"
    category = "Mean-reversion"
    description = "Williams %R momentum oscillator reversion out of overbought/oversold boundaries."
    rules_text = "Long: %R crosses up through -80. Short: %R crosses down through -20. Exit: Reaches mid level (-50)."
    params = {"period": 14}
    period = 14
    sl_atr_mult, rr_ratio = 2.0, 2.0

    def generate_signals(self, df):
        out = self._blank(df)
        wr = williams_r(df, self.period)
        long_in = (wr > -80) & (wr.shift(1) <= -80)
        short_in = (wr < -20) & (wr.shift(1) >= -20)
        exit_mid = ((wr > -50) & (wr.shift(1) <= -50)) | ((wr < -50) & (wr.shift(1) >= -50))

        out["enter_long"], out["enter_short"], out["exit"] = long_in, short_in, exit_mid
        for ts in df.index[long_in]:
            out.at[ts, "reason"] = f"Williams %R ({wr[ts]:.1f}) crossed UP through -80 (oversold recovery)"
        for ts in df.index[short_in]:
            out.at[ts, "reason"] = f"Williams %R ({wr[ts]:.1f}) crossed DOWN through -20 (overbought rejection)"
        return out


@register
class CciReversion(Strategy):
    name = "CCI Reversion"
    category = "Mean-reversion"
    description = "Commodity Channel Index mean-reversion entering from extreme statistical deviations."
    rules_text = "Long: CCI crosses above -100. Short: CCI crosses below +100. Exit: CCI crosses 0."
    params = {"period": 20}
    period = 20
    sl_atr_mult, rr_ratio = 2.0, 2.0

    def generate_signals(self, df):
        out = self._blank(df)
        c_val = cci(df, self.period)
        long_in = (c_val > -100) & (c_val.shift(1) <= -100)
        short_in = (c_val < 100) & (c_val.shift(1) >= 100)
        exit_sig = ((c_val > 0) & (c_val.shift(1) <= 0)) | ((c_val < 0) & (c_val.shift(1) >= 0))

        out["enter_long"], out["enter_short"], out["exit"] = long_in, short_in, exit_sig
        for ts in df.index[long_in]:
            out.at[ts, "reason"] = f"CCI ({c_val[ts]:.1f}) crossed ABOVE -100 (oversold recovery)"
        for ts in df.index[short_in]:
            out.at[ts, "reason"] = f"CCI ({c_val[ts]:.1f}) crossed BELOW +100 (overbought rejection)"
        return out


@register
class ZScoreReversion(Strategy):
    name = "Z-Score Mean Reversion"
    category = "Mean-reversion"
    description = "Statistical arbitrage Z-score reversion trading 2-standard-deviation price extremes."
    rules_text = "Long: Z-Score < -2.0. Short: Z-Score > +2.0. Exit: |Z-Score| < 0.5 (near mean)."
    params = {"period": 20}
    period = 20
    sl_atr_mult, rr_ratio = 1.5, 1.5

    def generate_signals(self, df):
        out = self._blank(df)
        zs = zscore(df["close"], self.period)
        long_in = (zs < -2.0) & (zs.shift(1) >= -2.0)
        short_in = (zs > 2.0) & (zs.shift(1) <= 2.0)
        exit_sig = zs.abs() < 0.5

        out["enter_long"], out["enter_short"], out["exit"] = long_in, short_in, exit_sig
        for ts in df.index[long_in]:
            out.at[ts, "reason"] = f"Z-Score ({zs[ts]:.2f}) fell below -2.0 (extreme statistical discount)"
        for ts in df.index[short_in]:
            out.at[ts, "reason"] = f"Z-Score ({zs[ts]:.2f}) rose above +2.0 (extreme statistical premium)"
        return out


# =====================================================================
# C. MOMENTUM
# =====================================================================

@register
class MacdHistMomentum(Strategy):
    name = "MACD Histogram Momentum"
    category = "Momentum"
    description = "Fast momentum strategy taking signals on MACD histogram zero-line crossovers."
    rules_text = "Long: MACD Histogram crosses above 0. Short/Exit: MACD Histogram crosses below 0."
    params = {"fast": 12, "slow": 26, "signal": 9}
    fast, slow, signal = 12, 26, 9
    sl_atr_mult, rr_ratio = 2.0, 2.0

    def generate_signals(self, df):
        out = self._blank(df)
        _, _, hist = macd(df["close"], self.fast, self.slow, self.signal)
        long_in = (hist > 0) & (hist.shift(1) <= 0)
        short_in = (hist < 0) & (hist.shift(1) >= 0)
        out["enter_long"], out["enter_short"], out["exit"] = long_in, short_in, short_in
        for ts in df.index[long_in]:
            out.at[ts, "reason"] = f"MACD Histogram ({hist[ts]:.2f}) crossed ABOVE 0 (bullish momentum acceleration)"
        for ts in df.index[short_in]:
            out.at[ts, "reason"] = f"MACD Histogram ({hist[ts]:.2f}) crossed BELOW 0 (bearish momentum acceleration)"
        return out


@register
class RocMomentum(Strategy):
    name = "Rate of Change (ROC)"
    category = "Momentum"
    description = "Pure percentage rate-of-change momentum zero-line crossover."
    rules_text = "Long: ROC(12) crosses above 0. Short/Exit: ROC(12) crosses below 0."
    params = {"period": 12}
    period = 12
    sl_atr_mult, rr_ratio = 2.0, 2.0

    def generate_signals(self, df):
        out = self._blank(df)
        r_val = roc(df["close"], self.period)
        long_in = (r_val > 0) & (r_val.shift(1) <= 0)
        short_in = (r_val < 0) & (r_val.shift(1) >= 0)
        out["enter_long"], out["enter_short"], out["exit"] = long_in, short_in, short_in
        for ts in df.index[long_in]:
            out.at[ts, "reason"] = f"ROC(12) ({r_val[ts]:.2f}%) crossed ABOVE 0"
        for ts in df.index[short_in]:
            out.at[ts, "reason"] = f"ROC(12) ({r_val[ts]:.2f}%) crossed BELOW 0"
        return out


@register
class AwesomeOscillatorStrategy(Strategy):
    name = "Awesome Oscillator"
    category = "Momentum"
    description = "Bill Williams' Awesome Oscillator median price momentum crossover."
    rules_text = "Long: AO crosses above 0. Short/Exit: AO crosses below 0."
    params = {}
    sl_atr_mult, rr_ratio = 2.0, 2.0

    def generate_signals(self, df):
        out = self._blank(df)
        ao_val = awesome_oscillator(df)
        long_in = (ao_val > 0) & (ao_val.shift(1) <= 0)
        short_in = (ao_val < 0) & (ao_val.shift(1) >= 0)
        out["enter_long"], out["enter_short"], out["exit"] = long_in, short_in, short_in
        for ts in df.index[long_in]:
            out.at[ts, "reason"] = f"Awesome Oscillator ({ao_val[ts]:.2f}) crossed ABOVE 0"
        for ts in df.index[short_in]:
            out.at[ts, "reason"] = f"Awesome Oscillator ({ao_val[ts]:.2f}) crossed BELOW 0"
        return out


@register
class StochRsiStrategy(Strategy):
    name = "StochRSI Momentum"
    category = "Momentum"
    description = "High-sensitivity Stochastic RSI momentum bounds breakout."
    rules_text = "Long: StochRSI crosses up from < 0.2. Short: StochRSI crosses down from > 0.8."
    params = {"n": 14, "k": 3, "d": 3}
    n, k, d_period = 14, 3, 3
    sl_atr_mult, rr_ratio = 2.0, 2.0

    def generate_signals(self, df):
        out = self._blank(df)
        sr_k, sr_d = stoch_rsi(df["close"], self.n, self.k, self.d_period)
        long_in = (sr_k > 0.2) & (sr_k.shift(1) <= 0.2)
        short_in = (sr_k < 0.8) & (sr_k.shift(1) >= 0.8)
        exit_sig = ((sr_k > 0.5) & (sr_k.shift(1) <= 0.5)) | ((sr_k < 0.5) & (sr_k.shift(1) >= 0.5))
        out["enter_long"], out["enter_short"], out["exit"] = long_in, short_in, exit_sig
        for ts in df.index[long_in]:
            out.at[ts, "reason"] = f"StochRSI %K ({sr_k[ts]:.2f}) crossed UP from oversold (<0.2)"
        for ts in df.index[short_in]:
            out.at[ts, "reason"] = f"StochRSI %K ({sr_k[ts]:.2f}) crossed DOWN from overbought (>0.8)"
        return out


@register
class TrixStrategy(Strategy):
    name = "TRIX Signal Crossover"
    category = "Momentum"
    description = "Triple-smoothed EMA TRIX indicator signal line crossover."
    rules_text = "Long: TRIX line crosses above signal line. Short/Exit: TRIX crosses below signal line."
    params = {"period": 15}
    period = 15
    sl_atr_mult, rr_ratio = 2.0, 2.0

    def generate_signals(self, df):
        out = self._blank(df)
        t_line, s_line = trix(df["close"], self.period)
        long_in = (t_line > s_line) & (t_line.shift(1) <= s_line.shift(1))
        short_in = (t_line < s_line) & (t_line.shift(1) >= s_line.shift(1))
        out["enter_long"], out["enter_short"], out["exit"] = long_in, short_in, short_in
        for ts in df.index[long_in]:
            out.at[ts, "reason"] = f"TRIX ({t_line[ts]:.4f}) crossed ABOVE Signal ({s_line[ts]:.4f})"
        for ts in df.index[short_in]:
            out.at[ts, "reason"] = f"TRIX ({t_line[ts]:.4f}) crossed BELOW Signal ({s_line[ts]:.4f})"
        return out


@register
class RelativeStrengthMomentumStub(Strategy):
    name = "Relative-Strength Momentum [needs multi-symbol]"
    category = "Momentum"
    description = "Ranks stocks by 90-day ROC to long the top decile. (Tagged: Requires multi-symbol comparison)."
    rules_text = "Long top decile ROC(90) stocks across multi-symbol universe. Stubbed on single-symbol OHLCV."
    params = {}
    is_stub = True

    def generate_signals(self, df):
        return self._blank(df)


# =====================================================================
# D. BREAKOUT / VOLATILITY
# =====================================================================

@register
class BollingerSqueezeBreakout(Strategy):
    name = "Bollinger Squeeze Breakout"
    category = "Breakout / volatility"
    description = "TTM Squeeze style volatility contraction followed by upper/lower Bollinger breakout."
    rules_text = "Long: Bands were inside Keltner channel (Squeeze) then price breaks above upper Bollinger band. Short: Breaks below lower band."
    params = {"bb_n": 20, "bb_k": 2.0, "kc_n": 20, "kc_mult": 1.5}
    bb_n, bb_k, kc_n, kc_mult = 20, 2.0, 20, 1.5
    sl_atr_mult, rr_ratio = 2.0, 2.5

    def generate_signals(self, df):
        out = self._blank(df)
        bb_upper, _, bb_lower = bollinger(df["close"], self.bb_n, self.bb_k)
        kc_upper, _, kc_lower = keltner(df, self.kc_n, 10, self.kc_mult)
        c = df["close"]

        squeeze = (bb_upper <= kc_upper) & (bb_lower >= kc_lower)
        was_squeezed = squeeze.shift(1).rolling(5).max() > 0

        long_in = was_squeezed & (c > bb_upper) & (c.shift(1) <= bb_upper.shift(1))
        short_in = was_squeezed & (c < bb_lower) & (c.shift(1) >= bb_lower.shift(1))
        out["enter_long"], out["enter_short"], out["exit"] = long_in, short_in, short_in
        for ts in df.index[long_in]:
            out.at[ts, "reason"] = f"Post-Squeeze Breakout: Close ({c[ts]:.2f}) broke ABOVE Upper Bollinger ({bb_upper[ts]:.2f})"
        for ts in df.index[short_in]:
            out.at[ts, "reason"] = f"Post-Squeeze Breakdown: Close ({c[ts]:.2f}) broke BELOW Lower Bollinger ({bb_lower[ts]:.2f})"
        return out


@register
class KeltnerChannelBreakout(Strategy):
    name = "Keltner Channel Breakout"
    category = "Breakout / volatility"
    description = "ATR-envelope channel breakout capturing strong trend expansion."
    rules_text = "Long: Close breaks above upper Keltner channel. Short: Below lower Keltner channel. Exit: Touch of EMA midline."
    params = {"ema_n": 20, "atr_n": 10, "mult": 2.0}
    ema_n, atr_n, mult = 20, 10, 2.0
    sl_atr_mult, rr_ratio = 2.0, 2.0

    def generate_signals(self, df):
        out = self._blank(df)
        upper, mid, lower = keltner(df, self.ema_n, self.atr_n, self.mult)
        c = df["close"]
        long_in = (c > upper) & (c.shift(1) <= upper.shift(1))
        short_in = (c < lower) & (c.shift(1) >= lower.shift(1))
        exit_mid = ((c <= mid) & (c.shift(1) > mid.shift(1))) | ((c >= mid) & (c.shift(1) < mid.shift(1)))
        out["enter_long"], out["enter_short"], out["exit"] = long_in, short_in, exit_mid
        for ts in df.index[long_in]:
            out.at[ts, "reason"] = f"Close ({c[ts]:.2f}) broke ABOVE Upper Keltner ({upper[ts]:.2f})"
        for ts in df.index[short_in]:
            out.at[ts, "reason"] = f"Close ({c[ts]:.2f}) broke BELOW Lower Keltner ({lower[ts]:.2f})"
        return out


@register
class AtrChannelBreakout(Strategy):
    name = "ATR Channel Breakout"
    category = "Breakout / volatility"
    description = "Adaptive ATR multiplier price move expansion."
    rules_text = "Long: Close > Previous Close + 1.5*ATR(14). Short: Close < Previous Close - 1.5*ATR(14)."
    params = {"period": 14, "k": 1.5}
    period, k = 14, 1.5
    sl_atr_mult, rr_ratio = 2.0, 2.0

    def generate_signals(self, df):
        out = self._blank(df)
        atr_val = atr(df, self.period)
        c = df["close"]
        prev_c = c.shift(1)

        long_in = c > (prev_c + self.k * atr_val)
        short_in = c < (prev_c - self.k * atr_val)
        out["enter_long"], out["enter_short"], out["exit"] = long_in, short_in, short_in
        for ts in df.index[long_in]:
            out.at[ts, "reason"] = f"Close ({c[ts]:.2f}) exceeded Previous Close + 1.5*ATR ({prev_c[ts] + 1.5*atr_val[ts]:.2f})"
        for ts in df.index[short_in]:
            out.at[ts, "reason"] = f"Close ({c[ts]:.2f}) fell below Previous Close - 1.5*ATR ({prev_c[ts] - 1.5*atr_val[ts]:.2f})"
        return out


@register
class Nr7InsideBarBreakout(Strategy):
    name = "NR7 / Inside-Bar Breakout"
    category = "Breakout / volatility"
    description = "Volatility contraction expansion buying next-bar breakout of NR7 or inside bar extreme."
    rules_text = "On NR7 or Inside Bar, buy next bar break of high; sell break of low."
    params = {}
    sl_atr_mult, rr_ratio = 1.5, 2.5

    def generate_signals(self, df):
        out = self._blank(df)
        is_ib = inside_bar(df)
        is_n7 = nr7(df)
        pattern = is_ib | is_n7

        prev_h = df["high"].shift(1)
        prev_l = df["low"].shift(1)
        c = df["close"]

        long_in = pattern.shift(1).fillna(False) & (c > prev_h)
        short_in = pattern.shift(1).fillna(False) & (c < prev_l)

        out["enter_long"], out["enter_short"], out["exit"] = long_in, short_in, short_in
        for ts in df.index[long_in]:
            out.at[ts, "reason"] = f"Price ({c[ts]:.2f}) broke ABOVE NR7/Inside-Bar high ({prev_h[ts]:.2f})"
        for ts in df.index[short_in]:
            out.at[ts, "reason"] = f"Price ({c[ts]:.2f}) broke BELOW NR7/Inside-Bar low ({prev_l[ts]:.2f})"
        return out


@register
class OrbBreakoutStub(Strategy):
    name = "Opening Range Breakout (ORB) [needs intraday]"
    category = "Breakout / volatility"
    description = "First 15/30-min range breakout. (Tagged: Requires intraday bars)."
    rules_text = "Long on break of first 15/30m range high, short on range low. Stubbed on daily OHLCV."
    params = {}
    is_stub = True

    def generate_signals(self, df):
        return self._blank(df)


@register
class DonchianDoubleBreakout(Strategy):
    name = "Donchian Double Breakout"
    category = "Breakout / volatility"
    description = "Dual-timeframe Donchian breakout entering on 20-bar breakout confirmed by 55-bar macro trend."
    rules_text = "Long: 20-bar Donchian breakout confirmed by Close > 55-bar Midline."
    params = {"fast_n": 20, "slow_n": 55}
    fast_n, slow_n = 20, 55
    sl_atr_mult, rr_ratio = 2.0, 3.0

    def generate_signals(self, df):
        out = self._blank(df)
        upper20, _, _ = donchian(df, self.fast_n)
        _, mid55, lower20 = donchian(df, self.slow_n)
        c = df["close"]

        long_in = (c > upper20.shift(1)) & (c > mid55)
        short_in = (c < lower20.shift(1)) & (c < mid55)
        out["enter_long"], out["enter_short"], out["exit"] = long_in, short_in, short_in
        for ts in df.index[long_in]:
            out.at[ts, "reason"] = f"Close ({c[ts]:.2f}) broke 20-bar High with 55-bar trend confirmation (> {mid55[ts]:.2f})"
        for ts in df.index[short_in]:
            out.at[ts, "reason"] = f"Close ({c[ts]:.2f}) broke 20-bar Low with 55-bar trend confirmation (< {mid55[ts]:.2f})"
        return out


# =====================================================================
# E. VOLUME-BASED
# =====================================================================

@register
class VolumeBreakout(Strategy):
    name = "Volume Breakout"
    category = "Volume-based"
    description = "Price 20-bar high/low breakout confirmed by > 2.0x average volume surge."
    rules_text = "Long: Close makes 20-bar high AND Volume > 2.0x 20-bar volume SMA. Short: 20-bar low on > 2.0x volume."
    params = {"period": 20, "vol_mult": 2.0}
    period, vol_mult = 20, 2.0
    sl_atr_mult, rr_ratio = 2.0, 2.5

    def generate_signals(self, df):
        out = self._blank(df)
        upper, _, lower = donchian(df, self.period)
        r_vol = rel_volume(df["volume"], self.period)
        c = df["close"]

        long_in = (c > upper.shift(1)) & (r_vol > self.vol_mult)
        short_in = (c < lower.shift(1)) & (r_vol > self.vol_mult)
        out["enter_long"], out["enter_short"], out["exit"] = long_in, short_in, short_in
        for ts in df.index[long_in]:
            out.at[ts, "reason"] = f"Price 20-bar High breakout with Relative Volume surge ({r_vol[ts]:.2f}x > 2.0x)"
        for ts in df.index[short_in]:
            out.at[ts, "reason"] = f"Price 20-bar Low breakdown with Relative Volume surge ({r_vol[ts]:.2f}x > 2.0x)"
        return out


@register
class ObvTrendConfirmation(Strategy):
    name = "OBV Trend Confirmation"
    category = "Volume-based"
    description = "On-Balance Volume 20-bar breakout confirming price channel breakout."
    rules_text = "Long: Price breaks 20-bar high AND OBV also breaks its 20-bar high. Exit: OBV rolls over."
    params = {"period": 20}
    period = 20
    sl_atr_mult, rr_ratio = 2.0, 2.0

    def generate_signals(self, df):
        out = self._blank(df)
        upper, _, _ = donchian(df, self.period)
        obv_val = obv(df)
        obv_upper = obv_val.rolling(self.period).max()
        c = df["close"]

        long_in = (c > upper.shift(1)) & (obv_val > obv_upper.shift(1))
        exit_sig = obv_val < obv_val.shift(1)
        out["enter_long"], out["exit"] = long_in, exit_sig
        for ts in df.index[long_in]:
            out.at[ts, "reason"] = f"Price 20-bar High confirmed by OBV new high ({obv_val[ts]:.0f})"
        return out


@register
class MfiStrategy(Strategy):
    name = "Money Flow Index (MFI)"
    category = "Volume-based"
    description = "Volume-weighted RSI oscillator overbought/oversold reversion."
    rules_text = "Long: MFI < 20 (oversold). Short: MFI > 80 (overbought). Exit: MFI crosses 50."
    params = {"period": 14, "oversold": 20, "overbought": 80}
    period, oversold, overbought = 14, 20, 80
    sl_atr_mult, rr_ratio = 2.0, 2.0

    def generate_signals(self, df):
        out = self._blank(df)
        m_val = mfi(df, self.period)
        long_in = (m_val < self.oversold) & (m_val.shift(1) >= self.oversold)
        short_in = (m_val > self.overbought) & (m_val.shift(1) <= self.overbought)
        exit_sig = ((m_val > 50) & (m_val.shift(1) <= 50)) | ((m_val < 50) & (m_val.shift(1) >= 50))
        out["enter_long"], out["enter_short"], out["exit"] = long_in, short_in, exit_sig
        for ts in df.index[long_in]:
            out.at[ts, "reason"] = f"MFI ({m_val[ts]:.1f}) fell below oversold boundary (<20)"
        for ts in df.index[short_in]:
            out.at[ts, "reason"] = f"MFI ({m_val[ts]:.1f}) rose above overbought boundary (>80)"
        return out


@register
class CmfStrategy(Strategy):
    name = "Chaikin Money Flow (CMF)"
    category = "Volume-based"
    description = "Accumulation/distribution money flow zero-line crossover."
    rules_text = "Long: CMF crosses above 0. Short/Exit: CMF crosses below 0."
    params = {"period": 20}
    period = 20
    sl_atr_mult, rr_ratio = 2.0, 2.0

    def generate_signals(self, df):
        out = self._blank(df)
        c_val = cmf(df, self.period)
        long_in = (c_val > 0) & (c_val.shift(1) <= 0)
        short_in = (c_val < 0) & (c_val.shift(1) >= 0)
        out["enter_long"], out["enter_short"], out["exit"] = long_in, short_in, short_in
        for ts in df.index[long_in]:
            out.at[ts, "reason"] = f"CMF ({c_val[ts]:.2f}) crossed ABOVE 0 (accumulation surge)"
        for ts in df.index[short_in]:
            out.at[ts, "reason"] = f"CMF ({c_val[ts]:.2f}) crossed BELOW 0 (distribution pressure)"
        return out


@register
class VwapReversionStub(Strategy):
    name = "VWAP Reversion / Trend [needs intraday]"
    category = "Volume-based"
    description = "Intraday session VWAP band bounce/breakout. (Tagged: Requires intraday data)."
    rules_text = "Trade intraday price bounces off VWAP +/- stddev bands. Stubbed on daily OHLCV."
    params = {}
    is_stub = True

    def generate_signals(self, df):
        return self._blank(df)


# =====================================================================
# F. MULTI-INDICATOR COMBOS
# =====================================================================

@register
class EmaCrossRsiFilter(Strategy):
    name = "EMA Cross + RSI Filter"
    category = "Multi-indicator combos"
    description = "Dual-confirmation trend strategy requiring RSI > 50 momentum to validate EMA crossover."
    rules_text = "Long: EMA9 crosses above EMA21 AND RSI(14) > 50. Short: EMA9 crosses below EMA21 AND RSI(14) < 50."
    params = {"fast": 9, "slow": 21, "rsi_n": 14}
    fast, slow, rsi_n = 9, 21, 14
    sl_atr_mult, rr_ratio = 2.0, 2.0

    def generate_signals(self, df):
        out = self._blank(df)
        ef, es = ema(df["close"], self.fast), ema(df["close"], self.slow)
        r_val = rsi(df["close"], self.rsi_n)

        long_in = (ef > es) & (ef.shift(1) <= es.shift(1)) & (r_val > 50)
        short_in = (ef < es) & (ef.shift(1) >= es.shift(1)) & (r_val < 50)
        out["enter_long"], out["enter_short"], out["exit"] = long_in, short_in, short_in
        for ts in df.index[long_in]:
            out.at[ts, "reason"] = f"EMA9/21 bullish cross confirmed by RSI({r_val[ts]:.1f}) > 50"
        for ts in df.index[short_in]:
            out.at[ts, "reason"] = f"EMA9/21 bearish cross confirmed by RSI({r_val[ts]:.1f}) < 50"
        return out


@register
class MacdRsiCombo(Strategy):
    name = "MACD + RSI Combo"
    category = "Multi-indicator combos"
    description = "High-probability trend entry combining MACD line cross with RSI trend side."
    rules_text = "Long: MACD crosses above signal line AND RSI > 50. Short: MACD crosses below signal line AND RSI < 50."
    params = {"fast": 12, "slow": 26, "signal": 9, "rsi_n": 14}
    fast, slow, signal, rsi_n = 12, 26, 9, 14
    sl_atr_mult, rr_ratio = 2.0, 2.0

    def generate_signals(self, df):
        out = self._blank(df)
        m_line, s_line, _ = macd(df["close"], self.fast, self.slow, self.signal)
        r_val = rsi(df["close"], self.rsi_n)

        long_in = (m_line > s_line) & (m_line.shift(1) <= s_line.shift(1)) & (r_val > 50)
        short_in = (m_line < s_line) & (m_line.shift(1) >= s_line.shift(1)) & (r_val < 50)
        out["enter_long"], out["enter_short"], out["exit"] = long_in, short_in, short_in
        for ts in df.index[long_in]:
            out.at[ts, "reason"] = f"MACD bull cross with RSI({r_val[ts]:.1f}) > 50"
        for ts in df.index[short_in]:
            out.at[ts, "reason"] = f"MACD bear cross with RSI({r_val[ts]:.1f}) < 50"
        return out


@register
class SuperTrendEma200(Strategy):
    name = "SuperTrend + EMA200 Filter"
    category = "Multi-indicator combos"
    description = "Macro-filtered SuperTrend taking longs only above EMA200 and shorts only below."
    rules_text = "Long: SuperTrend flips bullish AND Close > EMA200. Short: SuperTrend flips bearish AND Close < EMA200."
    params = {"st_period": 10, "st_mult": 3.0, "ema_n": 200}
    st_period, st_mult, ema_n = 10, 3.0, 200
    sl_atr_mult, rr_ratio = 2.5, 2.0

    def generate_signals(self, df):
        out = self._blank(df)
        st, direction = supertrend(df, self.st_period, self.st_mult)
        e200 = ema(df["close"], self.ema_n)
        c = df["close"]

        long_in = (direction == 1) & (direction.shift(1) == -1) & (c > e200)
        short_in = (direction == -1) & (direction.shift(1) == 1) & (c < e200)
        out["enter_long"], out["enter_short"], out["exit"] = long_in, short_in, short_in
        for ts in df.index[long_in]:
            out.at[ts, "reason"] = f"SuperTrend bullish flip confirmed by Close ({c[ts]:.2f}) > EMA200 ({e200[ts]:.2f})"
        for ts in df.index[short_in]:
            out.at[ts, "reason"] = f"SuperTrend bearish flip confirmed by Close ({c[ts]:.2f}) < EMA200 ({e200[ts]:.2f})"
        return out


@register
class FourFactorConfluence(Strategy):
    name = "4-Factor Confluence (200SMA + 20EMA + MACD + Cloud)"
    category = "Multi-indicator combos"
    description = "Institutional scoring system (0 to 4 factors) requiring >=3 bullish factors to enter."
    rules_text = "Score 4 factors: Close>200SMA (+1), Close>20EMA (+1), MACD>Signal (+1), Close>Cloud (+1). Long if score >= 3; exit if score <= 1."
    params = {}
    sl_atr_mult, rr_ratio = 2.0, 2.0

    def generate_signals(self, df):
        out = self._blank(df)
        c = df["close"]
        s200 = sma(c, 200)
        e20 = ema(c, 20)
        m_line, s_line, _ = macd(c, 12, 26, 9)
        _, _, senk_a, senk_b, _ = ichimoku(df, 9, 26, 52)
        cloud_top = np.maximum(senk_a, senk_b)

        f1 = (c > s200).astype(int)
        f2 = (c > e20).astype(int)
        f3 = (m_line > s_line).astype(int)
        f4 = (c > cloud_top).astype(int)

        score = f1 + f2 + f3 + f4
        long_in = (score >= 3) & (score.shift(1) < 3)
        exit_sig = score <= 1

        out["enter_long"], out["exit"] = long_in, exit_sig
        for ts in df.index[long_in]:
            out.at[ts, "reason"] = f"Bullish Confluence Score = {score[ts]}/4 (200SMA={f1[ts]}, 20EMA={f2[ts]}, MACD={f3[ts]}, Cloud={f4[ts]})"
        return out


@register
class TripleScreenElderStub(Strategy):
    name = "Triple Screen (Elder) [needs MTF]"
    category = "Multi-indicator combos"
    description = "Dr. Alexander Elder's Triple Screen MTF system. (Tagged: Requires multi-timeframe plumbing)."
    rules_text = "Weekly trend sets direction, daily oscillator times entry. Stubbed on single-timeframe daily."
    params = {}
    is_stub = True

    def generate_signals(self, df):
        return self._blank(df)


# =====================================================================
# G. CANDLESTICK / PRICE-ACTION
# =====================================================================

@register
class EngulfingPattern(Strategy):
    name = "Bullish/Bearish Engulfing"
    category = "Candlestick / price-action"
    description = "Classic 2-bar price action reversal engulfing pattern."
    rules_text = "Long: Bullish Engulfing pattern. Short: Bearish Engulfing pattern."
    params = {}
    sl_atr_mult, rr_ratio = 1.5, 2.0

    def generate_signals(self, df):
        out = self._blank(df)
        bull = bullish_engulfing(df)
        bear = bearish_engulfing(df)

        long_in = bull & (~bull.shift(1).fillna(False))
        short_in = bear & (~bear.shift(1).fillna(False))

        out["enter_long"], out["enter_short"], out["exit"] = long_in, short_in, short_in
        for ts in df.index[long_in]:
            out.at[ts, "reason"] = f"Bullish Engulfing pattern detected (Close={df['close'][ts]:.2f} > Prev Open={df['open'].shift(1)[ts]:.2f})"
        for ts in df.index[short_in]:
            out.at[ts, "reason"] = f"Bearish Engulfing pattern detected (Close={df['close'][ts]:.2f} < Prev Open={df['open'].shift(1)[ts]:.2f})"
        return out


@register
class HammerShootingStar(Strategy):
    name = "Hammer / Shooting Star"
    category = "Candlestick / price-action"
    description = "Single-candle rejection pattern (Hammer at lows, Shooting Star at highs)."
    rules_text = "Long: Hammer candle after down move (Close < EMA20). Short: Shooting Star candle after up move (Close > EMA20)."
    params = {"ema_n": 20}
    ema_n = 20
    sl_atr_mult, rr_ratio = 1.5, 2.0

    def generate_signals(self, df):
        out = self._blank(df)
        h_cand = hammer(df)
        ss_cand = shooting_star(df)
        e20 = ema(df["close"], self.ema_n)
        c = df["close"]

        long_in = h_cand & (c < e20)
        short_in = ss_cand & (c > e20)

        out["enter_long"], out["enter_short"], out["exit"] = long_in, short_in, short_in
        for ts in df.index[long_in]:
            out.at[ts, "reason"] = f"Hammer rejection candle below EMA20 (Low={df['low'][ts]:.2f})"
        for ts in df.index[short_in]:
            out.at[ts, "reason"] = f"Shooting Star rejection candle above EMA20 (High={df['high'][ts]:.2f})"
        return out


@register
class PivotPointBounce(Strategy):
    name = "Pivot Point Bounce/Breakout"
    category = "Candlestick / price-action"
    description = "Classic floor pivot points (PP, R1, S1, R2, S2) support bounce and resistance breakout."
    rules_text = "Long: Low touches/bounces off S1 and Close > S1. Short: High touches/rejected at R1 and Close < R1."
    params = {}
    sl_atr_mult, rr_ratio = 1.5, 2.0

    def generate_signals(self, df):
        out = self._blank(df)
        pp, r1, s1, r2, s2 = pivot_points(df)
        l, h, c = df["low"], df["high"], df["close"]

        long_in = (l <= s1) & (c > s1) & (c.shift(1) <= s1.shift(1))
        short_in = (h >= r1) & (c < r1) & (c.shift(1) >= r1.shift(1))

        out["enter_long"], out["enter_short"], out["exit"] = long_in, short_in, short_in
        for ts in df.index[long_in]:
            out.at[ts, "reason"] = f"Price bounced off Pivot S1 support level ({s1[ts]:.2f})"
        for ts in df.index[short_in]:
            out.at[ts, "reason"] = f"Price rejected at Pivot R1 resistance level ({r1[ts]:.2f})"
        return out
