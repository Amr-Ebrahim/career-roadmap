import re
import pandas as pd

skills = pd.read_csv("data/raw/esco/digitalSkillsCollection_en.csv")
print("Rows:", len(skills))
print("Columns:", skills.columns.tolist())
print()
print(skills[["preferredLabel", "altLabels"]].head(10).to_string())
print()

CHECK = ["python", "sql", "java", "javascript", "docker", "kubernetes", "aws",
         "pytorch", "tensorflow", "react", "langchain", "git", "linux",
         "power bi", "terraform", "kafka", "spark", "llm", "rag"]

text = (skills["preferredLabel"].fillna("") + "\n" + skills["altLabels"].fillna("")).str.lower()

print("Coverage check:")
for word in CHECK:
    hits = skills.loc[text.str.contains(rf"\b{re.escape(word)}\b", regex=True), "preferredLabel"]
    print(f"  {word:12} -> {len(hits):3}  {hits.head(3).tolist()}")