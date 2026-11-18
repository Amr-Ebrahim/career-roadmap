# preview_boilerplate.py - what would strip_boilerplate() cut from ALL posts? Changes nothing.
# No LLM, no tokens. Takes ~1-3 minutes.
#   python preview_boilerplate.py
# Prints the totals and writes boilerplate_preview.txt with:
#   - how many words are cut, and of which kind (pay, benefits, equal opportunity, ...)
#   - 80 random cut pieces, to read and check that nothing useful is cut
#   - "skills lost": skills found in the full post but no longer in the cleaned text.
#     The safety rule should make this 0; any line here is a bug to fix before re-indexing.
import random
from collections import Counter

import pandas as pd

from boilerplate import strip_boilerplate
from skill_matcher import extract_skills

df = pd.read_parquet("data/processed/jobs_skills.parquet")
df = df[df["n_skills"] > 0]

words_before = words_after = posts_changed = 0
kinds, words_by_kind = Counter(), Counter()
pieces, lost = [], []
for row in df.itertuples():
    text = row.description
    removed = []
    clean = strip_boilerplate(text, removed)
    before, after = len(text.split()), len(clean.split())
    words_before += before
    words_after += after
    if not removed:
        continue
    posts_changed += 1
    for kind, piece in removed:
        kinds[kind] += 1
        words_by_kind[kind] += len(piece.split())
        pieces.append((row.source, kind, piece))
    gone = set(extract_skills(text)) - set(extract_skills(clean))
    if gone:
        lost.append((row.job_id, sorted(gone)))

cut = words_before - words_after
lines = [
    f"Posts: {len(df):,}   changed: {posts_changed:,} ({100 * posts_changed / len(df):.0f}%)",
    f"Words: {words_before:,} -> {words_after:,}   cut: {cut:,} ({100 * cut / words_before:.1f}%)",
    "",
    "Cut pieces by kind (pieces / words):",
]
for kind, n in kinds.most_common():
    lines.append(f"  {kind:<18} {n:>7,} / {words_by_kind[kind]:>9,} words")
lines.append(f"\nSkills lost (should be 0): {len(lost)} posts")
for job_id, skills in lost[:30]:
    lines.append(f"  {job_id}: {', '.join(skills)}")
summary = "\n".join(lines)
print(summary)

random.seed(7)
with open("boilerplate_preview.txt", "w", encoding="utf-8") as f:
    f.write(summary + "\n\n80 random cut pieces:\n")
    for source, kind, piece in random.sample(pieces, min(80, len(pieces))):
        f.write(f"\n[{kind} | {source}] {piece[:300]}\n")
print("\nSaved boilerplate_preview.txt")
