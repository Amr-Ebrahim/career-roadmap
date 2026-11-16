# show_source.py - print one saved source from an eval CSV, to check a claim by eye.
# Usage: python show_source.py evals/baseline_2026-11-16.csv backend 2
#        (a word from the question, then the source number)
import csv
import json
import sys

path, word, n = sys.argv[1], sys.argv[2].lower(), int(sys.argv[3])
with open(path, encoding="utf-8") as f:
    row = next(r for r in csv.DictReader(f) if word in r["question"].lower())
print(row["question"], "\n")
print(json.loads(row["sources"])[n - 1])