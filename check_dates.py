# check_dates.py - which time periods does each source cover? (no tokens)
import pandas as pd

df = pd.read_parquet("data/processed/jobs_skills.parquet",
                     columns=["job_id", "source", "posted_date"])

print("=== Date range per source")
print(df.groupby("source")["posted_date"].agg(["min", "max", "count"]).to_string())

print("\n=== Posts per month and source")
months = df["posted_date"].dt.to_period("M")
table = pd.crosstab(months, df["source"])
print(table.to_string())

print("\nPosts with no date:", int(df["posted_date"].isna().sum()))