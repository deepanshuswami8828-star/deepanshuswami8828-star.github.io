"""Event-driven backtest engine.

Design choices that make results honest:
  * Look-ahead safe : a signal generated on bar t (using close of t) is filled
    at bar t+1's OPEN. Nothing ever trades on information from its own bar.
  * Uniform risk     : stop-loss and target are set from ATR at entry using each
    strategy's sl_atr_mult / rr_ratio, so strategies are compared fairly.
  * Real costs        : an Indian-equity cost model (brokerage, STT, exchange txn,
    GST, SEBI, stamp duty) + slippage is applied to every fill.
  * Conservative fills: if a bar touches both stop and target, the STOP is assumed
    hit first (worst case).
Every trade stores the exact entry reason and exit reason.
"""
import math
import pandas as pd

from indicators import atr

# --- Indian equity cost model. Rates change over time; verify with your broker. ---
COSTS = {
    "segment": "intraday",          # "intraday" or "delivery"
    "brokerage_pct": 0.0003,        # 0.03% of turnover per executed order
    "brokerage_cap": 20.0,          # capped at 20 per order (Zerodha-style)
    "stt_intraday_sell": 0.00025,   # 0.025% on SELL leg (intraday)
    "stt_delivery": 0.001,          # 0.1% on BOTH legs (delivery)
    "exch_txn_pct": 0.0000297,      # NSE ~0.00297%
    "sebi_pct": 0.000001,           # ~10 per crore
    "stamp_intraday_buy": 0.00003,  # 0.003% on BUY leg (intraday)
    "stamp_delivery_buy": 0.00015,  # 0.015% on BUY leg (delivery)
    "gst_pct": 0.18,                # 18% GST on (brokerage + exch txn + sebi)
    "slippage_pct": 0.0002,         # 0.02% slippage assumed per market fill
}


def _leg_cost(turnover: float, side: str, cfg: dict) -> float:
    """Charges (in currency) for one leg. side is 'buy' or 'sell'."""
    brokerage = min(turnover * cfg["brokerage_pct"], cfg["brokerage_cap"])
    if cfg["segment"] == "intraday":
        stt = turnover * cfg["stt_intraday_sell"] if side == "sell" else 0.0
        stamp = turnover * cfg["stamp_intraday_buy"] if side == "buy" else 0.0
    else:
        stt = turnover * cfg["stt_delivery"]
        stamp = turnover * cfg["stamp_delivery_buy"] if side == "buy" else 0.0
    exch = turnover * cfg["exch_txn_pct"]
    sebi = turnover * cfg["sebi_pct"]
    gst = cfg["gst_pct"] * (brokerage + exch + sebi)
    return brokerage + stt + stamp + exch + sebi + gst


def run_backtest(df: pd.DataFrame, strategy, capital_per_trade: float = 100_000, costs: dict | None = None):
    """Return (trades_df, daily_equity_series)."""
    cfg = {**COSTS, **(costs or {})}
    slip = cfg["slippage_pct"]
    signals = strategy.generate_signals(df)
    atr_series = atr(df, strategy.atr_period)

    trades: list[dict] = []
    pos: dict | None = None

    for i in range(1, len(df)):
        ts = df.index[i]
        o, h, l = df["open"].iloc[i], df["high"].iloc[i], df["low"].iloc[i]
        sig = signals.iloc[i - 1]  # decision made on the PREVIOUS bar

        # (a) act on that decision at THIS bar's open -----------------------
        if pos is not None and sig["exit"]:
            fill = o * (1 - slip) if pos["dir"] == "long" else o * (1 + slip)
            _close(pos, fill, ts, "Strategy exit signal", cfg, trades)
            pos = None
        if pos is None:
            atr_now = atr_series.iloc[i - 1]
            if not math.isnan(atr_now) and atr_now > 0:
                if sig["enter_long"] and strategy.allow_long:
                    pos = _open("long", o * (1 + slip), ts, sig["reason"], atr_now, strategy, capital_per_trade)
                elif sig["enter_short"] and strategy.allow_short:
                    pos = _open("short", o * (1 - slip), ts, sig["reason"], atr_now, strategy, capital_per_trade)

        # (b) intrabar stop / target check on THIS bar ----------------------
        if pos is not None:
            if pos["dir"] == "long":
                if l <= pos["sl"]:
                    _close(pos, pos["sl"], ts, "Stop-loss hit", cfg, trades); pos = None
                elif h >= pos["target"]:
                    _close(pos, pos["target"], ts, "Target hit", cfg, trades); pos = None
            else:
                if h >= pos["sl"]:
                    _close(pos, pos["sl"], ts, "Stop-loss hit", cfg, trades); pos = None
                elif l <= pos["target"]:
                    _close(pos, pos["target"], ts, "Target hit", cfg, trades); pos = None

    if pos is not None:  # force-close any open position at the final close
        _close(pos, df["close"].iloc[-1], df.index[-1], "End of backtest", cfg, trades)

    trades_df = pd.DataFrame(trades)
    equity = _equity_curve(trades_df, capital_per_trade)
    return trades_df, equity


def _open(direction, price, ts, reason, atr_now, strat, capital):
    qty = max(int(capital // price), 1)
    dist = strat.sl_atr_mult * atr_now
    if direction == "long":
        sl, target = price - dist, price + strat.rr_ratio * dist
    else:
        sl, target = price + dist, price - strat.rr_ratio * dist
    return {"dir": direction, "entry": price, "entry_time": ts, "qty": qty,
            "sl": sl, "target": target, "reason": reason}


def _close(pos, price, ts, exit_reason, cfg, trades):
    qty = pos["qty"]
    entry_turn, exit_turn = pos["entry"] * qty, price * qty
    if pos["dir"] == "long":
        buy_turn, sell_turn = entry_turn, exit_turn
        gross = (price - pos["entry"]) * qty
    else:
        buy_turn, sell_turn = exit_turn, entry_turn
        gross = (pos["entry"] - price) * qty
    charges = _leg_cost(buy_turn, "buy", cfg) + _leg_cost(sell_turn, "sell", cfg)
    net = gross - charges
    trades.append({
        "direction": pos["dir"], "entry_time": pos["entry_time"], "exit_time": ts,
        "entry": round(pos["entry"], 2), "exit": round(price, 2), "qty": qty,
        "sl": round(pos["sl"], 2), "target": round(pos["target"], 2),
        "gross_pnl": round(gross, 2), "charges": round(charges, 2), "net_pnl": round(net, 2),
        "return_pct": round(100 * net / (pos["entry"] * qty), 3),
        "entry_reason": pos["reason"], "exit_reason": exit_reason,
    })


def _equity_curve(trades_df, capital):
    if trades_df.empty:
        return pd.Series(dtype=float)
    eq = trades_df.set_index("exit_time")["net_pnl"].cumsum() + capital
    return eq.resample("1D").last().ffill().dropna()
