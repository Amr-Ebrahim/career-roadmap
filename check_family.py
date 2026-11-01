import sys
import pandas as pd

path = sys.argv[1]
family = sys.argv[2]

df = pd.read_parquet(path)
titles = df[df["role_family"] == family]["title"]

print(f"{family}: {len(titles)} posts")
for t in titles.sample(min(30, len(titles)), random_state=1):
    print("  ", t)