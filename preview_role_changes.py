# preview_role_changes.py - what would the new roles.py change? (reads only, changes nothing)
import pandas as pd

from roles import label_role

pd.set_option("display.width", 140)

df = pd.read_parquet("data/processed/jobs_skills.parquet", columns=["title", "role_family"])
df["new_family"] = df["title"].apply(label_role).fillna("NONE")

changed = df[df["role_family"] != df["new_family"]]
print(f"{len(changed)} of {len(df)} posts would change family\n")
print("=== old family (rows) -> new family (columns)")
print(pd.crosstab(changed["role_family"], changed["new_family"]))

print("\n=== most common changed titles")
print(changed.groupby(["role_family", "new_family"])["title"]
      .value_counts().groupby(level=[0, 1]).head(5).to_string())