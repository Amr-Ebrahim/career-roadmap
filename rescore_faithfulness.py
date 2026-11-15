# rescore_faithfulness.py - score the SAME saved answers again with a different judge setting.
# Shows whether low Faithfulness came from the RAG or from the judge.
# Usage: python rescore_faithfulness.py evals/baseline_2026-11-15.csv medium
import csv
import sys

from groq_judge import GroqJudge  # import first: it loads .env before deepeval
from deepeval.metrics import FaithfulnessMetric
from deepeval.test_case import LLMTestCase
from eval_rag import TESTS, THRESHOLD
from rag_by_hand import source_blocks
from retrieval import retrieve

path = sys.argv[1]
reasoning = sys.argv[2] if len(sys.argv) > 2 else "medium"
filters = {t["question"]: t for t in TESTS}

with open(path, encoding="utf-8") as f:
    rows = [r for r in csv.DictReader(f) if r["metric"] == "Faithfulness"]

judge = GroqJudge(reasoning=reasoning)
metric = FaithfulnessMetric(threshold=THRESHOLD, model=judge, async_mode=False,
                            penalize_ambiguous_claims=True)
print("Judge:", judge.get_model_name())

for r in rows:
    t = filters[r["question"]]
    # same question + same filters -> retrieval returns the same 5 posts as in the saved run
    posts = retrieve(t["question"], role_family=t["role_family"], level=t["level"])
    case = LLMTestCase(input=r["question"], actual_output=r["answer"],
                       retrieval_context=source_blocks(posts))

    print(f"\n=== {r['question']}")
    try:
        metric.measure(case)
    except Exception as e:
        print(f"  ERROR {type(e).__name__}: {e}")
        continue

    before = f"{float(r['score']):.2f}" if r["score"] else "-"
    print(f"  before: {before}   now: {metric.score:.2f}   ({len(metric.claims)} claims)")
    # every claim the judge did NOT accept, so we can compare with check_claims.py
    for claim, v in zip(metric.claims, metric.verdicts):
        if str(v.verdict).lower() != "yes":
            print(f"  [{v.verdict}] {claim}")
            if v.reason:
                print(f"        why: {v.reason}")