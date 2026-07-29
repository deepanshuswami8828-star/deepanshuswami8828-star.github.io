"""Data layer - fetch OHLCV, cache to Parquet, update incrementally.

Runs on YOUR machine (needs internet). Free daily (end-of-day) data comes from
yfinance. For intraday NSE data, swap the body of fetch_raw() for a broker API
(Zerodha Kite / Upstox / Angel One) - the rest of the platform stays identical.

The cache means you fetch a date range from the network only ONCE. After that
it is read from disk, and each daily run only appends the new tail.
"""
import os
import pandas as pd

CACHE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cache")
os.makedirs(CACHE_DIR, exist_ok=True)


def _cache_path(symbol: str, interval: str) -> str:
    safe = symbol.replace(".", "_").replace("^", "idx_")
    return os.path.join(CACHE_DIR, f"{safe}_{interval}.parquet")


def _to_yahoo(symbol: str) -> str:
    # NSE equities on Yahoo use the .NS suffix; indices start with ^ (e.g. ^NSEI).
    if symbol.endswith(".NS") or symbol.endswith(".BO") or symbol.startswith("^"):
        return symbol
    return symbol + ".NS"


def fetch_raw(symbol: str, start: str, end: str, interval: str = "1d") -> pd.DataFrame:
    """Return normalized OHLCV (open/high/low/close/volume, datetime index).

    >>> SWAP THIS FUNCTION for a broker API to get real intraday NSE data. <<<
    Example (Zerodha Kite):
        from kiteconnect import KiteConnect
        kite = KiteConnect(api_key=...); kite.set_access_token(...)
        data = kite.historical_data(instrument_token, start, end, interval)
        return pd.DataFrame(data).rename(columns={...}).set_index("date")
    """
    import yfinance as yf
    raw = yf.download(_to_yahoo(symbol), start=start, end=end, interval=interval,
                      auto_adjust=True, progress=False)
    if raw.empty:
        return pd.DataFrame()
    if isinstance(raw.columns, pd.MultiIndex):
        raw.columns = raw.columns.get_level_values(0)
    raw = raw.rename(columns=str.lower)[["open", "high", "low", "close", "volume"]]
    raw.index = pd.to_datetime(raw.index)
    return raw.dropna()


def get_data(symbol: str, start: str, end: str, interval: str = "1d", use_cache: bool = True) -> pd.DataFrame:
    """Load from cache, fetch only the missing tail, append, and return the slice."""
    path = _cache_path(symbol, interval)
    cached = pd.read_parquet(path) if (use_cache and os.path.exists(path)) else pd.DataFrame()

    need_start = start
    if not cached.empty:
        need_start = (cached.index.max() + pd.Timedelta(days=1)).strftime("%Y-%m-%d")

    if pd.Timestamp(need_start) < pd.Timestamp(end):
        fresh = fetch_raw(symbol, need_start, end, interval)
        if not fresh.empty:
            combined = pd.concat([cached, fresh])
            combined = combined[~combined.index.duplicated(keep="last")].sort_index()
            combined.to_parquet(path)
            cached = combined
    if cached.empty:
        raise RuntimeError(f"No data for {symbol}. Check the symbol/interval and your internet.")
    return cached.loc[str(start): str(end)]
