import os
import re
import time

import chromadb
import numpy as np
from sentence_transformers import SentenceTransformer
from sklearn.feature_extraction.text import ENGLISH_STOP_WORDS, CountVectorizer


DB_PATH = "data/chroma"
QUERY_PREFIX = "Represent this sentence for searching relevant passages: "

_model = SentenceTransformer("BAAI/bge-small-en-v1.5")
_collection = chromadb.PersistentClient(path=DB_PATH).get_collection(
    "job_chunks"
)

K1, B = 1.5, 0.75

EXTRA_STOP = {
    "job", "jobs", "entry", "level",
    "need", "ask", "asks", "mention", "mentions",
}

STOP = ENGLISH_STOP_WORDS | EXTRA_STOP

_bm25 = None


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
    """Missing or invalid dates do not get a freshness bonus."""
    if half_life_days <= 0:
        raise ValueError("half_life_days must be positive")

    try:
        posted_ts = float(posted_ts)
    except (TypeError, ValueError):
        return 0.0

    if not np.isfinite(posted_ts) or posted_ts <= 0:
        return 0.0

    age_days = max(0.0, (time.time() - posted_ts) / 86400)
    return 0.5 ** (age_days / half_life_days)


def tokenize(text):
    """Preserve technical terms such as c++, a+, and node.js."""
    tokens = [
        token.rstrip(".")
        for token in re.findall(
            r"[a-z0-9][a-z0-9+#.]*",
            text.lower(),
        )
    ]

    return [
        token
        for token in tokens
        if token and token not in STOP
    ]


def _body(document):
    """
    Remove the header created by chunking.make_header().

    Unlike an unconditional split, do not remove the first line of a
    document that does not appear to contain our header.
    """
    first, separator, rest = document.partition("\n")

    if separator and first.count(" | ") >= 2:
        return rest.strip()

    return document.strip()


def _candidate(chunk_id, document, metadata):
    if not document:
        return None

    metadata = dict(metadata or {})

    if metadata.get("job_id") is None:
        raise ValueError(
            f"Chunk {chunk_id!r} is missing job_id metadata"
        )

    return {
        **metadata,
        "chunk_id": chunk_id,
        "text": _body(document),
        "freshness": freshness(metadata.get("posted_ts")),
    }


def _cosine_similarity(query_vector, embedding):
    """
    Calculate cosine similarity directly, rather than assuming that
    Chroma's returned distance is cosine distance.
    """
    embedding = np.asarray(embedding, dtype=np.float64)
    query_vector = np.asarray(query_vector, dtype=np.float64)

    denominator = (
        np.linalg.norm(query_vector) * np.linalg.norm(embedding)
    )

    if denominator == 0:
        return 0.0

    return float(
        np.clip(
            np.dot(query_vector, embedding) / denominator,
            -1.0,
            1.0,
        )
    )


# ---------------- vector search ----------------

def _vector_chunks(
    question,
    role_family,
    level,
    fetch,
    recency_weight,
):
    count = _collection.count()

    if count == 0:
        return []

    vector = _model.encode(
        QUERY_PREFIX + question,
        normalize_embeddings=True,
    )

    query_args = {
        "query_embeddings": [vector.tolist()],
        "n_results": min(fetch, count),
        "include": [
            "documents",
            "metadatas",
            "distances",
            "embeddings",
        ],
    }

    where = build_filter(role_family, level)

    if where is not None:
        query_args["where"] = where

    result = _collection.query(**query_args)

    candidates = []

    for chunk_id, document, metadata, distance, embedding in zip(
        result["ids"][0],
        result["documents"][0],
        result["metadatas"][0],
        result["distances"][0],
        result["embeddings"][0],
    ):
        candidate = _candidate(chunk_id, document, metadata)

        if candidate is None:
            continue

        similarity = _cosine_similarity(vector, embedding)

        candidate.update({
            "similarity": similarity,
            "distance": float(distance),
            "bm25": None,
            "score": (
                similarity
                + recency_weight * candidate["freshness"]
            ),
        })

        candidates.append(candidate)

    return sorted(
        candidates,
        key=lambda candidate: candidate["score"],
        reverse=True,
    )


