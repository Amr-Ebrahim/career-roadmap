# check_levels.py - why do senior posts show lower skill shares? (no tokens)
import pandas as pd

pd.set_option("display.width", 120)

df = pd.read_parquet("data/processed/jobs_skills.parquet",
                     columns=["job_id", "role_family", "level", "level_source", "source",
                              "formatted_experience_level", "title", "description", "skills"])
df = df[(df["role_family"] == "devops_cloud") & df["level"].isin(["entry", "mid", "senior"])]
df = df.assign(n_skills=df["skills"].apply(len),
               desc_words=df["description"].str.split().str.len())

print("=== Skills found per level, split by WHERE the level label came from")
print(df.groupby(["level", "level_source"])[["n_skills", "desc_words"]]
        .agg(["mean", "count"]).round(1))

print("\n=== Kaggle's own label for posts we call senior")
senior = df[df["level"] == "senior"]
print(senior["formatted_experience_level"].value_counts(dropna=False))

print("\n=== 10 random senior titles labeled by the Kaggle label")
sample = senior[senior["level_source"] == "kaggle"]
print(sample["title"].sample(min(10, len(sample)), random_state=1).to_string())