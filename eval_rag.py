# eval_rag.py - score the RAG's answers with DeepEval (judge = Groq, free)
#   python eval_rag.py baseline     -> hand-built RAG, vector search
#   python eval_rag.py langchain    -> LangChain RAG, vector search
#   python eval_rag.py hybrid       -> hand-built RAG, hybrid search (BM25 + vector)
#   python eval_rag.py hybrid 2     -> test run: first 2 questions only
# Results: evals/<run>_<date>.csv  (test runs: evals/test-<run>_<date>.csv)
# Each row also saves the exact numbered sources the answer was written from,
# so the answer can be re-checked later, even after the data has changed.
import csv
import json
import os
import sys
import time
from datetime import date

from groq_judge import GroqJudge  # import first: it loads .env before deepeval
from deepeval.metrics import AnswerRelevancyMetric, ContextualRelevancyMetric
from deepeval.test_case import LLMTestCase
from citation_faithfulness import CitationFaithfulnessMetric

THRESHOLD = 0.7  # a score below this counts as FAIL

# Same questions every run, so scores can be compared later.
# The last two use exact tool/certification names (where keyword search should help).
TESTS = [
    {"question": "What skills do I need to get an entry-level cloud engineer job?",
     "role_family": "devops_cloud", "level": "entry"},
    {"question": "What do entry-level help desk jobs require?",
     "role_family": "networking_it", "level": "entry"},
    {"question": "Which tools do entry-level security analyst jobs ask for?",
     "role_family": "security", "level": "entry"},
    {"question": "What skills do entry-level backend developer jobs ask for?",
     "role_family": "backend", "level": "entry"},
    {"question": "Which certifications do entry-level IT support jobs mention?",
     "role_family": "networking_it", "level": "entry"},
    {"question": "Which entry-level cloud jobs ask for Terraform or Kubernetes?",
     "role_family": "devops_cloud", "level": "entry"},
    {"question": "Do entry-level help desk jobs ask for CompTIA A+ or ITIL?",
     "role_family": "networking_it", "level": "entry"},
]

# run name -> (which RAG code, which search mode)
RUNS = {
    "baseline": ("by_hand", "vector"),
    "langchain": ("langchain", "vector"),
    "hybrid": ("by_hand", "hybrid"),
}


def load_rag(code):
    # import only the version we need (LangChain is slow to import)
    if code == "langchain":
        from rag_langchain import rag_answer
    else:
        from rag_by_hand import rag_answer
    return rag_answer


def make_metrics():
    # async_mode=False: one judge call at a time, gentle on Groq's free limits
    return [
        # our own metric: checks each answer line against the raw cited sources
        CitationFaithfulnessMetric(GroqJudge(reasoning="medium"), threshold=THRESHOLD),
        AnswerRelevancyMetric(threshold=THRESHOLD, model=GroqJudge(), async_mode=False),
        ContextualRelevancyMetric(threshold=THRESHOLD, model=GroqJudge(), async_mode=False),
    ]


def main():
    args = sys.argv[1:]
    run = args[0] if args else "baseline"
    if run not in RUNS:
        sys.exit(f"Unknown run '{run}'. Choose one of: {', '.join(RUNS)}")
    tests, label = TESTS, run
    if len(args) > 1:
        tests, label = TESTS[: int(args[1])], f"test-{run}"

    code, mode = RUNS[run]
    rag_answer = load_rag(code)
    metrics = make_metrics()
    rows = []
    print(f"Run: {run}  (RAG: {code}, search: {mode}, questions: {len(tests)})")

    for n, t in enumerate(tests, start=1):
        print(f"\n=== [{n}/{len(tests)}] {t['question']}  ({t['role_family']}, {t['level']})")
        start = time.time()

        result = rag_answer(t["question"], t["role_family"], t["level"], mode=mode)
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
                "run": run, "question": t["question"], "metric": name, "score": score,
                "status": status, "reason": reason, "answer": result["answer"],
                "sources": json.dumps(result["sources"], ensure_ascii=False),
            })
        print(f"  ({time.time() - start:.0f} s)")

    # save every score, so runs can be compared
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