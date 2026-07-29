import requests

BASE_URL = "http://127.0.0.1:8000"

print("Adding stock TCS...")
res = requests.post(f"{BASE_URL}/stocks", json={"symbol": "TCS", "name": "Tata Consultancy Services Limited"})
print(f"Response status: {res.status_code}")
print(res.json())

# Test duplicate add rejection
print("\nTesting duplicate stock add rejection...")
res_dup = requests.post(f"{BASE_URL}/stocks", json={"symbol": "TCS"})
print(f"Duplicate response status: {res_dup.status_code} (Expected 400)")
print(res_dup.json())

# Test invalid stock validation check
print("\nTesting invalid stock symbol validation...")
res_invalid = requests.post(f"{BASE_URL}/stocks", json={"symbol": "FAKE_STOCK_123"})
print(f"Invalid stock response status: {res_invalid.status_code} (Expected 400)")
print(res_invalid.json())

# Verify search finds TCS
print("\nSearching for TCS in database...")
res_search = requests.get(f"{BASE_URL}/stocks?query=TCS")
print(res_search.json())
