"""Daily auto-update worker.

On a schedule (or triggered via API), appends the new day's bar for a configurable
WATCHLIST plus any symbol already present in StockStatus / price_bars table.
Idempotent and logs a per-symbol OK/FAIL summary.
"""
import os
import sys
import datetime as dt

# Add backend directory to sys.path if needed
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from sqlmodel import Session, select
from database import engine
from models import StockStatus
from data import get_data

WATCHLIST = ["RELIANCE", "TCS", "HDFCBANK", "INFY", "ICICIBANK", "SBIN", "BHARTIARTL", "ITC", "LT", "AXISBANK"]
INTERVAL = "1d"
HISTORY_YEARS = 5

def run_daily_update():
    print("=== Starting BacktestLab Daily Auto-Update Worker ===")
    end = (dt.date.today() + dt.timedelta(days=1)).isoformat()
    start = (dt.date.today() - dt.timedelta(days=365 * HISTORY_YEARS)).isoformat()

    # Collect symbols from default WATCHLIST + any symbol in StockStatus
    symbols_to_update = set(WATCHLIST)
    try:
        with Session(engine) as session:
            cached_symbols = session.exec(select(StockStatus.symbol)).all()
            for s in cached_symbols:
                if s:
                    symbols_to_update.add(s.strip().upper())
    except Exception as e:
        print(f"Note: Could not query StockStatus table: {e}")

    symbols_list = sorted(list(symbols_to_update))
    print(f"Targeting {len(symbols_list)} symbols for daily update...")

    summary_results = []
    ok_count = 0
    fail_count = 0

    for sym in symbols_list:
        try:
            df = get_data(sym, start, end, INTERVAL, use_cache=True)
            last_date = df.index.max().strftime("%Y-%m-%d") if not df.empty else "N/A"
            msg = f"OK   {sym:<12} bars={len(df):<6} last={last_date}"
            print(msg)
            summary_results.append({"symbol": sym, "status": "OK", "bars": len(df), "last_bar": last_date})
            ok_count += 1
        except Exception as e:
            msg = f"FAIL {sym:<12} error={str(e)}"
            print(msg)
            summary_results.append({"symbol": sym, "status": "FAIL", "error": str(e)})
            fail_count += 1

    print(f"\n=== Daily Update Finished: {ok_count} OK, {fail_count} FAILED out of {len(symbols_list)} total ===")
    return {"ok_count": ok_count, "fail_count": fail_count, "results": summary_results}

if __name__ == "__main__":
    run_daily_update()
