import subprocess
import sys

STEPS = ["filter_tech.py", "process_arbeitnow.py", "merge_sources.py",
         "clean_jobs.py", "extract_skills.py"]

for step in STEPS:
    print(f"\n========== {step} ==========")
    subprocess.run([sys.executable, step], check=True)

print("\nPipeline finished.")