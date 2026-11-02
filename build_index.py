import sys
import time
import pandas as pd
import chromadb
from sentence_transformers import SentenceTransformer
from chunking import post_chunks

DB_PATH = "data/chroma"
COLLECTION = "job_chunks"
BATCH = 256


def text_or(value, default="unknown"):
    return value if isinstance(value, str) and value.strip() else default


df = pd.read_parquet("data/processed/jobs_skills.parquet")
df = df[df["n_skills"] > 0]

if len(sys.argv) > 1:
    df = df.sample(int(sys.argv[1]), random_state=0)
    DB_PATH = "data/chroma_test"
    print("TEST RUN:", len(df), "posts ->", DB_PATH)

client = chromadb.PersistentClient(path=DB_PATH)
collection = client.get_or_create_collection(
    COLLECTION, configuration={"hnsw": {"space": "cosine"}}
)
existing = set(collection.get(include=[])["ids"])
print("Already in index:", len(existing))

ids, docs, metas = [], [], []
for _, row in df.iterrows():
    for i, text, skills in post_chunks(row):
        chunk_id = f"{row['job_id']}_{i}"
        if chunk_id in existing:
            continue
        ids.append(chunk_id)
        docs.append(text)
        metas.append({
            "job_id": row["job_id"],
            "chunk": i,
            "title": row["title"],
            "company": text_or(row["company_name"]),
            "role_family": row["role_family"],
            "level": row["level"],
            "source": row["source"],
            "remote": "unknown" if pd.isna(row["remote_allowed"]) else str(bool(row["remote_allowed"])).lower(),
            "posted_ts": int(row["posted_date"].timestamp()),
            "url": text_or(row["job_posting_url"], ""),
            "skills": ", ".join(skills),
        })

print("New chunks to embed:", len(ids))
if not ids:
    sys.exit()

model = SentenceTransformer("BAAI/bge-small-en-v1.5")
start = time.perf_counter()

for b in range(0, len(ids), BATCH):
    vectors = model.encode(docs[b:b + BATCH], batch_size=32, normalize_embeddings=True)
    collection.add(
        ids=ids[b:b + BATCH],
        documents=docs[b:b + BATCH],
        embeddings=vectors.tolist(),
        metadatas=metas[b:b + BATCH],
    )
    done = min(b + BATCH, len(ids))
    elapsed = time.perf_counter() - start
    left = elapsed / done * (len(ids) - done)
    print(f"{done}/{len(ids)} chunks  ({elapsed / 60:.1f} min done, ~{left / 60:.0f} min left)")

print("Total chunks in index:", collection.count())