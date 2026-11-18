# preview_filter.py - what does the sentence filter send to the LLM for the 7 eval questions?
# Search + filter only: no LLM, no Groq tokens. ~1 minute.
#   python preview_filter.py
# Prints words before -> after per question and writes filter_preview.txt with, for each post,
# the KEPT sentences and the CUT ones, so you can check that nothing important is cut.
from rag_by_hand import encode
from retrieval import retrieve
from sentence_filter import filter_posts, split_sentences

QUESTIONS = [  # the same 7 questions as eval_rag.py
    ("What skills do I need to get an entry-level cloud engineer job?", "devops_cloud"),
    ("What do entry-level help desk jobs require?", "networking_it"),
    ("Which tools do entry-level security analyst jobs ask for?", "security"),
    ("What skills do entry-level backend developer jobs ask for?", "backend"),
    ("Which certifications do entry-level IT support jobs mention?", "networking_it"),
    ("Which entry-level cloud jobs ask for Terraform or Kubernetes?", "devops_cloud"),
    ("Do entry-level help desk jobs ask for CompTIA A+ or ITIL?", "networking_it"),
]

with open("filter_preview.txt", "w", encoding="utf-8") as f:
    for question, family in QUESTIONS:
        posts = retrieve(question, role_family=family, level="entry", mode="hybrid")
        kept = filter_posts(question, posts, encode)
        before = sum(len(p["text"].split()) for p in posts)
        after = sum(len(p["text"].split()) for p in kept)
        print(f"{before:>5} -> {after:>4} words  {question}")
        f.write(f"\n{'=' * 90}\nQ: {question}\n{before} -> {after} words\n")
        for n, (p, k) in enumerate(zip(posts, kept), start=1):
            keep = set(k["text"].split("\n"))
            f.write(f"\n--- [{n}] {p['title']} at {p['company']} (kept {k['kept']} sentences)\n")
            for s in split_sentences(p["text"]):
                f.write(f"  {'KEEP' if s in keep else 'cut '} | {s}\n")
print("\nSaved filter_preview.txt")
