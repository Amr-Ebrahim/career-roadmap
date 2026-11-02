import time
import chromadb
from sentence_transformers import SentenceTransformer

DB_PATH = "data/chroma"
QUERY_PREFIX = "Represent this sentence for searching relevant passages: "

_model = SentenceTransformer("BAAI/bge-small-en-v1.5")
_collection = chromadb.PersistentClient(path=DB_PATH).get_collection("job_chunks")


def build_filter(role_family=None, level=None):
    conditions = []
    if role_family:
        conditions.append({"role_family": role_family})
    if level:
        conditions.append({"level": level})
    if not conditions:
        return None
    if len(conditions) == 1:
        return conditions[0]
    return {"$and": conditions}


def freshness(posted_ts, half_life_days=180):
    age_days = max(0, (time.time() - posted_ts) / 86400)
    return 0.5 ** (age_days / half_life_days)

def retrieve(question, role_family=None, level=None, n_posts=5, fetch=60, recency_weight=0.02):
    vector = _model.encode(QUERY_PREFIX + question, normalize_embeddings=True)
    res = _collection.query(
        query_embeddings=[vector.tolist()],
        n_results=fetch,
        where=build_filter(role_family, level),
        include=["documents", "metadatas", "distances"],
    )

    best = {}
    for doc, meta, dist in zip(res["documents"][0], res["metadatas"][0], res["distances"][0]):
        if meta["job_id"] in best:
            continue
        similarity = 1 - dist
        fresh = freshness(meta["posted_ts"])
        best[meta["job_id"]] = {
            **meta,
            "text": doc.split("\n", 1)[1],
            "similarity": similarity,
            "freshness": fresh,
            "score": similarity + recency_weight * fresh,
        }

    ranked = sorted(best.values(), key=lambda r: r["score"], reverse=True)
    return ranked[:n_posts]