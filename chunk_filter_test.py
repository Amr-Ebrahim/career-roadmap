import pandas as pd
from chunking import chunk_text, post_chunks

df = pd.read_parquet("data/processed/jobs_skills.parquet")
df = df[df["n_skills"] > 0].sample(500, random_state=0)

total, kept_total, posts_without_chunks = 0, 0, 0
dropped_examples = []

for _, row in df.iterrows():
    all_pieces = chunk_text(row["description"])
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
      f"({(total - kept_total) / total:.0%})")
print(f"Posts left with no chunks: {posts_without_chunks}")
print(f"New time estimate: ~{47 * kept_total / total:.0f} minutes")
print()
print("Sample of DROPPED chunks (check they're really boilerplate):")
for text in pd.Series(dropped_examples).sample(15, random_state=1):
    print("  -", text)