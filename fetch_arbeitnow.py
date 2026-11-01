import json
import os
import requests

URL = "https://www.arbeitnow.com/api/job-board-api"
OUT = "data/raw/arbeitnow_page1.json"

resp = requests.get(URL, timeout=30)
resp.raise_for_status()
data = resp.json()

os.makedirs("data/raw", exist_ok=True)
with open(OUT, "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False)

print("Top-level keys:", list(data.keys()))
print("Jobs on this page:", len(data["data"]))
print()
print("links:", data.get("links"))
print("meta:", data.get("meta"))
print()
first = data["data"][0]
for key, value in first.items():
    print(f"{key}: {str(value)[:120]}")