# check_ai_titles.py - how many Arbeitnow ai_ml posts are real AI/ML engineering jobs? (no tokens)
import pandas as pd

df = pd.read_parquet("data/processed/jobs_skills.parquet",
                     columns=["title", "role_family", "source", "skills"])
ai = df[(df["role_family"] == "ai_ml") & (df["source"] == "arbeitnow")]

ENGINEERING = r"engineer|developer|scientist|research|architect|ml|machine learning|data|mlops|programmer"
looks_technical = ai["title"].str.contains(ENGINEERING, case=False)

print(f"Arbeitnow ai_ml posts: {len(ai)}")
print(f"  titles with an engineering word: {int(looks_technical.sum())}")
print(f"  titles without one:              {int((~looks_technical).sum())}")

print("\n=== 30 random titles WITHOUT an engineering word")
others = ai[~looks_technical]
for _, p in others.sample(min(30, len(others)), random_state=3).iterrows():
    print(f"  {p['title'][:70]:<70} | {len(p['skills'])} skills")