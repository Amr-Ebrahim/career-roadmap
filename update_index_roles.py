# update_index_roles.py - copy the new role_family into the Chroma metadata (no re-embedding)
import pandas as pd
import chromadb

jobs = pd.read_parquet("data/processed/jobs_skills.parquet")
new_family = dict(zip(jobs["job_id"], jobs["role_family"]))

collection = chromadb.PersistentClient(path="data/chroma").get_collection("job_chunks")
data = collection.get(include=["metadatas"])

ids, metas = [], []
for chunk_id, meta in zip(data["ids"], data["metadatas"]):
    family = new_family.get(meta["job_id"])
    if family and family != meta["role_family"]:
        ids.append(chunk_id)
        metas.append({**meta, "role_family": family})

print("Chunks with a changed role family:", len(ids))
for b in range(0, len(ids), 500):
    collection.update(ids=ids[b:b + 500], metadatas=metas[b:b + 500])
print("Updated.")