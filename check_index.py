import chromadb
from transformers import AutoTokenizer

tok = AutoTokenizer.from_pretrained("BAAI/bge-small-en-v1.5")
col = chromadb.PersistentClient(path="data/chroma").get_collection("job_chunks")
print("Chunks:", col.count())

data = col.get(limit=3000, include=["documents", "metadatas"])
lengths = sorted(
    len(tok.encode(d, add_special_tokens=False)) for d in data["documents"]
)
n = len(lengths)
print("Sampled:", n)
print("median:", lengths[n // 2],
      "| 95th:", lengths[int(n * 0.95)],
      "| max:", lengths[-1])
print("chunks over 230 tokens:", sum(x > 230 for x in lengths))
print("Example id:", data["ids"][0])