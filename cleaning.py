import re

BRACKETS = re.compile(r"【[^】]*】")

GENDER = re.compile(
    r"\(\s*(?:[mfwdxh]\s*(?:/\s*[mfwdxh*]\s*)+|all genders?|gn\*?|div\.?)\s*\)",
    re.IGNORECASE,
)
GENDER_BARE = re.compile(r"\b[mfwdxh](?:/[mfwdxh]){1,2}\s*$", re.IGNORECASE)

STAFFING = re.compile(
    r"\b(?:only\s+(?:on\s+)?|on\s+)?w-?2(?:\s+(?:only|contract|role|candidates?(?:\s+only)?))?\b"
    r"|\b(?:no\s+)?(?:c2c|corp\s+to\s+corp)\b"
    r"|\b(?:only\s+)?locals?\s+(?:candidates?|profiles?)(?:\s+only)?|\b(?:only\s+)?locals\b(?:\s+only)?|\bonly\s+local\b"
    r"|\busc(?:\s*/\s*gc)?(?:\s+only)?\b"
    r"|\b(?:immediate\s+need|urgent(?:\s+need)?)\b"
    r"|^\s*(?:hiring\s+for|full[- ]time\s+job\s*:)",
    re.IGNORECASE,
)

JOB_CODES = re.compile(r"\([A-Z]*-?\d{4,}[A-Z]*\)|\bR-?\d{5,}\b")

EXTRA_PUNCT = re.compile(r"!!+|\|\|+|::+|\*+")
PAREN_OPEN = re.compile(r"\(\s*[\-–/|:,\s]*")
PAREN_CLOSE = re.compile(r"[\s\-–/|:,]*\)")
EMPTY_PARENS = re.compile(r"\(\s*\)")
SPACES = re.compile(r"\s{2,}")
EDGES = re.compile(r"^[\s\-–|:,/]+|[\s\-–|:,/]+$")


def clean_title(title):
    t = BRACKETS.sub(" ", title)
    t = GENDER.sub(" ", t)
    t = GENDER_BARE.sub(" ", t)
    t = STAFFING.sub(" ", t)
    t = JOB_CODES.sub(" ", t)
    t = EXTRA_PUNCT.sub(" ", t)
    t = PAREN_OPEN.sub("(", t)
    t = PAREN_CLOSE.sub(")", t)
    t = EMPTY_PARENS.sub(" ", t)
    t = SPACES.sub(" ", t)
    t = EDGES.sub("", t)
    return t


LEVEL_RULES = [
    ("intern", re.compile(r"\b(?:intern|internship|working student|trainee|apprentice\w*|co-?op)\b")),
    ("leadership", re.compile(r"\b(?:head of|director|s?vp|vice president|chief|cto|cio|ciso|manager|supervisor)\b")),
    ("senior", re.compile(r"\b(?:senior|sr|staff|principal|lead|architect|iii|iv)\b")),
    ("entry", re.compile(r"\b(?:junior|jr|entry[- ]level|graduate|new grad|associate|i|ii)\b")),
    ("mid", re.compile(r"\b(?:mid[- ]level|intermediate)\b")),
]


def level_from_title(title):
    t = title.lower()
    for level, pattern in LEVEL_RULES:
        if pattern.search(t):
            return level
    return None


KAGGLE_TO_LEVEL = {
    "Internship": "intern",
    "Entry level": "entry",
    "Associate": "entry",
    "Mid-Senior level": "mid",
    "Director": "leadership",
    "Executive": "leadership",
}

COMPATIBLE = {
    "intern": {"Internship"},
        "entry": {"Entry level", "Associate"},
    "mid": {"Associate", "Mid-Senior level"},
    "senior": {"Mid-Senior level"},
    "leadership": {"Director", "Executive", "Mid-Senior level"},
}