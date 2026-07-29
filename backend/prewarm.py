"""Pre-warm top-N script for BacktestLab.

Caches historical data for curated popular stocks (e.g. Nifty 50) so common stock backtests
are instant without fetching the entire 2300+ stock universe.
"""
import os
import sys
import datetime as dt

backend_dir = os.path.dirname(os.path.abspath(__file__))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)
sys.path.insert(0, os.path.join(backend_dir, "engine"))

from data import get_data

POPULAR_STOCKS = [
    "RELIANCE", "TCS", "HDFCBANK", "INFY", "ICICIBANK", "HINDUNILVR", "ITC", "SBIN",
    "BHARTIARTL", "KOTAKBANK", "LT", "AXISBANK", "ASIANPAINT", "HCLTECH", "MARUTI",
    "SUNPHARMA", "BAJFINANCE", "TITAN", "ULTRACEMCO", "TATAMOTORS"
]

def prewarm_top_n(stock_list=None, years=3):
    stocks = stock_list or POPULAR_STOCKS
    print(f"=== Pre-warming {len(stocks)} popular stocks ({years} years history) ===")
    end = dt.date.today().strftime("%Y-%m-%d")
    start = (dt.date.today() - dt.timedelta(days=365 * years)).strftime("%Y-%m-%d")

    results = []
    for sym in stocks:
        try:
            df = get_data(sym, start, end, "1d")
            print(f"Pre-warmed {sym:<12}: {len(df)} bars cached.")
            results.append({"symbol": sym, "status": "OK", "bars": len(df)})
        except Exception as e:
            print(f"Pre-warm failed for {sym:<12}: {e}")
            results.append({"symbol": sym, "status": "FAIL", "error": str(e)})
    print("=== Pre-warming Complete ===")
    return results

if __name__ == "__main__":
    prewarm_top_n()
