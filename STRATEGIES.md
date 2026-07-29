# STRATEGIES.md — BacktestLab strategy library to implement

## Agent instructions (read first)
Implement everything in this file. Steps:
1. **Add indicators** from the "Indicators to add" section to `indicators.py` — pure
   pandas/numpy, all **backward-looking** (no look-ahead). Reuse existing ones.
2. **Register every strategy** in the "Strategy catalog" as a proper built-in strategy in
   `strategies/` using the same pattern as the existing 4 (EMA Crossover, SuperTrend, RSI
   Mean-Reversion, Bollinger Breakout). Each strategy MUST carry metadata: `name`,
   `category`, one-line `description`, `rules_text` (the exact entry/exit rules in plain
   English), and default `params`. Every trade's `entry_reason` must state the rule that
   actually fired (with the live indicator values, like the existing strategies do).
3. **Skip-or-stub** anything tagged `[needs intraday]`, `[needs MTF]`, or
   `[needs multi-symbol]` if that data/plumbing isn't available yet. Implement all the
   plain **daily-OHLCV** strategies now.
4. **Expose metadata:** `GET /strategies` returns the metadata; the frontend shows each
   strategy with an info popover (category, description, rules, params) and groups the
   multi-select **by category**.
5. **Expand the no-code Build-Strategy whitelist** to include every new indicator + operator
   so users can compose these (and more) themselves.
6. **Data — all NSE stocks:** see the last section.

Honesty: these are templates, not guaranteed money-makers. A backtest is research, not a
prediction; results overfit easily. Keep costs + look-ahead handling exactly as the engine
already does.

---

## Indicators to add
Trend / channels: `macd(close, fast=12, slow=26, signal=9)` -> (macd, signal, hist);
`parabolic_sar(df, af=0.02, max_af=0.2)`; `ichimoku(df, 9, 26, 52)` -> tenkan, kijun,
senkou_a, senkou_b, chikou; `donchian(df, n=20)` -> upper, mid, lower;
`keltner(df, ema_n=20, atr_n=10, mult=2.0)` -> upper, mid, lower;
`ema_ribbon(close, [8,13,21,34,55])`; `vortex(df, n=14)` -> vi_plus, vi_minus;
`heikin_ashi(df)` -> ha_open/high/low/close; `linreg_slope(close, n=20)`;
`pivot_points(df)` (classic, from prior period H/L/C) -> pp, r1, s1, r2, s2.

Oscillators / momentum: `stochastic(df, k=14, d=3, smooth=3)` -> %K, %D;
`stoch_rsi(close, n=14, k=3, d=3)`; `cci(df, n=20)`; `williams_r(df, n=14)`;
`roc(close, n=12)`; `trix(close, n=15)` -> trix, signal;
`awesome_oscillator(df)` (median-price SMA5 - SMA34).

Volume: `obv(df)`; `mfi(df, n=14)`; `cmf(df, n=20)`; `vwap(df)` `[needs intraday]`;
`vol_sma(volume, n=20)`; `rel_volume = volume / vol_sma`.

Stats / helpers: `zscore(close, n=20)`; candlestick detectors returning bool Series:
`bullish_engulfing(df)`, `bearish_engulfing(df)`, `hammer(df)`, `shooting_star(df)`,
`doji(df)`, `inside_bar(df)`, `nr7(df)` (narrowest range of last 7).

Tricky-ones notes: Stochastic %K = 100*(close - LL_k)/(HH_k - LL_k), %D = SMA(%K, d).
Parabolic SAR is iterative (track EP + AF, flip on penetration). Ichimoku senkou spans are
plotted 26 ahead — when USING them as a signal, compare price to the span value valid at the
current bar (do not read future-shifted values into the past). Vortex uses TR and directional
movement sums. Keep all of these causal.

---

## Strategy catalog

### A. Trend-following
1. **EMA Crossover** (exists) — EMA. Long: EMA9 crosses above EMA21. Short/Exit: crosses below.
2. **SMA Golden/Death Cross** — SMA. Long: SMA50 crosses above SMA200 (golden cross).
   Short/Exit: SMA50 crosses below SMA200 (death cross). Params: 50/200. Slow, delivery-style.
3. **MACD Crossover** — MACD(12,26,9). Long: MACD line crosses above signal AND hist>0.
   Short/Exit: MACD crosses below signal. 
