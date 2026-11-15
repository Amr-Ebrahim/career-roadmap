# rescore_citation.py - run our CitationFaithfulness metric on SAVED answers,
# to check it against check_claims.py before we trust it.
# Usage: python rescore_citation.py evals/baseline_2026-11-15.csv [low|medium]
import csv
import sys

from groq_judge import GroqJudge  # import first: it loads .env before deepeval
from deepeval.test_case import LLMTestCase
from citation_faithfulness import CitationFaithfulnessMetric
from eval_rag import TESTS, THRESHOLD
from rag_by_hand import source_blocks
from retrieval import retrieve

path = sys.argv[1]
reasoning = sys.argv[2] if len(sys.argv) > 2 else "medium"
filters = {t["question"]: t for t in TESTS}

with open(path, encoding="utf-8") as f:
    rows = [r for r in csv.DictReader(f) if r["metric"] == "Faithfulness"]

metric = CitationFaithfulnessMetric(GroqJudge(reasoning=reasoning), threshold=THRESHOLD)
print("Judge:", metric.evaluation_model)

for r in rows:
    t = filters[r["question"]]
    posts = retrieve(t["question"], role_family=t["role_family"], level=t["level"])
    case = LLMTestCase(input=r["question"], actual_output=r["answer"],
                       retrieval_context=source_blocks(posts))

    print(f"\n=== {r['question']}")
    try:
        metric.measure(case)
    except Exception as e:
        print(f"  ERROR {type(e).__name__}: {e}")
        continue

    print(f"  score: {metric.score:.2f}   ({metric.reason})")
    for d in metric.details:
        if d["verdict"] not in ("supported", "no_claim") or d["generalizing"]:
            print(f"  line {d['line']} [{d['verdict']}] {d['text'][:110]}")
            if d["missing"]:
                print(f"        missing: {d['missing']}")
            if d["other_source"]:
                print(f"        found in another source: {d['other_source']}")
            if d["generalizing"]:
                print(f"        generalizing: {d['generalizing']}")