# sync_index.py - make the Chroma metadata match jobs_skills.parquet (no re-embedding):
#   1. update role_family and level where they changed
#   2. delete chunks of posts that are no longer in the data
import chromadb
import pandas as pd

jobs = pd.read_parquet("data/processed/jobs_skills.parquet", columns=["job_id", "role_family", "level"])
current = jobs.set_index("job_id")[["role_family", "level"]].to_dict("index")

collection = chromadb.PersistentClient(path="data/chroma").get_collection("job_chunks")
data = collection.get(include=["metadatas"])

update_ids, update_metas, delete_ids = [], [], []
for chunk_id, meta in zip(data["ids"], data["metadatas"]):
    post = current.get(meta["job_id"])
    if post is None:
        delete_ids.append(chunk_id)
    elif post["role_family"] != meta["role_family"] or post["level"] != meta["level"]:
        update_ids.append(chunk_id)
        update_metas.append({**meta, "role_family": post["role_family"], "level": post["level"]})

print("Chunks in index:", len(data["ids"]))
print("Chunks to update:", len(update_ids))
print("Chunks to delete (post no longer in the data):", len(delete_ids))

for b in range(0, len(update_ids), 500):
    collection.update(ids=update_ids[b:b + 500], metadatas=update_metas[b:b + 500])
for b in range(0, len(delete_ids), 500):
    collection.delete(ids=delete_ids[b:b + 500])
print("Chunks in index now:", collection.count())