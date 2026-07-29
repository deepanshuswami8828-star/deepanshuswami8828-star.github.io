# AI Trading Research & Backtesting Platform

Choose a stock, a date range and a timeframe. The platform pulls the historical
data, runs **every** strategy on the same data at once, and produces one PDF that
compares them - with full stats and a complete trade log (every trade shows its
entry/exit, stop-loss, target, P&L, and the exact reason it was taken).

## What it does
- One command runs all strategies together and ranks them by net P&L.
- Professional stats per strategy: win rate, profit factor, reward:risk,
  expectancy, max drawdown, Sharpe, CAGR, streaks, avg win/loss, total charges.
- **Realistic Indian costs** (brokerage, STT, exchange txn, GST, SEBI, stamp) +
  slippage applied to every trade - so P&L is net, not fantasy.
- **Look-ahead safe**: signals form on bar `t`, fills happen at bar `t+1` open.
- **Market-regime tagging**: see which strategy wins in trending vs ranging vs
  volatile conditions.
- **Pluggable strategies**: add one file, it appears everywhere automatically.
- **Daily auto-update**: a scheduled job appends each day's data to a local cache.

## Setup
```bash
pip install -r requirements.txt
```

## Run it
```bash
# 1) Try it instantly with synthetic data (no internet, no API):
python run.py --demo

# 2) Real data (free daily/EOD via yfinance). Edit CONFIG in run.py, or:
python run.py --symbol RELIANCE --start 2023-01-01 --end 2025-01-01 --interval 1d
```
Output: a PDF like `backtest_report_RELIANCE_YYYY-MM-DD.pdf` in the folder.

## Choosing what to test
Open `run.py` and edit the `CONFIG` block at the top: `symbol`, `start`, `end`,
`interval`, `capital_per_trade`, `segment` (`intraday`/`delivery`), and `only`
(a list to run a subset, or `None` for all).

## Data & daily automation
- `data.py` fetches OHLCV and caches it to `cache/*.parquet`. It hits the network
  only for dates you don't already have; everything else is read from disk.
- `daily_update.py` appends each trading day's new bar for your `WATCHLIST`.
  Schedule it (commands are inside the file):
  - Windows: Task Scheduler
  - Linux/Mac: cron

### Free daily vs paid intraday
Free `yfinance` is fine for **daily** bars. For reliable **intraday** NSE data,
replace the body of `fetch_raw()` in `data.py` with a broker API (the rest of the
platform is unchanged). Zerodha Kite Connect is the usual choice - as of 2025 its
paid plan (~Rs 500/month) bundles historical intraday data (up to ~10 years).
Angel One SmartAPI and Dhan offer free-ish alternatives. Note: broker data is
licensed for your own use, not for redistribution.

## Add your own strategy (this is the point of the design)
Create `strategies/my_strategy.py`:
```python
from .base import Strategy, register
from indicators import ema

@register
class MyStrategy(Strategy):
    name = "My Strategy"
    sl_atr_mult, rr_ratio = 2.0, 2.0   # engine sets stop/target from these

    def generate_signals(self, df):
        out = self._blank(df)
        fast, slow = ema(df["close"], 5), ema(df["close"], 20)
        cross = (fast > slow) & (fast.shift(1) <= slow.shift(1))
        out["enter_long"] = cross
        for ts in df.index[cross]:
            out.at[ts, "reason"] = "my rule fired here"
        return out
```
Then add `from . import my_strategy` to `strategies/__init__.py`. Done - it now
shows up in the leaderboard, the charts, the regime breakdown and the trade log.

## Files
| File | Role |
|------|------|
| `run.py` | choose + run everything + build the PDF |
| `data.py` | fetch + cache OHLCV (swap `fetch_raw` for a broker API) |
| `daily_update.py` | scheduled daily data append |
| `engine.py` | look-ahead-safe backtester + Indian cost model |
| `strategies/` | pluggable strategy framework + library |
| `indicators.py` | EMA, RSI, ATR, ADX, SuperTrend, Bollinger |
| `metrics.py` | all the trading statistics |
| `regime.py` | market-regime tagging + per-regime stats |
| `report.py` | the PDF generator |

## Honest notes (read these)
- **Backtest results are research, not a prediction.** A strategy that wins on
  one stock over one period is very often curve-fit noise. Before trusting any
  winner, test it **out-of-sample** (a period it never saw) and on other stocks.
- **Verify cost rates.** The rates in `engine.py` (`COSTS`) change over time -
  check current STT/brokerage/stamp with your broker and update the dict.
- **Intraday data quality matters.** Free sources have gaps; use a broker API for
  anything below daily bars.
