# verify_role_update.py - after re-running the pipeline: did ONLY role_family change?
import pandas as pd

old = pd.read_parquet("data/processed/jobs_skills_backup.parquet").set_index("job_id")
new = pd.read_parquet("data/processed/jobs_skills.parquet").set_index("job_id")

print("Posts before / after:", len(old), "/", len(new))
print("Same job ids:", set(old.index) == set(new.index))

new = new.loc[old.index]
for col in ["role_family", "level", "level_source", "n_skills", "title"]:
    print(f"  {col:<14} changed in {int((old[col].fillna('') != new[col].fillna('')).sum())} posts")

print("\nPosts per family now:")
print(new["role_family"].value_counts().to_string())