# Examples:
#
# Only the certification question, contextual relevance only:
#   python eval_rag.py filtered --questions 5 --metrics context
#
# Previously failing questions, contextual relevance only:
#   python eval_rag.py filtered --questions 3 5 6 7 --metrics context
#
# All questions and all metrics:
#   python eval_rag.py filtered
#
# Original first-N syntax still works:
#   python eval_rag.py hybrid 2
#
# Held-out questions (never used to design the filter):
#   python eval_rag.py hybrid --set heldout --metrics context
#   python eval_rag.py filtered --set heldout --metrics context

import argparse
import csv
import json
import math
import os
import time
from datetime import datetime

from groq_judge import GroqJudge  # Loads .env before DeepEval.

from deepeval.metrics import (
    AnswerRelevancyMetric,
    ContextualRelevancyMetric,
)
from deepeval.test_case import LLMTestCase

from citation_faithfulness import CitationFaithfulnessMetric


THRESHOLD = 0.7

TESTS = [
    {
        "question": (
            "What skills do I need to get an "
            "entry-level cloud engineer job?"
        ),
        "role_family": "devops_cloud",
        "level": "entry",
    },
    {
        "question": "What do entry-level help desk jobs require?",
        "role_family": "networking_it",
        "level": "entry",
    },
    {
        "question": (
            "Which tools do entry-level security analyst jobs ask for?"
        ),
        "role_family": "security",
        "level": "entry",
    },
    {
        "question": (
            "What skills do entry-level backend developer jobs ask for?"
        ),
        "role_family": "backend",
        "level": "entry",
    },
    {
        "question": (
            "Which certifications do entry-level IT support jobs mention?"
        ),
        "role_family": "networking_it",
        "level": "entry",
    },
    {
        "question": (
            "Which entry-level cloud jobs ask for Terraform or Kubernetes?"
        ),
        "role_family": "devops_cloud",
        "level": "entry",
    },
    {
        "question": (
            "Do entry-level help desk jobs ask for CompTIA A+ or ITIL?"
        ),
        "role_family": "networking_it",
        "level": "entry",
    },
]

# Held-out set: written on 2026-11-19 AFTER the filter rules were frozen.
# Same question kinds as TESTS, but different roles and skills.
# Do not change the filter based on these results.
HELDOUT = [
    {
        "question": (
            "Which certifications do entry-level cybersecurity jobs mention?"
        ),
        "role_family": "security",
        "level": "entry",
    },
    {
        "question": (
            "Which programming languages do junior data analyst jobs ask for?"
        ),
        "role_family": "data",
        "level": "entry",
    },
    {
        "question": (
            "Do entry-level DevOps jobs ask for Docker or Ansible?"
        ),
        "role_family": "devops_cloud",
        "level": "entry",
    },
    {
        "question": (
            "What do entry-level backend developer jobs require?"
        ),
        "role_family": "backend",
        "level": "entry",
    },
]

SETS = {"main": TESTS, "heldout": HELDOUT}

RUNS = {
    "baseline": ("by_hand", "vector"),
    "langchain": ("langchain", "vector"),
    "hybrid": ("by_hand", "hybrid"),
    "filtered": ("by_hand", "hybrid+sentences"),
}

METRIC_NAMES = {
    "faithfulness": "CitationFaithfulness",
    "answer": "AnswerRelevancy",
    "context": "ContextualRelevancy",
}

FIELDS = [
    "run",
    "question_id",
    "question",
    "role_family",
    "level",
    "metric",
    "score",
    "status",
    "reason",
    "answer",
    "source_count",
    "context_chars",
    "posts_override",
    "recency_weight_override",
    "sources",
    "details",
]


def positive_int(value):
    value = int(value)

    if value <= 0:
        raise argparse.ArgumentTypeError(
            "Must be a positive integer"
        )

    return value


def parse_args():
    parser = argparse.ArgumentParser(
        description="Evaluate the career-roadmap RAG."
    )

    parser.add_argument(
        "run",
        nargs="?",
        default="baseline",
        choices=RUNS,
    )

    parser.add_argument(
        "limit",
        nargs="?",
        type=positive_int,
        help="Evaluate only the first N questions.",
    )

    parser.add_argument(
        "--set",
        dest="question_set",
        default="main",
        choices=SETS,
        help="Question set: main (7 tuning questions) or heldout (4 new ones).",
    )

    parser.add_argument(
        "--questions",
        nargs="+",
        type=positive_int,
        help="Specific question numbers, such as 3 5 6 7.",
    )

    parser.add_argument(
        "--metrics",
        nargs="+",
        choices=["all", "faithfulness", "answer", "context"],
        default=["all"],
        help="Metrics to evaluate. Default: all.",
    )

    parser.add_argument(
        "--posts",
        type=positive_int,
        help="Override retrieval's returned-job count.",
    )

    parser.add_argument(
        "--recency-weight",
        type=float,
        help="Override retrieval's freshness bonus.",
    )

    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Show intermediate judge output.",
    )

    args = parser.parse_args()

    if args.limit is not None and args.questions is not None:
        parser.error("Use either limit or --questions, not both.")

    tests = SETS[args.question_set]

    if args.questions and any(
        number > len(tests) for number in args.questions
    ):
        parser.error(
            f"Question numbers must be between 1 and {len(tests)}."
        )

    if "all" in args.metrics and len(args.metrics) > 1:
        parser.error("Use --metrics all by itself.")

    if args.metrics == ["all"]:
        args.metrics = ["faithfulness", "answer", "context"]
    else:
        args.metrics = list(dict.fromkeys(args.metrics))

    # The context-only shortcut uses the prepare_posts() interface
    # from the updated rag_by_hand.py.
    if args.run == "langchain" and args.metrics == ["context"]:
        parser.error(
            "Context-only mode currently supports baseline, "
            "hybrid, and filtered—not the separate LangChain path."
        )

    return args


