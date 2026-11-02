import pandas as pd
from cleaning import min_years_required, years_mentions

df = pd.read_parquet("data/processed/jobs_skills.parquet")
df["min_years"] = df["description"].apply(min_years_required).astype(float)

print("Posts stating years of experience:", df["min_years"].notna().sum(), "of", len(df))
print()

bucket = df["min_years"].fillna(-1).clip(upper=8).astype(int)
print("Level vs minimum years (-1 = none stated, 8 = 8 or more):")
print(pd.crosstab(df["level"], bucket))
print()

junior = df["level"].isin(["entry", "intern"])
conflicts = df[junior & (df["min_years"] >= 3)]
print(f"Entry/intern posts asking 3+ years: {len(conflicts)} of {junior.sum()}")
print()

for _, r in conflicts.sample(12, random_state=0).iterrows():
    snippets = [s for y, s in years_mentions(r["description"])]
    print(f"[{r['level']} from {r['level_source']}, {int(r['min_years'])}y] {r['title']}")
    print(f"     matched: {snippets}")