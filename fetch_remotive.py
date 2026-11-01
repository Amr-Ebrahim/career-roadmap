import json
import os
import requests

URL = "https://remotive.com/api/remote-jobs"
OUT = "data/raw/remotive.json"

resp = requests.get(URL, timeout=30)
resp.raise_for_status()
data = resp.json()

os.makedirs("data/raw", exist_ok=True)
with open(OUT, "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False)

print("Top-level keys:", list(data.keys()))
print("Jobs returned:", len(data["jobs"]))
print()
first = data["jobs"][0]
for key, value in first.items():
    print(f"{key}: {str(value)[:120]}")