def make_metric(key, verbose=False):
    if key == "faithfulness":
        return CitationFaithfulnessMetric(
            GroqJudge(reasoning="medium"),
            threshold=THRESHOLD,
        )

    if key == "answer":
        return AnswerRelevancyMetric(
            threshold=THRESHOLD,
            model=GroqJudge(),
            async_mode=False,
            verbose_mode=verbose,
        )

    return ContextualRelevancyMetric(
        threshold=THRESHOLD,
        model=GroqJudge(),
        async_mode=False,
        verbose_mode=verbose,
    )


def json_default(value):
    if hasattr(value, "model_dump"):
        return value.model_dump()

    if hasattr(value, "dict"):
        return value.dict()

    return str(value)


def metric_details(metric):
    details = {}

    for attribute in (
        "statements",
        "verdicts",
        "relevant_statements",
        "irrelevant_statements",
        "verbose_logs",
    ):
        value = getattr(metric, attribute, None)

        if value is not None:
            details[attribute] = value

    return json.dumps(
        details,
        ensure_ascii=False,
        default=json_default,
    )


def is_rate_limit(exc):
    """Recognize direct or wrapped rate-limit exceptions."""
    seen = set()
    current = exc

    while current is not None and id(current) not in seen:
        seen.add(id(current))

        status_code = getattr(current, "status_code", None)
        text = str(current).lower()

        if (
            status_code == 429
            or type(current).__name__ == "RateLimitError"
            or "rate_limit_exceeded" in text
            or "rate limit reached" in text
        ):
            return True

        current = current.__cause__ or current.__context__

    return False


def validate_result(result):
    if not isinstance(result, dict):
        raise TypeError("RAG result must be a dictionary.")

    answer = result.get("answer")
    sources = result.get("sources")

    if not isinstance(answer, str):
        raise TypeError("answer must be a string.")

    if not isinstance(sources, list) or not all(
        isinstance(source, str) for source in sources
    ):
        raise TypeError("sources must be a list of strings.")

    return answer, sources


