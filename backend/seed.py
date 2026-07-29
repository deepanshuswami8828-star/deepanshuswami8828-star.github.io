import os
import csv
import urllib.request
import io
from sqlmodel import Session, select, delete
from database import engine, create_db_and_tables
from models import Stock

NSE_CSV_URL = "https://archives.nseindia.com/content/equities/EQUITY_L.csv"
LOCAL_NSE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "nse_equities.csv")
LOCAL_CSV_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "stock_metadata.csv")

def seed_stocks():
    print("Initializing database tables...")
    create_db_and_tables()

    stocks_data = []
    
    # 1. Try reading from bundled nse_equities.csv first
    if os.path.exists(LOCAL_NSE_PATH):
        try:
            print(f"Reading bundled NSE equity dataset: {LOCAL_NSE_PATH}...")
            with open(LOCAL_NSE_PATH, "r", encoding="utf-8-sig") as f:
                reader = csv.DictReader(f)
                headers = {h.strip().upper(): h for h in reader.fieldnames}
                symbol_col = headers.get("SYMBOL")
                name_col = headers.get("NAME OF COMPANY") or headers.get("NAME") or headers.get("COMPANY NAME")
                series_col = headers.get("SERIES")

                if symbol_col and name_col:
                    for row in reader:
                        symbol = row[symbol_col].strip()
                        name = row[name_col].strip()
                        series = row[series_col].strip() if series_col else "EQ"
                        if symbol and name:
                            stocks_data.append({
                                "symbol": symbol,
                                "name": name,
                                "exchange": "NSE",
                                "series": series
                            })
            print(f"Loaded {len(stocks_data)} NSE equities from bundled CSV.")
        except Exception as e:
            print(f"Error reading bundled NSE CSV: {e}")

    # 2. Try fetching from live NSE list if local was empty
    if not stocks_data:
        try:
            print(f"Attempting to fetch live NSE equity list from {NSE_CSV_URL}...")
            req = urllib.request.Request(
                NSE_CSV_URL, 
                headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
            )
            with urllib.request.urlopen(req) as response:
                content = response.read().decode('utf-8')
                csv_file = io.StringIO(content)
                reader = csv.DictReader(csv_file)
                headers = {h.strip().upper(): h for h in reader.fieldnames}
                
                symbol_col = headers.get("SYMBOL")
                name_col = headers.get("NAME OF COMPANY") or headers.get("NAME")
                series_col = headers.get("SERIES")

                if symbol_col and name_col:
                    for row in reader:
                        symbol = row[symbol_col].strip()
                        name = row[name_col].strip()
                        series = row[series_col].strip() if series_col else "EQ"
                        stocks_data.append({
                            "symbol": symbol,
                            "name": name,
                            "exchange": "NSE",
                            "series": series
                        })
                    print(f"Successfully loaded {len(stocks_data)} stocks from live NSE.")
        except Exception as e:
            print(f"Failed to fetch live NSE list: {e}")

    # 3. Fallback to root stock_metadata.csv
    if not stocks_data and os.path.exists(LOCAL_CSV_PATH):
        print(f"Reading fallback metadata file: {LOCAL_CSV_PATH}...")
        with open(LOCAL_CSV_PATH, "r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            headers = {h.strip().upper(): h for h in reader.fieldnames}
            
            symbol_col = headers.get("SYMBOL")
            name_col = headers.get("COMPANY NAME") or headers.get("NAME")
            series_col = headers.get("SERIES")

            if symbol_col and name_col:
                for row in reader:
                    symbol = row[symbol_col].strip()
                    name = row[name_col].strip()
                    series = row[series_col].strip() if series_col else "EQ"
                    stocks_data.append({
                        "symbol": symbol,
                        "name": name,
                        "exchange": "NSE",
                        "series": series
                    })

    if not stocks_data:
        print("No stock data loaded. Seeding aborted.")
        return

    # De-duplicate by symbol
    unique_stocks = {}
    for item in stocks_data:
        unique_stocks[item["symbol"]] = item
    stocks_data = list(unique_stocks.values())

    # Persist to database in bulk
    with Session(engine) as session:
        print("Clearing existing stocks table...")
        session.exec(delete(Stock))
        session.commit()

        print(f"Bulk inserting {len(stocks_data)} unique NSE stocks into database...")
        session.bulk_insert_mappings(Stock, stocks_data)
        session.commit()
        print("Seeding completed successfully!")

if __name__ == "__main__":
    seed_stocks()
