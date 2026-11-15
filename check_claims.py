# check_claims.py - are the words the judge called "unsupported" really missing
# from the sources? Uses retrieval only, no Groq tokens.
from retrieval import retrieve

CHECKS = [
    ("What skills do I need to get an entry-level cloud engineer job?", "devops_cloud", "entry",
     ["Linux", "Ansible", "CI/CD", "automation", "Redshift", "scientist", "business unit"]),
    ("What do entry-level help desk jobs require?", "networking_it", "entry",
     ["SCCM", "Autopilot", "PowerShell", "SharePoint", "VPN", "365", "graduate", "school",
      "pressure", "composure", "non-technical"]),
    ("Which tools do entry-level security analyst jobs ask for?", "security", "entry",
     ["SIEM", "email security", "vulnerability", "patch", "identity", "VMware", "Docker",
      "CyberChef", "WAF", "IDS", "Linux", "command line"]),
    ("What skills do entry-level backend developer jobs ask for?", "software", "entry",
     ["Django", "Node", "Spring", "C#", ".NET", "PostgreSQL", "ETL", "REST", "Git", "Playwright",
      "Cypress", "Azure"]),
    ("Which certifications do entry-level IT support jobs mention?", "networking_it", "entry",
     ["A+", "Network+", "Security+", "MCITP", "CCENT", "ITIL", "Apple", "ACMT", "Google IT",
      "VMware", "Dell", "Ubiquiti"]),
]

for question, family, level, words in CHECKS:
    posts = retrieve(question, role_family=family, level=level)
    print(f"\n=== {question}")
    for word in words:
        found = [str(i) for i, p in enumerate(posts, start=1) if word.lower() in p["text"].lower()]
        print(f"  {word:<16} {'in [' + ','.join(found) + ']' if found else 'NOT FOUND'}")