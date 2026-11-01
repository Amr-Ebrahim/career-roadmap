import pandas as pd
from cleaning import COMPATIBLE, KAGGLE_TO_LEVEL, clean_title, level_from_title

df = pd.read_parquet("data/processed/jobs_all.parquet")
df["title_clean"] = df["title"].apply(clean_title)
df["title_level"] = df["title_clean"].apply(level_from_title)

both = df[df["title_level"].notna() & df["formatted_experience_level"].notna()]
agree = both.apply(
    lambda r: r["formatted_experience_level"] in COMPATIBLE[r["title_level"]], axis=1
)

print("Posts with both a title level and a Kaggle label:", len(both))
print(f"Agreement: {agree.mean():.1%}")
print()
print(pd.crosstab(both["title_level"], both["formatted_experience_level"]))
print()

print("Disagreements (sample):")
wrong = both[~agree]
for _, r in wrong.sample(min(15, len(wrong)), random_state=3).iterrows():
    print(f"  [title says {r['title_level']}, label says {r['formatted_experience_level']}] {r['title_clean']}")
print()

df["kaggle_level"] = df["formatted_experience_level"].map(KAGGLE_TO_LEVEL)
df["level"] = df["title_level"].fillna(df["kaggle_level"]).fillna("unknown")
print(pd.crosstab(df["level"], df["source"], margins=True))