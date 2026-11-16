# compare_skills.py - how did a skill-matcher change move the counts?
# Usage: python compare_skills.py data/processed/jobs_skills_before.parquet
import sys

import pandas as pd

old = pd.read_parquet(sys.argv[1], columns=["job_id", "skills"]).set_index("job_id")
new = pd.read_parquet("data/processed/jobs_skills.parquet", columns=["job_id", "skills"]).set_index("job_id")
old_counts = old["skills"].explode().value_counts()
new_counts = new["skills"].explode().value_counts()

table = pd.DataFrame({"before": old_counts, "after": new_counts}).fillna(0).astype(int)
table["gained"] = table["after"] - table["before"]
table["change_%"] = (table["gained"] / table["before"].clip(lower=1) * 100).round(1)
moved = table[table["gained"] != 0].sort_values("gained", ascending=False)

print(f"Posts: {len(new)}  |  skill mentions before {table['before'].sum()}, after {table['after'].sum()}")
print(f"Posts with 0 skills: before {(old['skills'].apply(len) == 0).sum()}, "
      f"after {(new['skills'].apply(len) == 0).sum()}")
print(f"\nSkills that changed ({len(moved)}), biggest first:")
print(moved.head(30).to_string())