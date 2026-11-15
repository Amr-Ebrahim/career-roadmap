# peek_low_skill_seniors.py - read senior posts where we found few skills (no tokens)
import pandas as pd

df = pd.read_parquet("data/processed/jobs_skills.parquet",
                     columns=["title", "company_name", "role_family", "level",
                              "level_source", "description", "skills"])
df = df[(df["role_family"] == "devops_cloud") & (df["level"] == "senior")
        & (df["level_source"] == "title")]
df = df.assign(n_skills=df["skills"].apply(len),
               desc_words=df["description"].str.split().str.len())

# long descriptions but few skills found: the most suspicious cases
low = df[(df["desc_words"] > 400) & (df["n_skills"] <= 3)]
print(f"{len(low)} of {len(df)} senior posts have 400+ words but 3 or fewer skills found\n")

for _, p in low.sample(min(3, len(low)), random_state=2).iterrows():
    print("=" * 100)
    print(f"{p['title']} | {p['company_name']} | {p['desc_words']} words | skills: {list(p['skills'])}")
    print("-" * 100)
    print(p["description"][:1500])
    print()