import pandas as pd

COLS = ["job_id", "title", "description", "skills_desc", "company_name",
        "location", "remote_allowed", "formatted_experience_level",
        "listed_time", "job_posting_url"]

df = pd.read_csv("data/raw/postings.csv", usecols=COLS)

print("Rows:", len(df))
print("RAM used (MB):", round(df.memory_usage(deep=True).sum() / 1e6))
print()

print("Missing values per column:")
print(df.isna().sum())
print()

print("Experience levels:")
print(df["formatted_experience_level"].value_counts(dropna=False))
print()

df["listed_date"] = pd.to_datetime(df["listed_time"], unit="ms")
print("Dates from", df["listed_date"].min(), "to", df["listed_date"].max())
print()

print("Top 20 job titles:")
print(df["title"].value_counts().head(20))