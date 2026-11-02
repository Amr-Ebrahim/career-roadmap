import pandas as pd
from transformers import AutoTokenizer
from skill_matcher import extract_skills

tok = AutoTokenizer.from_pretrained("BAAI/bge-small-en-v1.5")

df = pd.read_parquet("data/processed/jobs_skills.parquet")
df = df[df["n_skills"] > 0].sample(500, random_state=0)

lengths = df["description"].apply(lambda t: len(tok.encode(t, add_special_tokens=False)))
print("Description length in tokens:")
print(lengths.describe(percentiles=[0.25, 0.5, 0.75, 0.9]).round(0).to_string())
print(f"Longer than 512 tokens: {(lengths > 512).mean():.0%}")
print()

kept = []
for text in df["description"]:
    full = set(extract_skills(text))
    if not full:
        continue
    enc = tok(text, add_special_tokens=False, return_offsets_mapping=True)
    offsets = enc["offset_mapping"]
    cut = offsets[509][1] if len(offsets) > 510 else len(text)
    first_part = text[:cut]
    seen = set(extract_skills(first_part))
    kept.append(len(seen & full) / len(full))

print(f"Skills still visible in the first 512 tokens: {sum(kept) / len(kept):.0%}")