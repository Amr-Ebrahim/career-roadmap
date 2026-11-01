import pandas as pd
from cleaning import KAGGLE_TO_LEVEL, clean_title, level_from_title

df = pd.read_parquet("data/processed/jobs_all.parquet")
print("Input:", len(df))

df["title_raw"] = df["title"]
df["title"] = df["title_raw"].apply(clean_title)

title_level = df["title"].apply(level_from_title)
kaggle_level = df["formatted_experience_level"].map(KAGGLE_TO_LEVEL)
df["level"] = title_level.fillna(kaggle_level).fillna("unknown")

df["level_source"] = "none"
df.loc[kaggle_level.notna(), "level_source"] = "kaggle"
df.loc[title_level.notna(), "level_source"] = "title"

df["description"] = df["description"].fillna("").str.strip()
short = df["description"].str.len() < 200
print("Removed (description under 200 characters):", short.sum())
df = df[~short]

df.to_parquet("data/processed/jobs_clean.parquet", index=False)
print("Saved", len(df), "posts to data/processed/jobs_clean.parquet")
print()
print(pd.crosstab(df["level"], df["source"], margins=True))
print()
print("Level source:", df["level_source"].value_counts().to_dict())