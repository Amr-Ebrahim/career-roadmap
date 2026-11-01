import pandas as pd
from cleaning import clean_title

df = pd.read_parquet("data/processed/jobs_all.parquet")
df["title_clean"] = df["title"].apply(clean_title)

changed = df[df["title"] != df["title_clean"]]
print("Titles changed:", len(changed), "of", len(df))
print()

for _, row in changed.sample(25, random_state=7).iterrows():
    print("BEFORE:", row["title"])
    print("AFTER: ", row["title_clean"])
    print()