4. **SuperTrend** (exists) — SuperTrend(10,3). Long on flip above, short on flip below.
5. **ADX + DI Trend** — ADX(14). Long: ADX>=25 AND +DI crosses above -DI. Short: ADX>=25 AND
   -DI crosses above +DI. Exit: DI cross back or ADX<20.
6. **Parabolic SAR Flip** — PSAR(0.02,0.2). Long: SAR flips to below price. Short: SAR flips
   above price. Exit: opposite flip. Natural trailing stop = SAR.
7. **Ichimoku Cloud** — Ichimoku(9,26,52). Long: close above cloud (max senkA/senkB) AND
   Tenkan crosses above Kijun. Short: close below cloud AND Tenkan below Kijun. Exit: price
   re-enters cloud.
8. **Donchian Breakout (Turtle-style)** — Donchian(20). Long: close breaks above prior 20-bar
   high. Short/Exit: close breaks below prior 20-bar low. Params: 20 entry / 10 exit optional.
9. **Moving Average Ribbon** — EMA ribbon [8,13,21,34,55]. Long: ribbon fully stacked bullish
   (8>13>21>34>55) and price above. Short: fully bearish stack. Exit: stack breaks.
10. **Vortex Crossover** — Vortex(14). Long: VI+ crosses above VI-. Short: VI- crosses above VI+.
11. **Heikin-Ashi Trend** — Heikin-Ashi. Long: HA turns/stays green after a red (flat-bottom
    candles). Short: HA turns red. Exit: opposite color flip. Smoother trend rider.
12. **Linear Regression Slope** — linreg_slope(20). Long: slope crosses above 0 (uptilt).
    Short: slope crosses below 0.

### B. Mean-reversion
13. **RSI Mean-Reversion** (exists) — RSI(14). Long <30, short >70, exit at 50.
14. **RSI-2 (Connors)** — RSI(2) + SMA200. Long: close>SMA200 AND RSI(2)<10. Exit: close>SMA5.
    (Short-term pullback buyer in an uptrend.) Long-only by default.
15. **Bollinger Band Reversion** — Bollinger(20,2). Long: close closes below lower band (fade).
    Short: close above upper band. Exit: touch of the mid band. (Range-market fade — opposite
    of the existing Bollinger Breakout.)
16. **Stochastic Reversal** — Stochastic(14,3,3). Long: %K crosses above %D while both <20.
    Short: %K crosses below %D while both >80. Exit: cross back through 50.
17. **Williams %R** — Williams %R(14). Long: %R crosses up through -80 (oversold). Short: %R
    crosses down through -20 (overbought). Exit: mid (-50).
18. **CCI Reversion** — CCI(20). Long: CCI crosses above -100 from below. Short: CCI crosses
    below +100 from above. Exit: CCI crosses 0.
19. **Z-Score Mean Reversion** — zscore(20). Long: z < -2. Short: z > +2. Exit: |z| < 0.5.

### C. Momentum
20. **MACD Histogram Momentum** — MACD hist. Long: hist crosses above 0. Short: hist crosses
    below 0. (Faster than the MACD-line cross.)
21. **Rate of Change (ROC)** — ROC(12). Long: ROC crosses above 0. Short: below 0.
22. **Awesome Oscillator** — AO. Long: AO crosses above 0 (or bullish saucer). Short: below 0.
23. **StochRSI** — StochRSI(14,3,3). Long: crosses up from <0.2. Short: crosses down from >0.8.
24. **TRIX** — TRIX(15). Long: TRIX crosses above its signal line (and >0). Short: below.
25. **Relative-Strength Momentum** `[needs multi-symbol]` — rank stocks by ROC(90); long the
    top decile, exit when it drops out. (Works in the cross-stock/compare mode, not a single
    single-symbol backtest.)

### D. Breakout / volatility
26. **Bollinger Squeeze Breakout** — Bollinger(20,2) + Keltner(20,1.5). Long: bands were inside
    Keltner (squeeze) then close breaks above upper Bollinger. Short: breaks below lower.
    (Classic TTM-style squeeze.)
27. **Keltner Channel Breakout** — Keltner(20,10,2). Long: close breaks above upper channel.
    Short: below lower. Exit: back to mid (EMA).
28. **ATR Channel Breakout** — ATR(14). Long: close > previous close + k*ATR (k=1.5).
    Short: close < previous close - k*ATR.
