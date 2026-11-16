# skill_matcher.py - finds the skills from skills_dict.py in a text.
import re

from skills_dict import CASE_SENSITIVE, SKILLS

LEFT = r"(?<![\w+#])"
# A skill ends where the word ends. Also accept a "glued" next word: Kaggle posts lost the
# line breaks between bullet points, so "Postgres" + "Knowledge" became "PostgresKnowledge".
# (?-i:...) turns case-insensitive matching OFF inside, so this part really means:
# a lowercase letter, then a capital letter followed by a lowercase one (a new word started).
# All-caps words like "LANGUAGE" are not split, so "lan" still doesn't match inside them.
RIGHT = r"(?:(?![\w+#])|(?-i:(?<=[a-z])(?=[A-Z][a-z])))"


def _compile(aliases, flags):
    return re.compile(LEFT + "(?:" + "|".join(aliases) + ")" + RIGHT, flags)


PATTERNS = [(name, _compile(aliases, re.IGNORECASE)) for name, (cat, aliases) in SKILLS.items()]
PATTERNS += [(name, _compile(aliases, 0)) for name, (cat, aliases) in CASE_SENSITIVE.items()]

CATEGORY = {name: cat for name, (cat, _) in {**SKILLS, **CASE_SENSITIVE}.items()}


def extract_skills(text):
    found = {name for name, pattern in PATTERNS if pattern.search(text)}
    return sorted(found)