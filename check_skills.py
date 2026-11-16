# check_skills.py - a free, independent check of the judge (no LLM, no tokens).
# For every answer line, the skills dictionary finds the skills it names, then checks
# whether each one is in the post(s) the line cites. Compare with the judge's verdicts.
# Usage: python check_skills.py evals/baseline_2026-11-16.csv
import csv
import json
import re
import sys

from skill_matcher import extract_skills

CITE = re.compile(r"\[(\d+)\]")
path = sys.argv[1]

with open(path, encoding="utf-8") as f:
    rows = list({r["question"]: r for r in csv.DictReader(f)}.values())

total_lines = total_skills = total_missing = total_moved = 0
for r in rows:
    sources = json.loads(r["sources"])
    in_source = [set(extract_skills(s)) for s in sources]  # skills found in each numbered post
    everyone = range(1, len(sources) + 1)
    print(f"\n=== {r['question']}")

    # same line numbers as the judge: non-empty lines, counted from 1
    lines = [l.strip() for l in r["answer"].splitlines() if l.strip()]
    problems = 0
    for i, line in enumerate(lines, start=1):
        named = set(extract_skills(line))
        if not named:
            continue
        cited = [n for n in map(int, CITE.findall(line)) if 1 <= n <= len(sources)] or list(everyone)
        found = set().union(*(in_source[n - 1] for n in cited))
        missing = sorted(named - found)
        total_lines += 1
        total_skills += len(named)
        if not missing:
            continue
        problems += 1
        others = [n for n in everyone if n not in cited]
        for skill in missing:
            elsewhere = [n for n in others if skill in in_source[n - 1]]
            if elsewhere:
                total_moved += 1
                print(f"  line {i}: {skill} is not in {cited}, but is in {elsewhere} (wrong citation)")
            else:
                total_missing += 1
                print(f"  line {i}: {skill} is in NONE of the sources (invented?)")
        print(f"          {line[:110]}")
    if not problems:
        print("  all named skills are in the cited posts")

print(f"\nChecked {total_skills} skill mentions in {total_lines} lines: "
      f"{total_missing} in no source, {total_moved} with a wrong citation.")
print("Compare with the judge: every line listed here should be 'partly' or 'unsupported' there.")