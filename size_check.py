import pandas as pd

df = pd.read_parquet("data/processed/jobs_tech.parquet")
chars = df["description"].str.len()

print("Posts:", len(df))
print("Average characters per post:", int(chars.mean()))
print("Estimated total tokens:", int(chars.sum() / 4))