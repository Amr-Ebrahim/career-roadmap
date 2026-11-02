import re
from skills_dict import CASE_SENSITIVE, SKILLS

LEFT = r"(?<![\w+#])"
RIGHT = r"(?![\w+#])"


def _compile(aliases, flags):
    return re.compile(LEFT + "(?:" + "|".join(aliases) + ")" + RIGHT, flags)


PATTERNS = [(name, _compile(aliases, re.IGNORECASE)) for name, (cat, aliases) in SKILLS.items()]
PATTERNS += [(name, _compile(aliases, 0)) for name, (cat, aliases) in CASE_SENSITIVE.items()]

CATEGORY = {name: cat for name, (cat, _) in {**SKILLS, **CASE_SENSITIVE}.items()}


def extract_skills(text):
    found = {name for name, pattern in PATTERNS if pattern.search(text)}
    return sorted(found)