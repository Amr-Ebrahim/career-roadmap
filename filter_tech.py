import os
import re
import pandas as pd

COLS = ["job_id", "title", "description", "company_name", "location",
        "remote_allowed", "formatted_experience_level", "listed_time",
        "job_posting_url"]

df = pd.read_csv("data/raw/postings.csv", usecols=COLS)

ROLE_FAMILIES = {
    "ai_ml": ["machine learning", "ml", "mlops", "ai", "artificial intelligence",
              "deep learning", "nlp", "computer vision", "llm"],
    "data": ["data scientist", "data science", "data engineer", "data analyst",
             "analytics engineer", "business intelligence", "bi developer",
             "bi analyst", "etl", "big data", "data architect",
             "database administrator", "dba", "sql developer"],
    "security": ["cyber ?security", "cyber", "information security", "infosec",
                 "security engineer", "security analyst", "soc analyst",
                 "penetration tester", "appsec", "devsecops"],
    "devops_cloud": ["devops", "site reliability", "sre", "platform engineer",
                     "infrastructure engineer", "solutions? architect",
                     "cloud (engineer|architect|developer|administrator)"],
    "mobile": ["ios", "android", "flutter", "react native",
               "mobile (developer|engineer)"],
    "frontend": ["front[- ]?end", "ui developer", "ui engineer", "web developer",
                 "javascript developer", "react developer", "angular developer"],
    "backend": ["back[- ]?end", "java developer", "java architect", "python developer",
                "net developer", "node(js)? developer", "golang", "php developer",
                "ruby developer", "api developer"],
    "qa": ["qa engineer", "qa analyst", "qa automation", "sdet",
           "quality assurance engineer", "software test(er)?",
           "test automation", "game tester"],
    "networking_it": ["network engineer", "network administrator",
                      "network technician", "it support", "help ?desk",
                      "desktop support", "service desk", "systems? administrator",
                      "sysadmin", "technical support", "noc", "it specialist",
                      "it technician", "information technology"],
    "software": ["software", "developer", "programmer", "full[- ]?stack"],
}

PATTERNS = {
    family: re.compile(r"\b(" + "|".join(words) + r")\b")
    for family, words in ROLE_FAMILIES.items()
}

EXCLUDE = re.compile(r"\b(sales|recruit\w*|marketing|account executive|account manager"
                     r"|insurance|underwriter|industrial security|curriculum)\b")


def label_role(title):
    t = title.lower()
    if EXCLUDE.search(t):
        return None
    for family, pattern in PATTERNS.items():
        if pattern.search(t):
            return family
    return None


df["role_family"] = df["title"].apply(label_role)
tech = df[df["role_family"].notna()]

print("Tech posts:", len(tech), f"({len(tech) / len(df):.1%} of all)")
print()
print(tech["role_family"].value_counts())
print()

for family in ROLE_FAMILIES:
    titles = tech[tech["role_family"] == family]["title"]
    sample = titles.sample(min(8, len(titles)), random_state=42)
    print(f"--- {family} ---")
    for t in sample:
        print("  ", t)

print()
print("=== Possibly missed: unlabeled titles with engineer/architect/technology ===")
missed = df[
    df["role_family"].isna()
    & df["title"].str.lower().str.contains(r"\b(?:engineer|architect|technolog\w*)\b", regex=True)
]
print(missed["title"].value_counts().head(40))

tech = tech.copy()
tech["posted_date"] = pd.to_datetime(tech["listed_time"], unit="ms")
tech = tech.drop(columns=["listed_time"])
tech["source"] = "kaggle_linkedin"

os.makedirs("data/processed", exist_ok=True)
out = "data/processed/jobs_tech.parquet"
tech.to_parquet(out, index=False)

print()
print("Saved", len(tech), "posts to", out)
print("CSV size (MB):    ", round(os.path.getsize("data/raw/postings.csv") / 1e6))
print("Parquet size (MB):", round(os.path.getsize(out) / 1e6, 1))