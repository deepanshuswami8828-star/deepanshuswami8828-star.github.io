"""ONE command to run everything.

    python run.py                 # real data (edit CONFIG below) - needs internet
    python run.py --demo          # synthetic data, works fully offline
    python run.py --symbol TCS --start 2023-01-01 --end 2025-01-01

Flow: load data -> tag market regimes -> run EVERY registered strategy on the
same data -> compute stats -> write one PDF comparing them all.
"""
import argparse
import datetime as dt

import numpy as np
import pandas as pd

from strategies import all_strategies          # importing registers them
from engine import run_backtest
from metrics import compute
from regime import tag_bars, attach_to_trades
from report import build_report

# ============================ CHOOSE HERE ============================
CONFIG = {
    "symbol": "RELIANCE",       # NSE symbol (no suffix needed; .NS added for you)
    "start": "2023-01-01",
    "end": "2025-01-01",
    "interval": "1d",           # 1d, 1h, 15m, 5m ... (intraday needs a broker API)
    "capital_per_trade": 100_000,
    "segment": "intraday",      # "intraday" or "delivery" (affects the cost model)
    "only": None,               # e.g. ["EMA Crossover", "SuperTrend"] or None for all
}
# =====================================================================


def synthetic_ohlcv(days: int = 520, seed: int = 7) -> pd.DataFrame:
    """Regime-switching random walk so different strategies behave differently."""
    rng = np.random.default_rng(seed)
    idx = pd.bdate_range(end=pd.Timestamp.today().normalize(), periods=days)
    price, drift, vol, closes = 1000.0, 0.0004, 0.012, []
    for i in range(days):
        if i % 70 == 0:
            drift = float(rng.choice([0.0016, -0.0013, 0.0002]))   # trend up / down / range
            vol = float(rng.choice([0.008, 0.017, 0.030]))         # calm / normal / volatile
        price *= (1 + rng.normal(drift, vol))
        closes.append(price)
    close = pd.Series(closes, index=idx)
    open_ = close.shift(1).fillna(close.iloc[0])
    wick = pd.Series(np.abs(rng.normal(0, vol, days)), index=idx)
    high = pd.concat([close * (1 + wick / 2), open_, close], axis=1).max(axis=1)
    low = pd.concat([close * (1 - wick / 2), open_, close], axis=1).min(axis=1)
    volume = pd.Series(rng.integers(100_000, 5_000_000, days), index=idx)
    return pd.DataFrame({"open": open_, "high": high, "low": low, "close": close, "volume": volume})


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--demo", action="store_true", help="use synthetic data (offline)")
    ap.add_argument("--symbol"); ap.add_argument("--start"); ap.add_argument("--end")
    ap.add_argument("--interval"); ap.add_argument("--segment")
    args = ap.parse_args()
    for k in ("symbol", "start", "end", "interval", "segment"):
        if getattr(args, k):
            CONFIG[k] = getattr(args, k)

    if args.demo:
        df = synthetic_ohlcv()
        symbol = "DEMO-SYNTHETIC"
        print(f"[demo] synthetic data: {len(df)} bars {df.index.min().date()} -> {df.index.max().date()}")
    else:
        from data import get_data
        df = get_data(CONFIG["symbol"], CONFIG["start"], CONFIG["end"], CONFIG["interval"])
        symbol = CONFIG["symbol"]
        print(f"[data] {symbol}: {len(df)} bars {df.index.min().date()} -> {df.index.max().date()}")

    regimes = tag_bars(df)
    strategies = all_strategies()
    if CONFIG["only"]:
        strategies = {k: v for k, v in strategies.items() if k in CONFIG["only"]}

    results = {}
    print("\nStrategy                     Net P&L      Trades   Win%")
    print("-" * 58)
    for name, Strat in strategies.items():
        trades, equity = run_backtest(df, Strat(), CONFIG["capital_per_trade"], {"segment": CONFIG["segment"]})
        trades = attach_to_trades(trades, regimes)
        m = compute(trades, equity, CONFIG["capital_per_trade"])
        results[name] = {"trades": trades, "equity": equity, "metrics": m}
        print(f"{name:<28} {m.get('net_pnl', 0):>10,.0f}   {m.get('trades', 0):>6}  {m.get('win_rate', 0):>5}")

    out = f"backtest_report_{symbol.split('-')[0].split('.')[0]}_{dt.date.today()}.pdf"
    build_report(out, symbol, CONFIG["interval"], df, results)
    print(f"\nPDF report -> {out}")
    return out


if __name__ == "__main__":
    main()
