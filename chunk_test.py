import time
import pandas as pd
from sentence_transformers import SentenceTransformer
from chunking import chunk_text, make_header

df = pd.read_parquet("data/processed/jobs_skills.parquet")
df = df[df["n_skills"] > 0]
sample = df.sample(200, random_state=0)

chunks = []
for _, row in sample.iterrows():
    header = make_header(row)
    for piece in chunk_text(row["description"]):
        chunks.append(header + piece)

per_post = len(chunks) / len(sample)
print(f"{len(sample)} posts -> {len(chunks)} chunks ({per_post:.1f} per post)")
print()

example = sample.iloc[0]
pieces = chunk_text(example["description"])
print("Example post:", example["title"], f"({len(pieces)} chunks)")
for i, p in enumerate(pieces):
    start = p[:70].replace("\n", " ")
    end = p[-70:].replace("\n", " ")
    print(f"--- chunk {i}: starts '{start}'")
    print(f"              ends   '{end}'")
print()

model = SentenceTransformer("BAAI/bge-small-en-v1.5")
start_time = time.perf_counter()
vectors = model.encode(chunks, batch_size=32, normalize_embeddings=True, show_progress_bar=True)
secs = time.perf_counter() - start_time
rate = len(chunks) / secs

print(f"Embedded {len(chunks)} chunks in {secs:.1f} s ({rate:.0f} chunks/s)")
total_chunks = per_post * len(df)
print(f"Estimate for all {len(df)} posts: ~{total_chunks:.0f} chunks, ~{total_chunks / rate / 60:.0f} minutes")