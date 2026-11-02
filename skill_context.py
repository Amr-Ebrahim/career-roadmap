import sys
import pandas as pd
from skill_matcher import PATTERNS

skill = sys.argv[1]
patterns = [p for name, p in PATTERNS if name == skill]

df = pd.read_parquet("data/processed/jobs_skills.parquet")
posts = df[df["skills"].apply(lambda s: skill in s)]
print(f"{skill}: found in {len(posts)} posts")
print()

for _, row in posts.sample(min(15, len(posts)), random_state=0).iterrows():
    text = row["title"] + "\n" + row["description"]
    for p in patterns:
        m = p.search(text)
        if m:
            start, end = max(0, m.start() - 60), m.end() + 60
            snippet = text[start:end].replace("\n", " ")
            print(f"[{row['role_family']}] ...{snippet}...")
            break