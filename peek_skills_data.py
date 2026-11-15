# peek_skills_data.py - look at the columns before we build the stats tool
import glob

import pandas as pd

pd.set_option("display.max_colwidth", 80)

path = glob.glob("data/**/jobs_skills.parquet", recursive=True)[0]
df = pd.read_parquet(path)

print("File:", path)
print("Rows, columns:", df.shape)
print("\n--- column types ---")
print(df.dtypes)
print("\n--- first row ---")
print(df.iloc[0])