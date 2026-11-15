import glob
import html
import json
import os

import pandas as pd
from bs4 import BeautifulSoup
from langdetect import DetectorFactory, LangDetectException, detect
from roles import label_role

DetectorFactory.seed = 0

# every weekly snapshot, oldest first; the same post can appear in several of them
frames = []
for path in sorted(glob.glob("data/raw/arbeitnow/*.json")):
    with open(path, encoding="utf-8") as f:
        frames.append(pd.DataFrame(json.load(f)))
    print(f"Snapshot {os.path.basename(path)}: {len(frames[-1])} jobs")

# keep the newest version of each post (keep="last" because files are sorted oldest first)
df = pd.concat(frames, ignore_index=True).drop_duplicates(subset="slug", keep="last")
print(f"Unique posts across {len(frames)} snapshots: {len(df)}")


def clean_html(raw):
    text = html.unescape(raw)
    return BeautifulSoup(text, "html.parser").get_text(" ", strip=True)


def language(text):
    try:
        return detect(text[:1000])
    except LangDetectException:
        return "unknown"


df["description"] = df["description"].apply(clean_html)
df["lang"] = df["description"].apply(language)
print("Languages:", df["lang"].value_counts().head(8).to_dict())

df = df[df["lang"] == "en"].copy()
df["role_family"] = df["title"].apply(label_role)
tech = df[df["role_family"].notna()]

print("English posts:", len(df))
print("English tech posts:", len(tech))
print()
print(tech["role_family"].value_counts())
print()
for t in tech["title"].sample(min(15, len(tech)), random_state=42):
    print("  ", t)

out = pd.DataFrame({
    "job_id": "arbeitnow_" + tech["slug"],
    "title": tech["title"],
    "description": tech["description"],
    "company_name": tech["company_name"],
    "location": tech["location"],
    "remote_allowed": tech["remote"],
    "formatted_experience_level": None,
    "job_posting_url": tech["url"],
    "role_family": tech["role_family"],
    "posted_date": pd.to_datetime(tech["created_at"], unit="s"),
    "source": "arbeitnow",
})

os.makedirs("data/processed", exist_ok=True)
out.to_parquet("data/processed/jobs_arbeitnow.parquet", index=False)
print()
print("Saved", len(out), "posts to data/processed/jobs_arbeitnow.parquet")