# ---------------- BM25 keyword search ----------------

def reset_bm25():
    """
    Call this if you update the collection inside a running process.
    Otherwise, restarting the process rebuilds the in-memory index.
    """
    global _bm25
    _bm25 = None


def _load_bm25():
    global _bm25

    if _bm25 is not None:
        return _bm25

    start = time.time()

    data = _collection.get(
        include=["documents", "metadatas"]
    )

    records = [
        (chunk_id, document, metadata or {})
        for chunk_id, document, metadata in zip(
            data["ids"],
            data["documents"],
            data["metadatas"],
        )
        if document
    ]

    if not records:
        _bm25 = {
            "ids": [],
            "docs": [],
            "metas": [],
            "vocab": {},
            "family": np.array([], dtype=object),
            "level": np.array([], dtype=object),
        }
        return _bm25

    ids, documents, metadatas = zip(*records)

    # Search the evidence body, not the repeated role/title header.
    bodies = [_body(document) for document in documents]

    vectorizer = CountVectorizer(
        tokenizer=tokenize,
        lowercase=False,
        token_pattern=None,
    )

    try:
        tf = vectorizer.fit_transform(bodies).tocsc()
    except ValueError as exc:
        if "empty vocabulary" not in str(exc).lower():
            raise

        _bm25 = {
            "ids": list(ids),
            "docs": list(documents),
            "metas": list(metadatas),
            "vocab": {},
            "family": np.array(
                [m.get("role_family") for m in metadatas],
                dtype=object,
            ),
            "level": np.array(
                [m.get("level") for m in metadatas],
                dtype=object,
            ),
        }
        return _bm25

    n_docs = tf.shape[0]
    doc_len = np.asarray(tf.sum(axis=1)).ravel()
    average_len = max(float(doc_len.mean()), 1.0)

    # One nonzero entry per document containing the vocabulary term.
    document_frequency = np.diff(tf.indptr)

    _bm25 = {
        "ids": list(ids),
        "docs": list(documents),
        "metas": list(metadatas),
        "vocab": vectorizer.vocabulary_,
        "tf": tf,
        "idf": np.log(
            (n_docs - document_frequency + 0.5)
            / (document_frequency + 0.5)
            + 1
        ),
        "norm": K1 * (
            1 - B + B * doc_len / average_len
        ),
        "family": np.array(
            [m.get("role_family") for m in metadatas],
            dtype=object,
        ),
        "level": np.array(
            [m.get("level") for m in metadatas],
            dtype=object,
        ),
    }

    print(
        f"(BM25 index: {n_docs} chunks, "
        f"{len(_bm25['vocab'])} words, "
        f"{time.time() - start:.1f} s)"
    )

    return _bm25


def bm25_scores(question):
    index = _load_bm25()
    scores = np.zeros(len(index["ids"]), dtype=np.float64)

    if not index["vocab"]:
        return scores

    for word in set(tokenize(question)):
        column = index["vocab"].get(word)

        if column is None:
            continue

        start = index["tf"].indptr[column]
        end = index["tf"].indptr[column + 1]

        rows = index["tf"].indices[start:end]
        frequencies = index["tf"].data[start:end]

        scores[rows] += (
            index["idf"][column]
            * frequencies
            * (K1 + 1)
            / (frequencies + index["norm"][rows])
        )

    return scores


def _bm25_chunks(question, role_family, level, fetch):
    index = _load_bm25()
    scores = bm25_scores(question)

    if len(scores) == 0:
        return []

    allowed = np.ones(len(scores), dtype=bool)

    if role_family:
        allowed &= index["family"] == role_family

    if level:
        allowed &= index["level"] == level

    eligible = np.flatnonzero(allowed & (scores > 0))

    ordered = eligible[
        np.argsort(-scores[eligible], kind="stable")
    ][:fetch]

    candidates = []

    for position in ordered:
        candidate = _candidate(
            index["ids"][position],
            index["docs"][position],
            index["metas"][position],
        )

        if candidate is None:
            continue

        candidate.update({
            "similarity": None,
            "bm25": float(scores[position]),
            "score": float(scores[position]),
        })

        candidates.append(candidate)

    return candidates


