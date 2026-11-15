# check_senior_titles.py - what are "senior devops_cloud" posts really? (no tokens)
import pandas as pd

pd.set_option("display.width", 120)

df = pd.read_parquet("data/processed/jobs_skills.parquet",
                     columns=["title", "role_family", "level", "skills"])
df = df[(df["role_family"] == "devops_cloud") & df["level"].isin(["entry", "mid", "senior"])]
df = df.assign(n_skills=df["skills"].apply(len),
               architect=df["title"].str.contains("architect", case=False),
               sap=df["title"].str.contains(r"\bSAP\b"))

print("=== Skills found per level: architect titles vs the rest")
print(df.groupby(["level", "architect"])["n_skills"].agg(["mean", "count"]).round(1))

print(f"\nSAP titles in devops_cloud: {int(df['sap'].sum())}")

print("\n=== 25 most common senior titles")
print(df[df["level"] == "senior"]["title"].value_counts().head(25).to_string())
