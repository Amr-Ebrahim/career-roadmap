import json
from collections import Counter

with open("data/raw/remotive.json", encoding="utf-8") as f:
    data = json.load(f)

print("WARNING:", data["00-warning"])
print()
print("LEGAL:", data["0-legal-notice"])
print()
print("job-count:", data["job-count"])
print("total-job-count:", data["total-job-count"])
print()
print("Categories:", Counter(job["category"] for job in data["jobs"]))
print("Dates:", [job["publication_date"][:10] for job in data["jobs"]])