29. **NR7 / Inside-Bar Breakout** — nr7 / inside_bar. On an NR7 or inside bar, buy a break of
    that bar's high next bar; sell a break of its low. (Volatility-contraction breakout.)
30. **Opening Range Breakout (ORB)** `[needs intraday]` — first 15/30-min range of the session;
    long on break of range high, short on range low; exit at session close.
31. **Donchian Double Breakout** — Donchian. Enter on the 20-bar breakout; use a 55-bar breakout
    as a longer-trend confirmation filter.

### E. Volume-based
32. **Volume Breakout** — rel_volume. Long: close makes a 20-bar high AND volume > 2x its
    20-bar average. Short: 20-bar low on high volume.
33. **OBV Trend Confirmation** — OBV. Long: price breaks a 20-bar high AND OBV also breaks its
    own 20-bar high (volume confirms). Exit: OBV rolls over.
34. **Money Flow Index (MFI)** — MFI(14). Long <20 (oversold). Short >80 (overbought). Exit 50.
35. **Chaikin Money Flow (CMF)** — CMF(20). Long: CMF crosses above 0. Short: below 0.
36. **VWAP Reversion / Trend** `[needs intraday]` — long bounces off VWAP - band, short off
    VWAP + band during the session; or trade in the direction of price-vs-VWAP.

### F. Multi-indicator combos (higher-conviction)
37. **EMA Cross + RSI filter** — Long only when EMA9>EMA21 cross AND RSI(14)>50 (momentum
    confirms trend). Short mirror.
38. **MACD + RSI** — Long: MACD crosses above signal AND RSI>50. Short: MACD below signal AND RSI<50.
39. **SuperTrend + EMA200 filter** — Take SuperTrend long signals only when close>EMA200; shorts
    only when close<EMA200 (trade with the higher-timeframe-ish trend).
40. **200SMA + 20EMA + MACD + Ichimoku Confluence** — score bullish/bearish confluence: above
    200SMA (+1), above 20EMA (+1), bullish MACD cross (+1), above Ichimoku cloud (+1). Long when
    score>=3; exit when score<=1. Short mirror.
41. **Triple Screen (Elder)** `[needs MTF]` — weekly trend (MACD/EMA) sets direction, daily
    oscillator (Stochastic/Force) times entry. Needs multi-timeframe plumbing.

### G. Candlestick / price-action
42. **Bullish/Bearish Engulfing** — engulfing detectors. Long on a bullish engulfing at/after a
    downswing (e.g., near lower Bollinger or after 3 down closes). Short on bearish engulfing.
43. **Hammer / Shooting Star** — hammer/shooting_star. Long on a hammer after a downtrend
    (below EMA/oversold RSI). Short on a shooting star after an uptrend.
44. **Pivot Point Bounce/Breakout** — classic pivots. Long on bounce off S1/S2 (or breakout
    above R1); short on rejection at R1/R2. (Uses prior period's H/L/C — daily pivots for
    intraday, or weekly pivots for daily bars.)

---

## Out of scope (be honest — don't fake these)
These can't be backtested reliably with plain OHLCV alone; skip, or mark as "coming later":
- **Fibonacci retracement / Elliott / harmonic patterns** — need discretionary swing/pattern
  detection; not mechanically well-defined.
- **Pairs / statistical-arbitrage / cointegration (Kalman)** — need 2+ symbols and portfolio
  logic (partly enabled by the multi-symbol compare mode later).
- **Order flow / tape reading / market profile / options flow / DOM** — need level-2 / tick /
  options data, not OHLCV.
- **News / sentiment / event-driven** — need an external news/sentiment feed.
- **ML / regression-prediction strategies** — separate modeling pipeline; out of this rules
  engine's scope.

---

## Data — all NSE stocks
- Seed the **full NSE equity list** (symbol, name, series) into the `stocks` table so EVERY
  NSE stock is searchable in the UI from day one. Provide a `seed_stocks` script/endpoint to
  refresh it (bundle a CSV fallback if a live list isn't reachable).
- Do **NOT** bulk-download all ~2000 symbols' history (rate limits + hours + storage). Fetch a
  symbol's price history **lazily on its first backtest** and cache it in durable storage
  (Postgres `price_bars` table or Parquet in object storage), then only append new bars via the
  daily update job. Expose per-symbol data freshness (first_bar / last_bar / last_updated).
- Optional: a "pre-warm Nifty 50" script so the popular names are instant.
