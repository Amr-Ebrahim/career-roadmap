import re
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

EXCLUDE = re.compile(
    r"\b(sales|recruit\w*|marketing|account executive|account manager"
    r"|insurance|underwriter|industrial security|curriculum"
    r"|product manager|product owner|project (?:lead|manager)|delivery lead"
    r"|operations manager|associate partner|managing partner|consulting manager"
    r"|regulatory|ai trainer|strategist|volunteer"
    r"|stylist|model validation)\b"
)


def label_role(title):
    t = title.lower()
    if EXCLUDE.search(t):
        return None
    for family, pattern in PATTERNS.items():
        if pattern.search(t):
            return family
    return None