from rag_by_hand import prepare_posts

q = "Which tools do entry-level security analyst jobs ask for?"
posts = prepare_posts(q, role_family="security", level="entry", mode="hybrid+sentences")
print("Sources kept:", len(posts))
for i, p in enumerate(posts, 1):
    print(f"\n[{i}] {p.get('title')} | kept {p.get('kept')} | {p.get('filter_strategy')}")
    print(p["text"])