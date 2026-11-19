# sentence_filter.py
#
# Select evidence before answer generation.
# No remote LLM or judge calls.
#
# Focused questions are filtered:
#   - Certification questions: keep certification evidence.
#   - Category questions ("which languages / databases ..."):
#     keep sentences that name a skill of that kind.
#   - Named-skill questions ("... Terraform or Kubernetes?"):
#     keep sentences mentioning those skills.
#
# Broad questions ("what skills do I need ...", "what do ... jobs require?")
# and tools questions are NOT filtered. Their answer is the whole requirements list, so the
# full retrieved chunk is returned unchanged. (Measured on 2026-11-19:
# filtering broad questions cut useful requirements and lowered
# contextual relevancy from 1.00 to 0.43 on the help desk question.)

import re

from skill_matcher import CATEGORY, extract_skills


# These describe roles/topics rather than specific requested evidence.
GENERIC_SKILLS = {
    "cloud",
    "security",
    "networking",
    "backend",
    "frontend",
    "programming",
    "it",
    "it support",
    "help desk",
    "helpdesk",
    "desktop support",
    "technical support",
    "devops",
    "data",
}

CERT_QUESTION = re.compile(
    r"\bcertif",
    re.IGNORECASE,
)

# Category questions: question words -> which skill categories count.
# None means "any technology": every category except the ones below.
CATEGORY_QUESTIONS = [
    (re.compile(r"\b(?:programming\s+)?languages?\b", re.IGNORECASE),
     {"language"}),
    (re.compile(r"\bdatabases?\b", re.IGNORECASE),
     {"database"}),
]
# No rule for "which tools / software / technologies" questions: the skill
# dictionary groups skills by field (security, cloud, ...), not by kind, so
# it cannot tell a tool (QRadar) from an activity (incident response).
# Tested 2026-11-19: such a rule kept mostly activities. These questions
# are therefore treated like broad questions and not filtered.
NOT_A_TECHNOLOGY = {"certification", "practice"}

CERT_EVIDENCE = re.compile(
    r"\bcertif"
    r"|\bcomptia\b"
    r"|\bcomp\s+tia\b"
    r"|\bmcitp\b"
    r"|\bmcse\b"
    r"|\bmcp\b"
    r"|\bccna\b"
    r"|\bccent\b"
    r"|\bcct\b"
    r"|\bacit\b"
    r"|\bacmt\b"
    r"|\bitil\b"
    r"|\b(?:a|network|security)\+",
    re.IGNORECASE,
)

# These generic benefit lines do not identify requested credentials.
GENERIC_CERT_BENEFIT = re.compile(
    r"^(?:paid\s+)?training\s*(?:&|and)\s*certifications?[.!]?$",
    re.IGNORECASE,
)

QUALIFIER_HEADING = re.compile(
    r"^(?:"
    r"bonus(?:\s+experience.*)?"
    r"|preferred(?:\s+qualifications)?"
    r"|required(?:\s+qualifications)?"
    r"|minimum\s+qualifications"
    r"|qualifications"
    r"|requirements"
    r"|certifications?"
    r")\s*:?\s*$",
    re.IGNORECASE,
)

# Normal punctuation, newlines, bullets, and glued sentence endings.
# Avoid globally splitting camel-case words: that can damage tech names.
SPLIT = re.compile(
    r"(?<=[.!?;])\s+"
    r"|(?<=[a-z0-9)][.!?])(?=[A-Z][a-z])"
    r"|\n+"
    r"|\s{2,}"          # list items separated by 2+ spaces in scraped posts
    r"|\s*[•●▪]\s*"
)


def split_sentences(text):
    """
    Repair one observed raw-data boundary, then split text.
    This is a targeted heuristic, not a general text repair.
    """
    text = text.replace(
        "MCSAServiceNow",
        "MCSA\nServiceNow",
    )

    parts = [
        part.strip(" \t-*")
        for part in SPLIT.split(text)
    ]

    return [part for part in parts if part]


def _skills(text):
    return set(extract_skills(text))


def _is_heading(text):
    return (
        len(text.split()) <= 10
        and bool(QUALIFIER_HEADING.fullmatch(text))
    )


def _is_certification_evidence(text, skills):
    if _is_heading(text):
        return False

    if GENERIC_CERT_BENEFIT.fullmatch(text):
        return False

    return (
        any(
            CATEGORY.get(skill) == "certification"
            for skill in skills
        )
        or bool(CERT_EVIDENCE.search(text))
    )


def _asked_categories(question):
    """
    Return the set of skill categories a category question asks for,
    "any" for a general tools/technologies question, or None if the
    question is not a category question.
    """
    for pattern, categories in CATEGORY_QUESTIONS:
        if pattern.search(question):
            return "any" if categories is None else categories
    return None


def _is_category_evidence(text, skills, wanted):
    if _is_heading(text):
        return False

    for skill in skills:
        if str(skill).lower() in GENERIC_SKILLS:
            continue
        category = CATEGORY.get(skill)
        if wanted == "any":
            if category is not None and category not in NOT_A_TECHNOLOGY:
                return True
        elif category in wanted:
            return True

    return False


def _include_qualifier_headings(sentences, selected):
    """
    Preserve a directly preceding qualification heading.

    Example:
        Bonus Experience
        CompTIA A+ certification ...
    """
    keep = set(selected)

    for index in selected:
        if index > 0 and _is_heading(sentences[index - 1]):
            keep.add(index - 1)

    return keep


def question_strategy(question):
    """Which filter applies to this question (also used for reporting)."""
    if CERT_QUESTION.search(question):
        return "certification"

    if _asked_categories(question) is not None:
        return "category"

    named = {
        skill
        for skill in _skills(question)
        if str(skill).lower() not in GENERIC_SKILLS
    }
    if named:
        return "named-skills"

    return "none"


def filter_posts(question, posts, encode=None):
    """
    posts: dictionaries returned by retrieve()

    encode is accepted for compatibility with the earlier version
    and is no longer used (broad questions are not filtered).

    Returns copies containing selected evidence.
    Focused modes may return fewer posts, including zero.
    """
    strategy = question_strategy(question)

    # Broad question: keep the full retrieved chunks.
    if strategy == "none":
        return [
            {**post, "kept": "all", "filter_strategy": "none"}
            for post in posts
        ]

    wanted = _asked_categories(question)
    named_skills = {
        skill
        for skill in _skills(question)
        if str(skill).lower() not in GENERIC_SKILLS
    }

    output = []

    for post in posts:
        sentences = split_sentences(post["text"])

        if not sentences:
            continue

        found_skills = [
            _skills(sentence)
            for sentence in sentences
        ]

        if strategy == "certification":
            selected = {
                index
                for index, sentence in enumerate(sentences)
                if _is_certification_evidence(
                    sentence,
                    found_skills[index],
                )
            }

        elif strategy == "category":
            selected = {
                index
                for index, sentence in enumerate(sentences)
                if _is_category_evidence(
                    sentence,
                    found_skills[index],
                    wanted,
                )
            }

        else:  # named-skills
            selected = {
                index
                for index, skills in enumerate(found_skills)
                if (
                    named_skills & skills
                    and not _is_heading(sentences[index])
                )
            }

        # Do not replace missing focused evidence with unrelated text.
        if not selected:
            continue

        keep = _include_qualifier_headings(
            sentences,
            selected,
        )

        text = "\n".join(
            sentences[index]
            for index in sorted(keep)
        )

        output.append({
            **post,
            "text": text,
            "kept": f"{len(keep)}/{len(sentences)}",
            "filter_strategy": strategy,
        })

    return output
