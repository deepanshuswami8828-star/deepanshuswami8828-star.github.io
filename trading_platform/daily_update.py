"""Daily auto-update. Run this once every trading day so 'today live' becomes
tomorrow's cached history. It only appends the new bars to each symbol's cache.

Schedule it:
  Windows (Task Scheduler, runs 6:30pm on weekdays):
    schtasks /create /tn DOSTdata /sc weekly /d MON,TUE,WED,THU,FRI /st 18:30 ^
      /tr "python C:\\path\\to\\trading_platform\\daily_update.py"

  Linux/Mac (crontab -e):
    30 18 * * 1-5  cd /path/to/trading_platform && python daily_update.py
"""
import datetime as dt

from data import get_data

# Edit this list. To cover "all stocks", load NSE's equity list into WATCHLIST
# (e.g. from the NSE EQUITY_L CSV) - but a focused watchlist is faster and enough
# for personal research.
WATCHLIST = ["RELIANCE", "TCS", "HDFCBANK", "INFY", "ICICIBANK", "SBIN", "^NSEI"]
INTERVAL = "1d"
HISTORY_YEARS = 5


def main():
    end = (dt.date.today() + dt.timedelta(days=1)).isoformat()
    start = (dt.date.today() - dt.timedelta(days=365 * HISTORY_YEARS)).isoformat()
    for sym in WATCHLIST:
        try:
            df = get_data(sym, start, end, INTERVAL)
            print(f"OK   {sym:<10} rows={len(df):<6} last={df.index.max().date()}")
        except Exception as e:  # noqa: BLE001
            print(f"FAIL {sym:<10} {e}")


if __name__ == "__main__":
    main()
