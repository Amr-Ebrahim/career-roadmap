import re
import time

import chromadb
import numpy as np
from sentence_transformers import SentenceTransformer
from sklearn.feature_extraction.text import ENGLISH_STOP_WORDS, CountVectorizer

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


# ---------------- vector search (same as before) ----------------
def _vector_posts(question, role_family, level, fetch, recency_weight):
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
    return sorted(best.values(), key=lambda r: r["score"], reverse=True)


# ---------------- BM25 keyword search ----------------
K1, B = 1.5, 0.75  # standard BM25 settings
EXTRA_STOP = {"job", "jobs", "entry", "level", "need", "ask", "asks", "mention", "mentions"}
STOP = ENGLISH_STOP_WORDS | EXTRA_STOP
_bm25 = None  # built on first use, then kept in memory


def tokenize(text):
    # keeps tech words whole: c#, c++, a+, network+, node.js
    tokens = [t.rstrip(".") for t in re.findall(r"[a-z0-9][a-z0-9+#.]*", text.lower())]
    return [t for t in tokens if t and t not in STOP]


def _load_bm25():
    global _bm25
    if _bm25 is None:
        start = time.time()
        data = _collection.get(include=["documents", "metadatas"])
        vectorizer = CountVectorizer(tokenizer=tokenize, lowercase=False, token_pattern=None)
        tf = vectorizer.fit_transform(data["documents"]).tocsc()  # rows = chunks, columns = words
        n_docs = tf.shape[0]
        doc_len = np.asarray(tf.sum(axis=1)).ravel()
        df = np.diff(tf.indptr)  # in how many chunks each word appears
        _bm25 = {
            "vocab": vectorizer.vocabulary_,
            "tf": tf,
            "idf": np.log((n_docs - df + 0.5) / (df + 0.5) + 1),
            "norm": K1 * (1 - B + B * doc_len / doc_len.mean()),
            "docs": data["documents"],
            "metas": data["metadatas"],
            "family": np.array([m.get("role_family") for m in data["metadatas"]]),
            "level": np.array([m.get("level") for m in data["metadatas"]]),
        }
        print(f"(BM25 index: {n_docs} chunks, {len(_bm25['vocab'])} words, {time.time() - start:.1f} s)")
    return _bm25


def bm25_scores(question):
    b = _load_bm25()
    scores = np.zeros(b["tf"].shape[0])
    for word in set(tokenize(question)):
        j = b["vocab"].get(word)
        if j is None:
            continue
        start, end = b["tf"].indptr[j], b["tf"].indptr[j + 1]
        rows = b["tf"].indices[start:end]  # chunks that contain this word
        f = b["tf"].data[start:end]        # how many times it appears in each
        scores[rows] += b["idf"][j] * f * (K1 + 1) / (f + b["norm"][rows])
    return scores


def _bm25_posts(question, role_family, level, fetch):
    b = _load_bm25()
    scores = bm25_scores(question)
    allowed = np.ones(len(scores), dtype=bool)  # same filters as the vector search
    if role_family:
        allowed &= b["family"] == role_family
    if level:
        allowed &= b["level"] == level
    scores = np.where(allowed, scores, 0)
    top = [i for i in np.argsort(-scores)[:fetch] if scores[i] > 0]

    best = {}
    for i in top:
        meta = b["metas"][i]
        if meta["job_id"] in best:
            continue
        best[meta["job_id"]] = {
            **meta,
            "text": b["docs"][i].split("\n", 1)[1],
            "bm25": float(scores[i]),
            "freshness": freshness(meta["posted_ts"]),
        }
    return list(best.values())  # already in BM25 order


# ---------------- hybrid: merge both rankings ----------------
def rrf(rankings, k=60):
    # Reciprocal Rank Fusion: each list gives 1/(k + rank) points
    fused = {}
    for ranking in rankings:
        for rank, job_id in enumerate(ranking, start=1):
            fused[job_id] = fused.get(job_id, 0) + 1 / (k + rank)
    return fused


def retrieve(question, role_family=None, level=None, n_posts=5, fetch=60,
             recency_weight=0.02, mode="vector"):
    vector_posts = _vector_posts(question, role_family, level, fetch, recency_weight)
    if mode == "vector":
        return vector_posts[:n_posts]

    keyword_posts = _bm25_posts(question, role_family, level, fetch)
    v_rank = {p["job_id"]: r for r, p in enumerate(vector_posts, start=1)}
    k_rank = {p["job_id"]: r for r, p in enumerate(keyword_posts, start=1)}
    fused = rrf([list(v_rank), list(k_rank)])

    by_id_v = {p["job_id"]: p for p in vector_posts}
    by_id_k = {p["job_id"]: p for p in keyword_posts}
    results = []
    for job_id, score in sorted(fused.items(), key=lambda x: x[1], reverse=True)[:n_posts]:
        # use the chunk from the list where this post ranked better
        in_v, in_k = v_rank.get(job_id, 10**6), k_rank.get(job_id, 10**6)
        post = dict(by_id_v[job_id] if in_v <= in_k else by_id_k[job_id])
        post.update({
            "score": score,
            "vector_rank": v_rank.get(job_id),
            "bm25_rank": k_rank.get(job_id),
            "similarity": by_id_v[job_id]["similarity"] if job_id in by_id_v else None,
            "bm25": by_id_k[job_id]["bm25"] if job_id in by_id_k else None,
        })
        results.append(post)
    return results