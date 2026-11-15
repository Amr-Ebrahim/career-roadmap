# verify_role_update.py - compare the backup with the new parquet after re-running the pipeline
import pandas as pd

old = pd.read_parquet("data/processed/jobs_skills_backup.parquet").set_index("job_id")
new = pd.read_parquet("data/processed/jobs_skills.parquet").set_index("job_id")

removed = old.index.difference(new.index)
added = new.index.difference(old.index)
print("Posts before / after:", len(old), "/", len(new))
print("Removed posts:", len(removed), "| Added posts:", len(added), "(added should be 0)")
if len(removed):
    print("  removed posts came from:", old.loc[removed, "role_family"].value_counts().to_dict())

common = old.index.intersection(new.index)
for col in ["role_family", "level", "level_source", "n_skills", "title"]:
    diff = (old.loc[common, col].fillna("") != new.loc[common, col].fillna("")).sum()
    print(f"  {col:<14} changed in {int(diff)} posts")

print("\nPosts per family now:")
print(new["role_family"].value_counts().to_string())