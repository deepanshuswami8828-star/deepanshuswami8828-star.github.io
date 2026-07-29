"""Data layer - Durable DB storage (price_bars table), incremental fetch & status tracking.

Checks durable DB store (price_bars table) -> fetches missing tail from DataSource
(yfinance or broker) -> upserts to DB -> updates StockStatus metadata -> returns DataFrame.
"""
import os
import sys
import datetime as dt
import pandas as pd
from sqlmodel import Session, select, func, or_
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.dialects.postgresql import insert as pg_insert

# Add backend directory to sys.path if not present
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from database import engine
from models import PriceBar, StockStatus
from datasource import get_data_source


def get_data(symbol: str, start: str, end: str, interval: str = "1d", use_cache: bool = True) -> pd.DataFrame:
    """Load from DB store (price_bars), fetch only missing tail, upsert, update StockStatus, and return DataFrame slice."""
    symbol = symbol.strip().upper()
    interval = interval.strip().lower()

    start_dt = pd.to_datetime(start)
    end_dt = pd.to_datetime(end)

    with Session(engine) as session:
        # Check existing status / cached max timestamp in DB
        status_rec = session.exec(
            select(StockStatus)
            .where(StockStatus.symbol == symbol, StockStatus.interval == interval)
        ).first()

        cached_max_dt = None
        if status_rec and status_rec.last_bar:
            try:
                cached_max_dt = pd.to_datetime(status_rec.last_bar)
            except Exception:
                pass

        if not cached_max_dt:
            # Query max timestamp from PriceBar if status record not yet present
            max_ts = session.exec(
                select(func.max(PriceBar.timestamp))
                .where(PriceBar.symbol == symbol, PriceBar.interval == interval)
            ).one_or_none()
            if max_ts:
                cached_max_dt = pd.to_datetime(max_ts)

        need_start = start
        if cached_max_dt and use_cache:
            # Need start is the day after cached max
            next_day = cached_max_dt + pd.Timedelta(days=1)
            if next_day < end_dt:
                need_start = next_day.strftime("%Y-%m-%d")
            else:
                need_start = None  # Up to date!

        # Fetch missing tail if needed
        if need_start and pd.to_datetime(need_start) <= end_dt:
            ds = get_data_source()
            fresh_df = ds.fetch_ohlcv(symbol, need_start, end, interval)

            if not fresh_df.empty:
                # Upsert into price_bars DB table
                bars_to_insert = []
                for idx_ts, row in fresh_df.iterrows():
                    ts_val = idx_ts.to_pydatetime() if hasattr(idx_ts, "to_pydatetime") else idx_ts
                    bars_to_insert.append({
                        "symbol": symbol,
                        "interval": interval,
                        "timestamp": ts_val,
                        "open": float(row["open"]),
                        "high": float(row["high"]),
                        "low": float(row["low"]),
                        "close": float(row["close"]),
                        "volume": float(row["volume"])
                    })

                # Insert in chunks avoiding duplicates
                for chunk in [bars_to_insert[i:i + 500] for i in range(0, len(bars_to_insert), 500)]:
                    for b_dict in chunk:
                        # Check existing bar to be safe across SQLite/Postgres
                        existing_bar = session.exec(
                            select(PriceBar).where(
                                PriceBar.symbol == symbol,
                                PriceBar.interval == interval,
                                PriceBar.timestamp == b_dict["timestamp"]
                            )
                        ).first()
                        if existing_bar:
                            existing_bar.open = b_dict["open"]
                            existing_bar.high = b_dict["high"]
                            existing_bar.low = b_dict["low"]
                            existing_bar.close = b_dict["close"]
                            existing_bar.volume = b_dict["volume"]
                        else:
                            session.add(PriceBar(**b_dict))
                    session.commit()

        # Update StockStatus metadata
        min_max = session.exec(
            select(func.min(PriceBar.timestamp), func.max(PriceBar.timestamp), func.count(PriceBar.id))
            .where(PriceBar.symbol == symbol, PriceBar.interval == interval)
        ).one()

        min_ts, max_ts, count_bars = min_max
        if count_bars > 0:
            first_bar_str = pd.to_datetime(min_ts).strftime("%Y-%m-%d")
            last_bar_str = pd.to_datetime(max_ts).strftime("%Y-%m-%d")

            if not status_rec:
                status_rec = StockStatus(
                    symbol=symbol,
                    interval=interval,
                    first_bar=first_bar_str,
                    last_bar=last_bar_str,
                    last_updated=dt.datetime.utcnow(),
                    total_bars=count_bars
                )
                session.add(status_rec)
            else:
                status_rec.first_bar = first_bar_str
                status_rec.last_bar = last_bar_str
                status_rec.last_updated = dt.datetime.utcnow()
                status_rec.total_bars = count_bars
            session.commit()

        # Fetch requested slice from DB
        db_bars = session.exec(
            select(PriceBar)
            .where(
                PriceBar.symbol == symbol,
                PriceBar.interval == interval,
                PriceBar.timestamp >= start_dt,
                PriceBar.timestamp <= end_dt
            )
            .order_by(PriceBar.timestamp.asc())
        ).all()

        if not db_bars:
            # Fallback: if range wasn't covered yet, attempt full range fetch
            ds = get_data_source()
            fallback_df = ds.fetch_ohlcv(symbol, start, end, interval)
            if fallback_df.empty:
                raise RuntimeError(f"No data found for symbol '{symbol}'. Check symbol spelling and internet connection.")
            
            for idx_ts, row in fallback_df.iterrows():
                ts_val = idx_ts.to_pydatetime() if hasattr(idx_ts, "to_pydatetime") else idx_ts
                session.add(PriceBar(
                    symbol=symbol,
                    interval=interval,
                    timestamp=ts_val,
                    open=float(row["open"]),
                    high=float(row["high"]),
                    low=float(row["low"]),
                    close=float(row["close"]),
                    volume=float(row["volume"])
                ))
            session.commit()

            db_bars = session.exec(
                select(PriceBar)
                .where(
                    PriceBar.symbol == symbol,
                    PriceBar.interval == interval,
                    PriceBar.timestamp >= start_dt,
                    PriceBar.timestamp <= end_dt
                )
                .order_by(PriceBar.timestamp.asc())
            ).all()

    # Format result DataFrame
    records = []
    for b in db_bars:
        records.append({
            "datetime": b.timestamp,
            "open": b.open,
            "high": b.high,
            "low": b.low,
            "close": b.close,
            "volume": b.volume
        })
    df = pd.DataFrame(records).set_index("datetime")
    return df.sort_index()
