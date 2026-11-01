import json
import re
import pandas as pd

with open("data/raw/arbeitnow.json", encoding="utf-8") as f:
    jobs = json.load(f)

df = pd.DataFrame(jobs)
print("Rows:", len(df))
print("Unique slugs:", df["slug"].nunique())
print()

df["posted_date"] = pd.to_datetime(df["created_at"], unit="s")
print("Dates from", df["posted_date"].min(), "to", df["posted_date"].max())
print()

print("Remote:", df["remote"].value_counts().to_dict())
print()

print("Top tags:")
print(df["tags"].explode().value_counts().head(15))
print()

print("Top locations:")
print(df["location"].value_counts().head(10))
print()

GERMAN = re.compile(r"\b(und|der|die|das|mit|für|wir|sie|ist|bei|oder)\b")


def german_hits(text):
    return len(GERMAN.findall(text[:2000].lower()))


df["german_hits"] = (df["title"] + " " + df["description"]).apply(german_hits)
df["is_german"] = df["german_hits"] >= 8

print("Looks German:", df["is_german"].sum(), "of", len(df))
print()
print("Sample English titles:")
for t in df.loc[~df["is_german"], "title"].sample(10, random_state=42):
    print("  ", t)
print("Sample German titles:")
for t in df.loc[df["is_german"], "title"].sample(10, random_state=42):
    print("  ", t)