# ---------------- hybrid search ----------------

def rrf(rankings, k=60):
    """Reciprocal rank fusion over chunk IDs, not job IDs."""
    if k < 0:
        raise ValueError("k must not be negative")

    fused = {}

    for ranking in rankings:
        seen = set()

        for rank, chunk_id in enumerate(ranking, start=1):
            if chunk_id in seen:
                continue

            seen.add(chunk_id)

            fused[chunk_id] = (
                fused.get(chunk_id, 0.0)
                + 1.0 / (k + rank)
            )

    return fused


def _select_posts(candidates, n_posts):
    """
    Select one chunk per job AFTER ranking the chunks.

    This keeps the original public behavior: up to n_posts jobs,
    each with one selected evidence chunk.
    """
    selected = []
    seen_jobs = set()

    for candidate in candidates:
        job_id = candidate["job_id"]

        if job_id in seen_jobs:
            continue

        seen_jobs.add(job_id)
        selected.append(candidate)

        if len(selected) >= n_posts:
            break

    return selected


def retrieve(
    question,
    role_family=None,
    level=None,
    n_posts=5,
    fetch=60,
    recency_weight=0.02,
    mode="vector",
):
    """
    Compatible with the original retrieve() interface.

    Optional environment variables:
      RAG_N_POSTS=3
      RAG_RECENCY_WEIGHT=0

    hybrid+sentences still retrieves hybrid chunks. Your existing
    RAG/sentence_filter code must perform the sentence filtering.
    """
    if mode not in {"vector", "hybrid", "hybrid+sentences"}:
        raise ValueError(
            "mode must be vector, hybrid, or hybrid+sentences"
        )

    n_posts = int(os.getenv("RAG_N_POSTS", str(n_posts)))
    recency_weight = float(
        os.getenv(
            "RAG_RECENCY_WEIGHT",
            str(recency_weight),
        )
    )

    if n_posts <= 0:
        raise ValueError("n_posts must be positive")

    if fetch <= 0:
        raise ValueError("fetch must be positive")

    fetch = max(fetch, n_posts)

    vector_chunks = _vector_chunks(
        question,
        role_family,
        level,
        fetch,
        recency_weight,
    )

    if mode == "vector":
        return _select_posts(vector_chunks, n_posts)

    keyword_chunks = _bm25_chunks(
        question,
        role_family,
        level,
        fetch,
    )

    vector_rank = {
        candidate["chunk_id"]: rank
        for rank, candidate in enumerate(
            vector_chunks,
            start=1,
        )
    }

    keyword_rank = {
        candidate["chunk_id"]: rank
        for rank, candidate in enumerate(
            keyword_chunks,
            start=1,
        )
    }

    fused = rrf([
        list(vector_rank),
        list(keyword_rank),
    ])

    by_vector = {
        candidate["chunk_id"]: candidate
        for candidate in vector_chunks
    }

    by_keyword = {
        candidate["chunk_id"]: candidate
        for candidate in keyword_chunks
    }

    ranked = []

    for chunk_id, score in sorted(
        fused.items(),
        key=lambda item: item[1],
        reverse=True,
    ):
        # The ID identifies the SAME chunk in both rankings.
        # We no longer choose between different chunks from one job.
        candidate = dict(
            by_vector[chunk_id]
            if chunk_id in by_vector
            else by_keyword[chunk_id]
        )

        candidate.update({
            "score": score,
            "vector_rank": vector_rank.get(chunk_id),
            "bm25_rank": keyword_rank.get(chunk_id),
            "similarity": (
                by_vector[chunk_id]["similarity"]
                if chunk_id in by_vector
                else None
            ),
            "bm25": (
                by_keyword[chunk_id]["bm25"]
                if chunk_id in by_keyword
                else None
            ),
        })

        ranked.append(candidate)

    return _select_posts(ranked, n_posts)