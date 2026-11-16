# pipeline_stats.py - how many posts survive each step of the data pipeline (no LLM, no tokens).
# Reads the files the pipeline already wrote; for the README's data funnel.
#   python pipeline_stats.py
import glob
import json
import os

import pandas as pd


def show(label, value):
    print(f"  {label:<48} {value}")


print("KAGGLE (LinkedIn postings)")
if os.path.exists("data/raw/postings.csv"):
    raw = pd.read_csv("data/raw/postings.csv", usecols=["job_id"])
    show("all posts in postings.csv", f"{len(raw):,}")
else:
    show("all posts in postings.csv", "(file not on this machine)")
if os.path.exists("data/processed/jobs_tech.parquet"):
    tech = pd.read_parquet("data/processed/jobs_tech.parquet")
    show("tech posts kept by filter_tech", f"{len(tech):,}")
    if "role_family" in tech:
        show("  by role family", tech["role_family"].value_counts().to_dict())

print("\nARBEITNOW (job board API)")
snaps = sorted(glob.glob("data/raw/arbeitnow/*.json"))
slugs, total = set(), 0
for path in snaps:
    with open(path, encoding="utf-8") as f:
        jobs = json.load(f)
    total += len(jobs)
    slugs.update(j["slug"] for j in jobs)
    show(f"snapshot {os.path.basename(path)}", f"{len(jobs):,} posts")
show("all snapshots together", f"{total:,} posts, {len(slugs):,} unique")
if os.path.exists("data/processed/jobs_arbeitnow.parquet"):
    arb = pd.read_parquet("data/processed/jobs_arbeitnow.parquet")
    show("English tech posts kept by process_arbeitnow", f"{len(arb):,}")

print("\nMERGED AND CLEANED")
for name, path in [("jobs_all (merge_sources)", "data/processed/jobs_all.parquet"),
                   ("jobs_clean (clean_jobs)", "data/processed/jobs_clean.parquet"),
                   ("jobs_skills (extract_skills)", "data/processed/jobs_skills.parquet")]:
    if os.path.exists(path):
        df = pd.read_parquet(path)
        show(name, f"{len(df):,} posts, columns: {', '.join(df.columns)}")

df = pd.read_parquet("data/processed/jobs_skills.parquet")
show("by source", df["source"].value_counts().to_dict())
show("by level", df["level"].value_counts(dropna=False).to_dict())
show("by role family", df["role_family"].value_counts().to_dict())
n_skills = df["skills"].apply(len)
show("posts with at least 1 skill (indexed)", f"{(n_skills > 0).sum():,}")
show("average skills per post", round(n_skills.mean(), 1))
show("distinct skills found", df["skills"].explode().nunique())
dates = pd.to_datetime(df["posted_date"])
for source, group in df.assign(d=dates).groupby("source"):
    show(f"date range {source}", f"{group['d'].min():%Y-%m-%d} to {group['d'].max():%Y-%m-%d}")

print("\nSEARCH INDEX")
try:
    import chromadb
    col = chromadb.PersistentClient(path="data/chroma").get_collection("job_chunks")
    show("chunks in ChromaDB", f"{col.count():,}")
except Exception as e:
    show("chunks in ChromaDB", f"(could not open: {type(e).__name__})")
