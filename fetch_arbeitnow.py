# fetch_arbeitnow.py - download ALL current Arbeitnow jobs and save them as a dated snapshot.
# Run it once a week; every run adds a new file, nothing is overwritten.
import json
import os
import time
from datetime import date

import requests

URL = "https://www.arbeitnow.com/api/job-board-api"
OUT_DIR = "data/raw/arbeitnow"
MAX_PAGES = 200  # safety stop
HEADERS = {"User-Agent": "career-roadmap-learning-project"}


def get_page(url):
    for attempt in range(5):
        resp = requests.get(url, headers=HEADERS, timeout=30)
        if resp.status_code == 429:  # too many requests: wait and try again
            wait = int(resp.headers.get("Retry-After", 30))
            print(f"  rate limited, waiting {wait} s")
            time.sleep(wait)
            continue
        resp.raise_for_status()
        return resp.json()
    raise RuntimeError(f"Gave up on {url}")


jobs, url, page = [], URL, 0
while url and page < MAX_PAGES:
    page += 1
    data = get_page(url)
    jobs.extend(data["data"])
    print(f"page {page}: {len(data['data'])} jobs (total {len(jobs)})")
    url = data.get("links", {}).get("next")
    time.sleep(1)  # be polite to the free API

os.makedirs(OUT_DIR, exist_ok=True)
out = os.path.join(OUT_DIR, f"{date.today()}.json")
with open(out, "w", encoding="utf-8") as f:
    json.dump(jobs, f, ensure_ascii=False)
print(f"\nSaved {len(jobs)} jobs to {out}")