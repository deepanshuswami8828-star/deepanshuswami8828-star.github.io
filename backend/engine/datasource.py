"""DataSource Interface - Abstract adapter for yfinance and broker APIs.

Provides a unified interface for fetching market OHLCV data.
Default: YFinanceDataSource (daily end-of-day data).
Optional: BrokerDataSource (stub for Zerodha Kite Connect, Upstox, Angel One).

NOTE ON DATA LICENSING:
Broker historical market data accessed via official APIs (e.g. Zerodha Kite Connect)
is licensed for personal research, analysis, and backtesting use only and must not
be redistributed.
"""
import os
import pandas as pd

class DataSource:
    def fetch_ohlcv(self, symbol: str, start: str, end: str, interval: str = "1d") -> pd.DataFrame:
        """Fetch raw OHLCV DataFrame with columns: open, high, low, close, volume and DatetimeIndex."""
        raise NotImplementedError

def _to_yahoo(symbol: str) -> str:
    if symbol.endswith(".NS") or symbol.endswith(".BO") or symbol.startswith("^"):
        return symbol
    return symbol + ".NS"

class YFinanceDataSource(DataSource):
    def fetch_ohlcv(self, symbol: str, start: str, end: str, interval: str = "1d") -> pd.DataFrame:
        import yfinance as yf
        raw = yf.download(
            _to_yahoo(symbol),
            start=start,
            end=end,
            interval=interval,
            auto_adjust=True,
            progress=False
        )
        if raw.empty:
            return pd.DataFrame()
        if isinstance(raw.columns, pd.MultiIndex):
            raw.columns = raw.columns.get_level_values(0)
        raw = raw.rename(columns=str.lower)
        needed = [c for c in ["open", "high", "low", "close", "volume"] if c in raw.columns]
        raw = raw[needed]
        raw.index = pd.to_datetime(raw.index)
        return raw.dropna()

class BrokerDataSource(DataSource):
    """Stub implementation for Zerodha Kite / Upstox / Angel One API.
    
    Reads BROKER_API_KEY and BROKER_ACCESS_TOKEN from environment variables.
    """
    def __init__(self):
        self.api_key = os.getenv("BROKER_API_KEY", "")
        self.access_token = os.getenv("BROKER_ACCESS_TOKEN", "")

    def fetch_ohlcv(self, symbol: str, start: str, end: str, interval: str = "1d") -> pd.DataFrame:
        if not self.api_key or not self.access_token:
            print("Broker keys missing (BROKER_API_KEY/BROKER_ACCESS_TOKEN). Falling back to YFinanceDataSource.")
            return YFinanceDataSource().fetch_ohlcv(symbol, start, end, interval)

        # Plug-and-play Zerodha Kite Connect example:
        # try:
        #     from kiteconnect import KiteConnect
        #     kite = KiteConnect(api_key=self.api_key)
        #     kite.set_access_token(self.access_token)
        #     records = kite.historical_data(instrument_token, start, end, interval)
        #     df = pd.DataFrame(records).rename(columns={"date": "time"})
        #     df.set_index("time", inplace=True)
        #     return df[["open", "high", "low", "close", "volume"]]
        # except Exception as e:
        #     print(f"Broker API fetch error: {e}. Falling back to YFinance.")
        #     return YFinanceDataSource().fetch_ohlcv(symbol, start, end, interval)

        print("BrokerDataSource adapter initialized. Falling back to YFinanceDataSource for standard daily data.")
        return YFinanceDataSource().fetch_ohlcv(symbol, start, end, interval)

def get_data_source() -> DataSource:
    source_name = os.getenv("DATA_SOURCE", "yfinance").strip().lower()
    if source_name == "broker":
        return BrokerDataSource()
    return YFinanceDataSource()
