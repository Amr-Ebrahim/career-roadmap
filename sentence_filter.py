# sentence_filter.py
#
# Select evidence before answer generation.
# No remote LLM or judge calls.
#
# Focused questions:
#   - Certification questions: keep certification evidence.
#   - Named-skill questions: keep units mentioning those skills.
#
# Broad questions:
#   - Rank units by embedding similarity.
#   - Keep a small selection, without filling a word budget.
#
# WORD_BUDGET is a soft limit for broad questions.
# Focused evidence is not truncated merely to meet that budget.

import re

import numpy as np

from skill_matcher import CATEGORY, extract_skills


WORD_BUDGET = 110
MAX_BROAD_SENTENCES = 3
SKILL_BONUS = 0.03

# Experimental relative cutoff, not a calibrated relevance threshold.
BROAD_SCORE_MARGIN = 0.08

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
}

CERT_QUESTION = re.compile(
    r"\bcertif",
    re.IGNORECASE,
)

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


def _select_broad(question, sentences, skills, encode):
    eligible = [
        index
        for index, sentence in enumerate(sentences)
        if not _is_heading(sentence)
    ]

    if not eligible:
        return set()

    query = np.asarray(
        encode([question], True)[0],
        dtype=float,
    )

    vectors = np.asarray(
        encode(
            [sentences[index] for index in eligible],
            False,
        ),
        dtype=float,
    )

    scores = vectors @ query

    for position, index in enumerate(eligible):
        scores[position] += (
            SKILL_BONUS * min(len(skills[index]), 3)
        )

    ranked = np.argsort(-scores, kind="stable")
    best_score = float(scores[ranked[0]])

    keep = set()
    words = 0

    for position in ranked:
        position = int(position)
        index = eligible[position]

        if float(scores[position]) < (
            best_score - BROAD_SCORE_MARGIN
        ):
            break

        sentence_words = len(sentences[index].split())

        # Keep the best unit intact, even if it exceeds the budget.
        if keep and words + sentence_words > WORD_BUDGET:
            continue

        keep.add(index)
        words += sentence_words

        if (
            len(keep) >= MAX_BROAD_SENTENCES
            or words >= WORD_BUDGET
        ):
            break

    return keep


def filter_posts(question, posts, encode):
    """
    posts: dictionaries returned by retrieve()

    encode(texts, is_query):
        returns normalized embedding vectors

    Returns copies containing selected evidence.
    Focused mode may return fewer posts, including zero.
    """
    certification_question = bool(
        CERT_QUESTION.search(question)
    )

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

        if certification_question:
            selected = {
                index
                for index, sentence in enumerate(sentences)
                if _is_certification_evidence(
                    sentence,
                    found_skills[index],
                )
            }
            strategy = "certification"

        elif named_skills:
            selected = {
                index
                for index, skills in enumerate(found_skills)
                if (
                    named_skills & skills
                    and not _is_heading(sentences[index])
                )
            }
            strategy = "named-skills"

        else:
            selected = _select_broad(
                question,
                sentences,
                found_skills,
                encode,
            )
            strategy = "semantic"

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