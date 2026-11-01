import os
from roles import ROLE_FAMILIES, label_role
import pandas as pd

COLS = ["job_id", "title", "description", "company_name", "location",
        "remote_allowed", "formatted_experience_level", "listed_time",
        "job_posting_url"]

df = pd.read_csv("data/raw/postings.csv", usecols=COLS)


df["role_family"] = df["title"].apply(label_role)
tech = df[df["role_family"].notna()]

print("Tech posts:", len(tech), f"({len(tech) / len(df):.1%} of all)")
print()
print(tech["role_family"].value_counts())
print()

for family in ROLE_FAMILIES:
    titles = tech[tech["role_family"] == family]["title"]
    sample = titles.sample(min(8, len(titles)), random_state=42)
    print(f"--- {family} ---")
    for t in sample:
        print("  ", t)

print()
print("=== Possibly missed: unlabeled titles with engineer/architect/technology ===")
missed = df[
    df["role_family"].isna()
    & df["title"].str.lower().str.contains(r"\b(?:engineer|architect|technolog\w*)\b", regex=True)
]
print(missed["title"].value_counts().head(40))

tech = tech.copy()
tech["posted_date"] = pd.to_datetime(tech["listed_time"], unit="ms")
tech = tech.drop(columns=["listed_time"])
tech["source"] = "kaggle_linkedin"

os.makedirs("data/processed", exist_ok=True)
out = "data/processed/jobs_tech.parquet"
tech.to_parquet(out, index=False)

print()
print("Saved", len(tech), "posts to", out)
print("CSV size (MB):    ", round(os.path.getsize("data/raw/postings.csv") / 1e6))
print("Parquet size (MB):", round(os.path.getsize(out) / 1e6, 1))