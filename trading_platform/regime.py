"""Market-regime tagging.

Label every bar trending / ranging (via ADX + directional movement) with a
volatility bucket (via ATR%), then attach the entry-bar regime to each trade.
That is what lets the report answer "which strategy works in which condition".
"""
import pandas as pd

from indicators import adx, atr


def tag_bars(df: pd.DataFrame, adx_period: int = 14, adx_trend: float = 25.0) -> pd.DataFrame:
    adx_, plus_di, minus_di = adx(df, adx_period)
    atr_pct = atr(df, adx_period) / df["close"]

    trend = pd.Series("ranging", index=df.index)
    trend[(adx_ >= adx_trend) & (plus_di > minus_di)] = "trending_up"
    trend[(adx_ >= adx_trend) & (minus_di > plus_di)] = "trending_down"

    vol = pd.Series("normal_vol", index=df.index)
    if atr_pct.notna().sum() > 10:
        lo, hi = atr_pct.quantile(0.33), atr_pct.quantile(0.66)
        vol[atr_pct <= lo] = "low_vol"
        vol[atr_pct >= hi] = "high_vol"

    return pd.DataFrame({"trend_regime": trend, "vol_regime": vol})


def attach_to_trades(trades_df: pd.DataFrame, regimes: pd.DataFrame) -> pd.DataFrame:
    if trades_df.empty:
        return trades_df
    tr = trades_df.copy()
    tr["trend_regime"] = tr["entry_time"].map(regimes["trend_regime"])
    tr["vol_regime"] = tr["entry_time"].map(regimes["vol_regime"])
    return tr


def by_regime(trades_df: pd.DataFrame) -> pd.DataFrame:
    if trades_df.empty or "trend_regime" not in trades_df:
        return pd.DataFrame()
    g = trades_df.groupby("trend_regime")["net_pnl"]
    return pd.DataFrame({
        "trades": g.count(),
        "net_pnl": g.sum().round(2),
        "win_rate": trades_df.groupby("trend_regime")["net_pnl"].apply(lambda s: round(100 * (s > 0).mean(), 1)),
    }).reset_index()
