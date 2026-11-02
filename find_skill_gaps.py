import re
from collections import Counter
import pandas as pd
from skill_matcher import extract_skills

df = pd.read_parquet("data/processed/jobs_skills.parquet")
sample = df.sample(3000, random_state=0)

TOKEN = re.compile(
    r"(?<![\w+#.])(?:[A-Z][a-z]+[A-Z][\w]*|[A-Z]{3,6}\d*|[A-Za-z]+(?:\.js|\.NET|\+\+|#))(?![\w+#])"
)
STOP = {"USA", "EEO", "EOE", "LLC", "INC", "CEO", "CFO", "CTO", "PTO", "AND", "THE",
        "FOR", "III", "ADA", "FMLA", "COVID", "DOE", "FAQ", "NOT", "ALL", "YOU", "OUR",
        "USD", "LINKEDIN", "PHD", "DOD", "MUST", "JOB", "SCI", "HSA", "FSA", "NYC", "GED",
        "SKILLS", "USC", "REMOTE", "EAP", "SME", "NYSE", "STEM", "IBM", "SAAS", "PAAS",
        "CRM", "ERP", "ISO", "DBA", "HTTP", "ASP", "DEVELOPERLOCATION", "ENGINEERLOCATION"}

doc_freq = Counter()
for text in sample["description"]:
    tokens = set(TOKEN.findall(text))
    doc_freq.update(t for t in tokens if t.upper() not in STOP)

print("Possibly missing skills (% of sampled posts):")
shown = 0
for token, count in doc_freq.most_common(400):
    if extract_skills(token):
        continue
    print(f"  {token:20} {count / len(sample):.1%}")
    shown += 1
    if shown == 60:
        break

print()
print("Titles of posts with zero skills:")
for t in df[df["n_skills"] == 0]["title"].sample(20, random_state=1):
    print("  ", t)