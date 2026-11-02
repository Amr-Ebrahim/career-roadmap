import sys
import time
import pandas as pd
from skill_matcher import extract_skills

df = pd.read_parquet("data/processed/jobs_clean.parquet")

if len(sys.argv) > 1:
    df = df.sample(int(sys.argv[1]), random_state=0)
    print("SAMPLE RUN:", len(df), "posts (not saved)")

start = time.perf_counter()
df["skills"] = (df["title"] + "\n" + df["description"]).apply(extract_skills)
print(f"Extraction took {time.perf_counter() - start:.1f} s for {len(df)} posts")

df["n_skills"] = df["skills"].apply(len)
print("Average skills per post:", round(df["n_skills"].mean(), 1))
print("Posts with 0 skills:", (df["n_skills"] == 0).sum())
print()

counts = df["skills"].explode().value_counts()
print("Top 30 skills (% of posts):")
print((counts / len(df) * 100).round(1).head(30).to_string())
print()

for family in ["ai_ml", "data", "devops_cloud", "networking_it", "security", "frontend"]:
    sub = df[df["role_family"] == family]
    top = sub["skills"].explode().value_counts().head(8)
    print(f"{family:14} -> " + ", ".join(f"{s} {c / len(sub):.0%}" for s, c in top.items()))

if len(sys.argv) == 1:
    df.to_parquet("data/processed/jobs_skills.parquet", index=False)
    print()
    print("Saved data/processed/jobs_skills.parquet")