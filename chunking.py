import re

from transformers import AutoTokenizer

from boilerplate import strip_boilerplate
from skill_matcher import extract_skills


TOKENIZER = AutoTokenizer.from_pretrained(
    "BAAI/bge-small-en-v1.5"
)

CHUNK_TOKENS = 180
OVERLAP = 40


def _token_count(text):
    return len(
        TOKENIZER.encode(
            text,
            add_special_tokens=False,
        )
    )


def _token_windows(text, size, overlap):
    """
    Fallback for an individual sentence/bullet longer than size.
    Preserve original text using tokenizer character offsets.
    """
    offsets = TOKENIZER(
        text,
        add_special_tokens=False,
        return_offsets_mapping=True,
    )["offset_mapping"]

    if not offsets:
        return []

    if len(offsets) <= size:
        return [text]

    pieces = []
    step = size - overlap

    for start in range(0, len(offsets), step):
        end = min(start + size, len(offsets))

        piece = text[
            offsets[start][0]:offsets[end - 1][1]
        ].strip()

        if piece:
            pieces.append(piece)

        if end == len(offsets):
            break

    return pieces


def _text_units(text, size, overlap):
    """
    Prefer original lines/bullets, then sentence boundaries.

    Sentence splitting is deliberately conservative so terms such
    as node.js are not split at their internal period.
    """
    units = []

    for line in text.splitlines():
        line = line.strip()

        if not line:
            continue

        if _token_count(line) <= size:
            units.append(line)
            continue

        sentences = re.split(
            r"(?<=[.!?])\s+(?=[A-Z0-9])",
            line,
        )

        for sentence in sentences:
            sentence = sentence.strip()

            if not sentence:
                continue

            if _token_count(sentence) <= size:
                units.append(sentence)
            else:
                units.extend(
                    _token_windows(
                        sentence,
                        size,
                        overlap,
                    )
                )

    return units


def _overlap_tail(units, next_unit, size, overlap):
    """
    Keep complete trailing units only.

    Do not cut an ordinary requirement sentence merely to produce
    exactly `overlap` tokens.
    """
    if overlap == 0:
        return []

    tail = []

    for unit in reversed(units):
        proposed = [unit] + tail

        if _token_count("\n".join(proposed)) > overlap:
            break

        if _token_count(
            "\n".join(proposed + [next_unit])
        ) > size:
            break

        tail = proposed

    return tail


def chunk_text(text, size=CHUNK_TOKENS, overlap=OVERLAP):
    if size <= 0:
        raise ValueError("size must be positive")

    if overlap < 0 or overlap >= size:
        raise ValueError(
            "overlap must satisfy 0 <= overlap < size"
        )

    text = text.strip()

    if not text:
        return []

    if _token_count(text) <= size:
        return [text]

    units = _text_units(text, size, overlap)

    chunks = []
    current = []

    for unit in units:
        proposed = current + [unit]

        if (
            current
            and _token_count("\n".join(proposed)) > size
        ):
            chunks.append("\n".join(current))

            current = _overlap_tail(
                current,
                unit,
                size,
                overlap,
            )

        current.append(unit)

    if current:
        chunks.append("\n".join(current))

    return chunks


def make_header(row):
    return (
        f"{row['title']} | "
        f"{row['role_family']} | "
        f"{row['level']}\n"
    )


def post_chunks(row):
    header = make_header(row)

    # Keep your existing boilerplate removal.
    text = strip_boilerplate(row["description"])

    if not text:
        return []

    kept = []

    for index, piece in enumerate(chunk_text(text)):
        skills = extract_skills(piece)

        # Preserve the existing skill-containing-chunk policy.
        # This is NOT a question-specific relevance filter.
        if skills:
            kept.append((
                index,
                header + piece,
                skills,
            ))

    return kept