import time
import pandas as pd 
from sentence_transformers import SentenceTransformer

start = time.perf_counter()
model = SentenceTransformer("BAAI/bge-small-en-v1.5")
print(f"Model loaded in {time.perf_counter() - start:.1f} s")
print("Vector size:", model.get_embedding_dimension())
print("Max tokens per text:", model.max_seq_length)
print()

sentences = [
    "Machine learning engineer with PyTorch experience",
    "Deep learning developer who builds neural networks",
    "Network administrator managing Cisco routers and switches",
    "Help desk technician supporting Windows users",
    "Senior chef preparing Italian dishes",
]

vectors = model.encode(sentences, normalize_embeddings=True)
print("Shape:", vectors.shape)
print("First 8 numbers of sentence 0:", vectors[0][:8].round(3))
print()

for i, s in enumerate(sentences):
    print(f"{i}: {s}")
print()

sims = vectors @ vectors.T
labels = ["ML eng", "DL dev", "Net admin", "Help desk", "Chef"]
print("Similarity matrix (higher = closer in meaning):")
print(pd.DataFrame(sims, index=labels, columns=labels).round(2))