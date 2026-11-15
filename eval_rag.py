# eval_rag.py - score the RAG's answers with DeepEval (judge = Groq, free)
# Full run:  python eval_rag.py            -> evals/baseline_<date>.csv
# Named run: python eval_rag.py langchain  -> evals/langchain_<date>.csv
# Test run:  python eval_rag.py 1          -> first question only, evals/test_<date>.csv
import csv
import os
import sys
import time
from datetime import date

from groq_judge import GroqJudge  # import first: it loads .env before deepeval
from deepeval.metrics import (
    AnswerRelevancyMetric,
    ContextualRelevancyMetric,
    FaithfulnessMetric,
)
from deepeval.test_case import LLMTestCase
from rag_by_hand import rag_answer

THRESHOLD = 0.7  # a score below this counts as FAIL

# Same questions every run, so scores can be compared later
TESTS = [
    {"question": "What skills do I need to get an entry-level cloud engineer job?",
     "role_family": "devops_cloud", "level": "entry"},
    {"question": "What do entry-level help desk jobs require?",
     "role_family": "networking_it", "level": "entry"},
    {"question": "Which tools do entry-level security analyst jobs ask for?",
     "role_family": "security", "level": "entry"},
    {"question": "What skills do entry-level backend developer jobs ask for?",
     "role_family": "software", "level": "entry"},
    {"question": "Which certifications do entry-level IT support jobs mention?",
     "role_family": "networking_it", "level": "entry"},
]

def make_metrics(judge):
    # async_mode=False: one judge call at a time, gentle on Groq's free limits
    # penalize_ambiguous_claims=True: a claim the sources don't back up counts
    # against the score (by default only a direct contradiction does)
    return [
        FaithfulnessMetric(threshold=THRESHOLD, model=judge, async_mode=False,
                           penalize_ambiguous_claims=True),
        AnswerRelevancyMetric(threshold=THRESHOLD, model=judge, async_mode=False),
        ContextualRelevancyMetric(threshold=THRESHOLD, model=judge, async_mode=False),
    ]


def main():
    args = sys.argv[1:]
    if args and args[0].isdigit():
        tests, label = TESTS[: int(args[0])], "test"
    else:
        tests, label = TESTS, (args[0] if args else "baseline")

    metrics = make_metrics(GroqJudge())
    rows = []

    for n, t in enumerate(tests, start=1):
        print(f"\n=== [{n}/{len(tests)}] {t['question']}  ({t['role_family']}, {t['level']})")
        start = time.time()

        result = rag_answer(t["question"], t["role_family"], t["level"])
        case = LLMTestCase(
            input=t["question"],
            actual_output=result["answer"],
            retrieval_context=result["sources"],
        )

        for metric in metrics:
            name = metric.__class__.__name__.replace("Metric", "")
            try:
                metric.measure(case)
                score, reason = metric.score, metric.reason
                status = "PASS" if metric.is_successful() else "FAIL"
            except Exception as e:  # one broken judge reply shouldn't stop the run
                score, reason, status = None, f"{type(e).__name__}: {e}", "ERROR"

            shown = "-" if score is None else f"{score:.2f}"
            print(f"  {name:<20} {shown:>5}  {status}")
            print(f"      {str(reason)[:300]}")
            rows.append({
                "question": t["question"], "metric": name, "score": score,
                "status": status, "reason": reason, "answer": result["answer"],
            })
        print(f"  ({time.time() - start:.0f} s)")

    # save every score, so later runs (LangChain, hybrid) can be compared
    os.makedirs("evals", exist_ok=True)
    path = f"evals/{label}_{date.today()}.csv"
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    print("\n=== AVERAGES ===")
    for name in dict.fromkeys(r["metric"] for r in rows):
        scores = [r["score"] for r in rows if r["metric"] == name and r["score"] is not None]
        passed = sum(r["status"] == "PASS" for r in rows if r["metric"] == name)
        avg = f"{sum(scores) / len(scores):.2f}" if scores else "-"
        print(f"  {name:<20} {avg:>5}  ({passed}/{len(tests)} passed)")
    print(f"\nSaved: {path}")


if __name__ == "__main__":
    main()