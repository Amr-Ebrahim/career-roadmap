from transformers import AutoTokenizer
from skill_matcher import extract_skills

TOKENIZER = AutoTokenizer.from_pretrained("BAAI/bge-small-en-v1.5")
CHUNK_TOKENS = 300
OVERLAP = 50


def chunk_text(text, size=CHUNK_TOKENS, overlap=OVERLAP):
    offsets = TOKENIZER(text, add_special_tokens=False,
                        return_offsets_mapping=True)["offset_mapping"]
    if len(offsets) <= size:
        return [text]

    chunks = []
    step = size - overlap
    for start in range(0, len(offsets), step):
        end = min(start + size, len(offsets))
        chunks.append(text[offsets[start][0]:offsets[end - 1][1]])
        if end == len(offsets):
            break
    return chunks


def make_header(row):
    return f"{row['title']} | {row['role_family']} | {row['level']}\n"


def post_chunks(row):
    header = make_header(row)
    kept = []
    for i, piece in enumerate(chunk_text(row["description"])):
        skills = extract_skills(piece)
        if skills:
            kept.append((i, header + piece, skills))
    return kept