def main():
    args = parse_args()

    if args.posts is not None:
        os.environ["RAG_N_POSTS"] = str(args.posts)

    if args.recency_weight is not None:
        os.environ["RAG_RECENCY_WEIGHT"] = str(
            args.recency_weight
        )

    tests = SETS[args.question_set]

    if args.questions:
        question_ids = list(dict.fromkeys(args.questions))
    else:
        count = min(args.limit or len(tests), len(tests))
        question_ids = list(range(1, count + 1))

    code, mode = RUNS[args.run]
    context_only = args.metrics == ["context"]

    if context_only:
        from rag_by_hand import prepare_posts, source_blocks

        def get_result(test):
            posts = prepare_posts(
                test["question"],
                role_family=test["role_family"],
                level=test["level"],
                mode=mode,
            )

            # No generated answer is needed for contextual relevance.
            return {
                "answer": "",
                "sources": source_blocks(posts),
            }

    else:
        if code == "langchain":
            from rag_langchain import rag_answer
        else:
            from rag_by_hand import rag_answer

        def get_result(test):
            return rag_answer(
                test["question"],
                test["role_family"],
                test["level"],
                mode=mode,
            )

    os.makedirs("evals", exist_ok=True)

    timestamp = datetime.now().strftime(
        "%Y-%m-%d_%H-%M-%S-%f"
    )

    question_label = "-".join(map(str, question_ids))
    metric_label = "-".join(args.metrics)

    set_label = "" if args.question_set == "main" else f"{args.question_set}-"

    stem = (
        f"evals/{args.run}-{set_label}q{question_label}-"
        f"{metric_label}_{timestamp}"
    )

    csv_path = stem + ".csv"
    rows = []
    stop = False

    print(
        f"Run: {args.run} | set: {args.question_set} | questions: {question_ids} "
        f"| metrics: {args.metrics}"
    )

    if context_only:
        print(
            "Context-only mode: no answer-generation API call."
        )

    print("Results file:", csv_path)

    with open(
        csv_path,
        "w",
        newline="",
        encoding="utf-8",
    ) as file:
        writer = csv.DictWriter(file, fieldnames=FIELDS)
        writer.writeheader()
        file.flush()

        def save_row(base, metric, score, status, reason, details=""):
            row = {
                **base,
                "metric": metric,
                "score": score,
                "status": status,
                "reason": reason,
                "details": details,
            }

            writer.writerow(row)
            file.flush()
            rows.append(row)

        for question_id in question_ids:
            test = tests[question_id - 1]
            start = time.time()

            print(
                f"\n=== Question {question_id}: "
                f"{test['question']} ==="
            )

            base = {
                "run": (
                    args.run if args.question_set == "main"
                    else f"{args.run}-{args.question_set}"
                ),
                "question_id": question_id,
                "question": test["question"],
                "role_family": test["role_family"],
                "level": test["level"],
                "answer": "",
                "source_count": 0,
                "context_chars": 0,
                "posts_override": os.getenv("RAG_N_POSTS", ""),
                "recency_weight_override": os.getenv(
                    "RAG_RECENCY_WEIGHT", ""
                ),
                "sources": "[]",
            }

            try:
                answer, sources = validate_result(
                    get_result(test)
                )
            except Exception as exc:
                reason = f"{type(exc).__name__}: {exc}"
                limited = is_rate_limit(exc)

                save_row(
                    base,
                    "Preparation",
                    None,
                    "RATE_LIMIT" if limited else "ERROR",
                    reason,
                )

                print(reason)

                if limited:
                    stop = True
                    break

                continue

            base.update({
                "answer": answer,
                "source_count": len(sources),
                "context_chars": sum(map(len, sources)),
                "sources": json.dumps(
                    sources,
                    ensure_ascii=False,
                ),
            })

            # Save the exact prepared input BEFORE judge calls.
            snapshot_path = f"{stem}-q{question_id}.json"

            with open(
                snapshot_path,
                "w",
                encoding="utf-8",
            ) as snapshot:
                json.dump(
                    {
                        "run": args.run,
                        "mode": mode,
                        "context_only": context_only,
                        "question_id": question_id,
                        "question": test["question"],
                        "role_family": test["role_family"],
                        "level": test["level"],
                        "answer": answer,
                        "sources": sources,
                        "posts_override": base["posts_override"],
                        "recency_weight_override": (
                            base["recency_weight_override"]
                        ),
                    },
                    snapshot,
                    ensure_ascii=False,
                    indent=2,
                )

            print(
                f"Context: {len(sources)} sources, "
                f"{base['context_chars']} characters"
            )

            if not sources or not any(
                source.strip() for source in sources
            ):
                save_row(
                    base,
                    "Preparation",
                    None,
                    "NO_CONTEXT",
                    "No usable context; evaluation skipped.",
                )
                print("No context selected; skipping evaluation.")
                continue

            case = LLMTestCase(
                input=test["question"],
                actual_output=answer,
                retrieval_context=sources,
            )

            for key in args.metrics:
                name = METRIC_NAMES[key]
                metric = None
                limited = False

                try:
                    metric = make_metric(key, args.verbose)
                    metric.measure(case)

                    if metric.score is None:
                        raise RuntimeError(
                            "Metric completed without a score."
                        )

                    score = float(metric.score)

                    if not math.isfinite(score):
                        raise RuntimeError(
                            "Metric returned a non-finite score."
                        )

                    reason = metric.reason
                    status = (
                        "PASS" if metric.is_successful() else "FAIL"
                    )

                except Exception as exc:
                    score = None
                    reason = f"{type(exc).__name__}: {exc}"
                    limited = is_rate_limit(exc)
                    status = "RATE_LIMIT" if limited else "ERROR"

                details = (
                    metric_details(metric)
                    if metric is not None
                    else ""
                )

                save_row(
                    base, name, score, status, reason, details
                )

                shown = "-" if score is None else f"{score:.2f}"
                print(f"  {name:<22} {shown:>5}  {status}")

                reason_text = str(reason)
                print(
                    "    "
                    + (
                        reason_text
                        if args.verbose
                        else reason_text[:500]
                    )
                )

                if limited:
                    stop = True
                    break

            print(f"  ({time.time() - start:.0f} s)")

            if stop:
                break

    print("\n=== COMPLETED SCORES ===")

    for key in args.metrics:
        name = METRIC_NAMES[key]
        metric_rows = [
            row for row in rows if row["metric"] == name
        ]
        scored = [
            row for row in metric_rows
            if row["score"] is not None
        ]

        average = (
            f"{sum(row['score'] for row in scored) / len(scored):.2f}"
            if scored
            else "-"
        )

        passed = sum(
            row["status"] == "PASS" for row in scored
        )

        print(
            f"  {name:<22} {average:>5} "
            f"| scored {len(scored)}/{len(question_ids)} "
            f"| passed {passed}"
        )

    if stop:
        print(
            "\nStopped on a rate limit. This is an incomplete run, "
            "not a complete evaluation."
        )

    print("\nSaved:", csv_path)
    print("Prepared contexts are saved in matching -qN.json files.")


if __name__ == "__main__":
    main()