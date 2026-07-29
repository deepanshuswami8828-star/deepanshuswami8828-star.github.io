import requests
import json

BASE_URL = "http://127.0.0.1:8000"

# Step 1. Get strategies and clean up any existing custom ones
print("Fetching current strategies...")
res = requests.get(f"{BASE_URL}/strategies")
strats = res.json()
for s in strats:
    if s.get("is_custom"):
        print(f"Cleaning up old custom strategy: {s['name']} ({s['id']})")
        requests.delete(f"{BASE_URL}/strategies/{s['id']}")

# Step 2. Define the correct spec payload
spec = {
    "name": "EMA 5 Crossover 20",
    "entry_long": [
        {
            "left": {"type": "indicator", "name": "ema", "params": {"period": 5}},
            "op": "crosses_above",
            "right": {"type": "indicator", "name": "ema", "params": {"period": 20}}
        }
    ],
    "entry_short": [
        {
            "left": {"type": "indicator", "name": "ema", "params": {"period": 5}},
            "op": "crosses_below",
            "right": {"type": "indicator", "name": "ema", "params": {"period": 20}}
        }
    ],
    "exit": [],
    "risk": {
        "sl_atr_mult": 2.0,
        "rr_ratio": 2.0,
        "allow_long": True,
        "allow_short": True,
        "atr_period": 14
    }
}

# Step 3. Post to create strategy
print("\nCreating custom strategy spec...")
res = requests.post(f"{BASE_URL}/strategies", json=spec)
if res.status_code != 200:
    print(f"Error creating strategy: {res.status_code} - {res.text}")
    exit(1)
    
created_strat = res.json()
custom_id = created_strat["id"]
print(f"Successfully created custom strategy! ID: {custom_id}")

# Step 4. Test validation reject (submitting with fake indicator name)
invalid_spec = dict(spec)
invalid_spec["entry_long"] = [
    {
        "left": {"type": "indicator", "name": "fake_indicator", "params": {"period": 5}},
        "op": "crosses_above",
        "right": {"type": "indicator", "name": "ema", "params": {"period": 20}}
    }
]
print("\nVerifying validation reject on fake indicator name...")
res_reject = requests.post(f"{BASE_URL}/strategies", json=invalid_spec)
print(f"Reject response code: {res_reject.status_code} (Expected 422)")
if res_reject.status_code != 422:
    print("Error: Validation reject test failed!")
    exit(1)
else:
    print("Validation reject test passed! Detail:")
    print(res_reject.json())

# Step 5. Run backtest with the custom strategy
print("\nRunning backtest including the custom strategy...")
backtest_req = {
    "symbol": "RELIANCE",
    "start": "2023-01-01",
    "end": "2025-01-01",
    "interval": "1d",
    "capital_per_trade": 100000,
    "segment": "delivery",
    "strategy_ids": [custom_id, "ema_crossover"]  # Compare custom with built-in
}

res_backtest = requests.post(f"{BASE_URL}/backtest", json=backtest_req)
if res_backtest.status_code != 200:
    print(f"Error running backtest: {res_backtest.status_code} - {res_backtest.text}")
    exit(1)

bt_result = res_backtest.json()
print("\n" + "=" * 40)
print("              BACKTEST RESULTS")
print("=" * 40)
print(f"Symbol: {bt_result['symbol']} | Bars: {bt_result['bars']}")
print("\nLeaderboard:")
for idx, row in enumerate(bt_result["leaderboard"]):
    print(f"{idx+1}. {row['name']}: Net P&L = {row['net_pnl']:.2f} INR | Win Rate = {row['win_rate']:.2f}% | Return = {row['return_pct']:.2f}%")

print("\nCustom Strategy Trade Log Sample (First 3 trades):")
custom_details = bt_result["per_strategy"].get("EMA 5 Crossover 20")
if custom_details and custom_details["trades"]:
    for trade in custom_details["trades"][:3]:
        print(f"Date: {trade[0]} to {trade[1]} | Dir: {trade[2]} | Entry: {trade[3]:.2f} | Exit: {trade[4]:.2f} | P&L: {trade[8]:.2f} | Reason: {trade[11]}")
else:
    print("No trades generated for custom strategy.")
print("=" * 40)
