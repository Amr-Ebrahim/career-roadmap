import pandas as pd

from boilerplate import strip_boilerplate
from chunking import chunk_text, post_chunks

df = pd.read_parquet("data/processed/jobs_skills.parquet")
df = df[df["n_skills"] > 0].sample(500, random_state=0)

total, kept_total, posts_without_chunks = 0, 0, 0
dropped_examples = []

for _, row in df.iterrows():
    # Same text that post_chunks() chunks, so the indexes line up.
    all_pieces = chunk_text(strip_boilerplate(row["description"]))
    kept = post_chunks(row)
    total += len(all_pieces)
    kept_total += len(kept)
    if not kept:
        posts_without_chunks += 1
    kept_ids = {i for i, _, _ in kept}
    for i, piece in enumerate(all_pieces):
        if i not in kept_ids:
            dropped_examples.append(piece[:100].replace("\n", " "))

print(f"Chunks: {total} total, {kept_total} kept, {total - kept_total} dropped "
      f"({(total - kept_total) / max(total, 1):.0%})")
print(f"Posts left with no chunks: {posts_without_chunks}")
print()
print("Sample of DROPPED chunks (check they're really boilerplate):")
if dropped_examples:
    sample = pd.Series(dropped_examples).sample(
        min(15, len(dropped_examples)), random_state=1
    )
    for text in sample:
        print("  -", text)