import pandas as pd

kaggle = pd.read_parquet("data/processed/jobs_tech.parquet")
arbeit = pd.read_parquet("data/processed/jobs_arbeitnow.parquet")

kaggle["job_id"] = "kaggle_" + kaggle["job_id"].astype(str)
kaggle["remote_allowed"] = kaggle["remote_allowed"].map({1.0: True}).astype("boolean")
arbeit["remote_allowed"] = arbeit["remote_allowed"].astype("boolean")

jobs = pd.concat([kaggle, arbeit], ignore_index=True)
print("Combined:", len(jobs))

before = len(jobs)
jobs = jobs.drop_duplicates(subset=["title", "company_name", "description"])
print("Duplicates removed:", before - len(jobs))
print("Final:", len(jobs))
print()

print(pd.crosstab(jobs["role_family"], jobs["source"], margins=True))
print()
print("Remote values:", jobs["remote_allowed"].value_counts(dropna=False).to_dict())

jobs.to_parquet("data/processed/jobs_all.parquet", index=False)
print()
print("Saved data/processed/jobs_all.parquet")