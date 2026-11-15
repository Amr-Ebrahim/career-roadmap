# compare_retrieval.py - vector vs hybrid search on the eval questions (no Groq tokens)
from eval_rag import TESTS
from retrieval import retrieve, tokenize

for t in TESTS:
    q = t["question"]
    words = set(tokenize(q))
    print(f"\n=== {q}  ({t['role_family']}, {t['level']})")
    print(f"    keywords: {sorted(words)}")
    for mode in ("vector", "hybrid"):
        posts = retrieve(q, role_family=t["role_family"], level=t["level"], mode=mode)
        print(f"  --- {mode}")
        for i, p in enumerate(posts, start=1):
            hits = sum(w in set(tokenize(p["text"])) for w in words)
            ranks = ""
            if mode == "hybrid":
                ranks = f"  (vector #{p['vector_rank'] or '-'}, bm25 #{p['bm25_rank'] or '-'})"
            print(f"  [{i}] {str(p['title'])[:45]:<45} | {str(p['company'])[:22]:<22} | keywords {hits}/{len(words)}{ranks}")