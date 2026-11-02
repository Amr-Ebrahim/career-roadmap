import sys
import chromadb
from sentence_transformers import SentenceTransformer

DB_PATH = sys.argv[1] if len(sys.argv) > 1 else "data/chroma"
QUERY_PREFIX = "Represent this sentence for searching relevant passages: "

client = chromadb.PersistentClient(path=DB_PATH)
collection = client.get_collection("job_chunks")
model = SentenceTransformer("BAAI/bge-small-en-v1.5")


def search(question, n=5, where=None):
    print(f"QUERY: {question}   FILTER: {where}")
    vector = model.encode(QUERY_PREFIX + question, normalize_embeddings=True)
    res = collection.query(
        query_embeddings=[vector.tolist()],
        n_results=n,
        where=where,
        include=["documents", "metadatas", "distances"],
    )
    for doc, meta, dist in zip(res["documents"][0], res["metadatas"][0], res["distances"][0]):
        print(f"  [{1 - dist:.2f}] {meta['title']} | {meta['role_family']} | {meta['level']} | {meta['source']}")
        body = doc.split("\n", 1)[1][:140].replace("\n", " ")
        print(f"         {body}")
    print()


search("entry level cloud engineer with AWS and Terraform")
search("entry level cloud engineer with AWS and Terraform", where={"level": "entry"})
search("help desk support with Active Directory and Windows",
       where={"$and": [{"role_family": "networking_it"}, {"level": "entry"}]})