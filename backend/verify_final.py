import requests

BASE_URL = "http://127.0.0.1:8000"

print("Step 1. Adding stock WIPRO...")
res = requests.post(f"{BASE_URL}/stocks", json={"symbol": "WIPRO", "name": "Wipro Limited"})
print(f"Stock Add Status: {res.status_code}")
print(res.json())

print("\nStep 2. Creating custom strategy spec 'EMA 10 cross 50'...")
spec = {
    "name": "EMA 10 cross 50",
    "entry_long": [
        {
            "left": {"type": "indicator", "name": "ema", "params": {"period": 10}},
            "op": "crosses_above",
            "right": {"type": "indicator", "name": "ema", "params": {"period": 50}}
        }
    ],
    "entry_short": [],
    "exit": [],
    "risk": {
        "sl_atr_mult": 2.5,
        "rr_ratio": 2.0,
        "allow_long": True,
        "allow_short": False,
        "atr_period": 14
    }
}
res_spec = requests.post(f"{BASE_URL}/strategies", json=spec)
if res_spec.status_code != 200:
    print(f"Error creating strategy: {res_spec.status_code} - {res_spec.text}")
    exit(1)
custom_id = res_spec.json()["id"]
print(f"Strategy Created! ID: {custom_id}")

print("\nStep 3. Running backtest comparison on WIPRO (1d timeframe, 2023-01-01 to 2025-01-01)...")
backtest_req = {
    "symbol": "WIPRO",
    "start": "2023-01-01",
    "end": "2025-01-01",
    "interval": "1d",
    "capital_per_trade": 100000,
    "segment": "delivery",
    "strategy_ids": [custom_id, "ema_crossover"]
}
res_backtest = requests.post(f"{BASE_URL}/backtest", json=backtest_req)
if res_backtest.status_code != 200:
    print(f"Error running backtest: {res_backtest.status_code} - {res_backtest.text}")
    exit(1)

bt_result = res_backtest.json()
print("\n" + "=" * 40)
print("          VERIFIED BACKTEST RESULTS")
print("=" * 40)
print(f"Symbol: {bt_result['symbol']} | Bars: {bt_result['bars']}")
print("\nLeaderboard:")
for idx, row in enumerate(bt_result["leaderboard"]):
    print(f"{idx+1}. {row['name']}: Net P&L = {row['net_pnl']:.2f} INR | Win Rate = {row['win_rate']:.2f}% | Return = {row['return_pct']:.2f}%")

print("\nCustom Strategy 'EMA 10 cross 50' Trade Log Sample:")
custom_details = bt_result["per_strategy"].get("EMA 10 cross 50")
if custom_details and custom_details["trades"]:
    for trade in custom_details["trades"][:3]:
        print(f"Date: {trade[0]} to {trade[1]} | Dir: {trade[2]} | Entry: {trade[3]:.2f} | Exit: {trade[4]:.2f} | P&L: {trade[8]:.2f} | Reason: {trade[11]}")
else:
    print("No trades generated.")
print("=" * 40)
