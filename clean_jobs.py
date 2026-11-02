import pandas as pd
from cleaning import KAGGLE_TO_LEVEL, clean_title, level_from_title, min_years_required

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
df = df[~short].copy()

df["min_years"] = df["description"].apply(min_years_required).astype(float)


def years_to_level(years):
    if years < 3:
        return "entry"
    if years < 5:
        return "mid"
    return "senior"


too_junior = df["level"].isin(["entry", "intern"]) & (df["min_years"] >= 3)
unknown_with_years = (df["level"] == "unknown") & df["min_years"].notna()
fix = too_junior | unknown_with_years

df.loc[fix, "level"] = df.loc[fix, "min_years"].apply(years_to_level)
df.loc[fix, "level_source"] = "years"
print("Junior levels corrected from stated years:", too_junior.sum())
print("Unknown levels filled from stated years:", unknown_with_years.sum())

df.to_parquet("data/processed/jobs_clean.parquet", index=False)
print("Saved", len(df), "posts to data/processed/jobs_clean.parquet")
print()
print(pd.crosstab(df["level"], df["source"], margins=True))
print()
print("Level source:", df["level_source"].value_counts().to_dict())