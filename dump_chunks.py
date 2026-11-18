# dump_chunks.py - writes random chunks from the search index to a text file, to see what
# boilerplate (benefits, "about us", equal-opportunity text...) is inside them. No LLM, no tokens.
#   python dump_chunks.py            -> 40 random chunks
#   python dump_chunks.py 80         -> 80 random chunks
# Result: chunk_sample.txt
import random
import sys

import chromadb

N = int(sys.argv[1]) if len(sys.argv) > 1 else 40
random.seed(7)  # same sample every time, so a before/after comparison uses the same chunks

col = chromadb.PersistentClient(path="data/chroma").get_collection("job_chunks")
ids = col.get(include=[])["ids"]
pick = random.sample(ids, min(N, len(ids)))
got = col.get(ids=pick, include=["documents", "metadatas"])

with open("chunk_sample.txt", "w", encoding="utf-8") as f:
    f.write(f"{len(pick)} random chunks of {len(ids):,}\n")
    for i, (cid, doc, meta) in enumerate(zip(got["ids"], got["documents"], got["metadatas"]), start=1):
        f.write(f"\n===== [{i}] {cid} | {meta.get('source')} | {meta.get('role_family')} | "
                f"{meta.get('level')} | {len(doc.split())} words\n{doc}\n")
print(f"Saved {len(pick)} chunks to chunk_sample.txt")
