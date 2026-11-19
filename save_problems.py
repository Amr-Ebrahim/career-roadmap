import glob
import json
import os

import pandas as pd

files = [f for f in glob.glob("evals/*agent_*.csv") if "rescored" not in f]
latest = max(files, key=os.path.getmtime)
df = pd.read_csv(latest)

with open("problems_test.txt", "w", encoding="utf-8") as out:
    out.write(f"File: {latest}\n\n")
    for i, row in df.iterrows():
        label = " | ".join(str(row[c]) for c in df.columns[:2])
        out.write(f"=== Row {i}: {label} ===\n")
        problems = row.get("problems")
        if isinstance(problems, str) and problems.strip():
            try:
                items = json.loads(problems)
            except json.JSONDecodeError:
                items = [problems]
            if items:
                for p in items:
                    out.write(f"- {p}\n")
            else:
                out.write("(no problems)\n")
        else:
            out.write("(no problems column / failed row)\n")
        out.write("\n")

print("Saved problems_test.txt from", latest)
