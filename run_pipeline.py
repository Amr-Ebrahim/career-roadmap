# run_pipeline.py - runs the data pipeline steps in order.
# filter_tech.py needs the Kaggle postings.csv. That file only lives on the laptop (it is big and
# not ours to publish), so where it is missing - e.g. in the weekly GitHub Action - the step is
# skipped and the already-filtered Kaggle posts (data/processed/jobs_tech.parquet) are reused.
import os
import subprocess
import sys

STEPS = ["filter_tech.py", "process_arbeitnow.py", "merge_sources.py",
         "clean_jobs.py", "extract_skills.py"]
KAGGLE_CSV = "data/raw/postings.csv"
KAGGLE_FILTERED = "data/processed/jobs_tech.parquet"

for step in STEPS:
    if step == "filter_tech.py" and not os.path.exists(KAGGLE_CSV):
        if not os.path.exists(KAGGLE_FILTERED):
            sys.exit(f"Need {KAGGLE_CSV} or {KAGGLE_FILTERED} to start the pipeline.")
        print(f"\n========== {step}: skipped ==========")
        print(f"{KAGGLE_CSV} is not here, reusing {KAGGLE_FILTERED} (the Kaggle posts never change).")
        continue
    print(f"\n========== {step} ==========")
    subprocess.run([sys.executable, step], check=True)

print("\nPipeline finished.")
