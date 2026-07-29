"""Professional trade statistics, computed from the trade list and the daily
equity curve. Drawdown and Sharpe use the daily mark of realized equity.
"""
import numpy as np
import pandas as pd


def compute(trades_df: pd.DataFrame, equity: pd.Series, capital: float, periods_per_year: int = 252) -> dict:
    if trades_df is None or trades_df.empty:
        return {"trades": 0}

    net = trades_df["net_pnl"]
    wins, losses = net[net > 0], net[net < 0]
    gross_profit, gross_loss = wins.sum(), -losses.sum()
    n = len(net)

    aw = wins.mean() if len(wins) else 0.0
    al = abs(losses.mean()) if len(losses) else 0.0
    wr = len(wins) / n

    m = {
        "trades": n,
        "wins": len(wins),
        "losses": len(losses),
        "win_rate": round(100 * wr, 2),
        "net_pnl": round(net.sum(), 2),
        "gross_profit": round(gross_profit, 2),
        "gross_loss": round(gross_loss, 2),
        "profit_factor": round(gross_profit / gross_loss, 2) if gross_loss > 0 else float("inf"),
        "avg_win": round(aw, 2),
        "avg_loss": round(-al, 2),
        "avg_trade": round(net.mean(), 2),
        "largest_win": round(net.max(), 2),
        "largest_loss": round(net.min(), 2),
        "reward_risk": round(aw / al, 2) if al > 0 else float("inf"),
        "expectancy": round(wr * aw - (1 - wr) * al, 2),
        "return_pct": round(100 * net.sum() / capital, 2),
        "total_charges": round(trades_df["charges"].sum(), 2),
    }
    m["max_consec_wins"], m["max_consec_losses"] = _streaks(net)

    if equity is not None and len(equity) > 1:
        roll_max = equity.cummax()
        dd = equity - roll_max
        m["max_drawdown"] = round(dd.min(), 2)
        m["max_drawdown_pct"] = round(100 * (dd / roll_max).min(), 2)
        rets = equity.pct_change().dropna()
        m["sharpe"] = round(np.sqrt(periods_per_year) * rets.mean() / rets.std(), 2) if rets.std() > 0 else 0.0
        days = (equity.index[-1] - equity.index[0]).days
        if days > 0:
            m["cagr_pct"] = round(100 * ((equity.iloc[-1] / equity.iloc[0]) ** (365 / days) - 1), 2)
    return m


def _streaks(net):
    mw = cw = ml = cl = 0
    for x in net:
        if x > 0:
            cw, cl = cw + 1, 0; mw = max(mw, cw)
        elif x < 0:
            cl, cw = cl + 1, 0; ml = max(ml, cl)
    return mw, ml
