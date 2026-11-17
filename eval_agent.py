# eval_agent.py - Stage 7: evaluate the FULL roadmap agent, not just the plain RAG.
#   python eval_agent.py              -> all requests, with the LLM judge
#   python eval_agent.py 3            -> first 3 requests only (a test run)
#   python eval_agent.py --no-judge   -> code checks only (no judge tokens)
# Budget: each roadmap uses ~15-20K tokens of gpt-oss-20b; the judge ~6-7K of gpt-oss-120b.
# The judge checks numbers and learning order against the plan, examples [n] against the posts.
# Results: evals/agent_<date>.csv (test runs: evals/test-agent_<date>.csv), with the roadmap,
# the plan and the exact excerpts the writer saw, so every row can be re-checked later.
import csv
import json
import os
import re
import sys
import time
from datetime import date

from groq_judge import GroqJudge  # import first: it loads .env before deepeval
from deepeval.test_case import LLMTestCase

from citation_faithfulness import CitationFaithfulnessMetric
from roadmap_agent import check_quotes, generate_roadmap
from search_tool import SOURCES

THRESHOLD = 0.7

# one request per kind of job; "expect" is what the intake agent should understand
TESTS = [
    {"request": "I know Python and Excel and I want a junior data analyst job. What should I learn?",
     "expect": {"role_family": "data", "level": "entry"}},
    {"request": "I know Linux and Python, I want a junior DevOps job",
     "expect": {"role_family": "devops_cloud", "level": "entry"}},
    {"request": "I want my first help desk job, I already know Windows and Active Directory",
     "expect": {"role_family": "networking_it", "level": "entry"}},
    {"request": "I'm a computer science graduate and I know Java. I want to become a backend developer.",
     "expect": {"role_family": "backend", "level": "entry"}},
    {"request": "I know HTML and CSS and I want a junior frontend developer job",
     "expect": {"role_family": "frontend", "level": "entry"}},
    {"request": "I want to become an entry-level security analyst. I know networking basics.",
     "expect": {"role_family": "security", "level": "entry"}},
    {"request": "I know Python and statistics. How do I become a junior machine learning engineer?",
     "expect": {"role_family": "ai_ml", "level": "entry"}},
    {"request": "I have no experience and I want to get into software testing (QA)",
     "expect": {"role_family": "qa", "level": "entry"}},
]


def plan_skills(plan):
    return [s for skills in plan["phases"].values() for s in skills]


def mentioned(skill, text):
    return re.search(rf"(?<![\w+#]){re.escape(skill)}(?![\w+#])", text, re.IGNORECASE) is not None


def plan_numbers(plan):
    # every number the writer is allowed to print as a percentage
    nums = set()
    for s in plan_skills(plan) + plan["have"]:
        nums.add(round(s["share"]))
        nums.update(round(x) for x in s.get("entry_to_senior", ()))
        for key in ("or", "includes"):
            nums.update(round(o["share"]) for o in s.get(key, []))
    return nums


def code_checks(result, expect):
    """Free checks of one roadmap against its own plan."""
    plan, text = result["plan"], result["roadmap"] or ""
    data_part = text.split("General advice")[0]
    skills = plan_skills(plan)
    names = [s["skill"] for s in sorted(skills, key=lambda s: s.get("step", 0))]

    covered = [n for n in names if mentioned(n, data_part)]
    percents = [int(round(float(p))) for p in re.findall(r"(\d{1,3}(?:\.\d)?)\s?%", data_part)]
    allowed = plan_numbers(plan)
    wrong_numbers = sorted({p for p in percents if p not in allowed})

    # learning order: the skills' first mentions should come in step order
    firsts = [data_part.lower().find(n.lower()) for n in covered]
    in_order = sum(a < b for a, b in zip(firsts, firsts[1:]))
    pairs = max(len(firsts) - 1, 1)

    intake = result["intake"]
    return {
        "intake_ok": intake["role_family"] == expect["role_family"] and intake["level"] == expect["level"],
        "intake": f"{intake['role_family']}/{intake['level']}/{intake['title_keyword']}",
        "plan_coverage": round(len(covered) / len(names), 2) if names else 1.0,
        "missing_skills": ", ".join(n for n in names if n not in covered),
        "numbers_ok": round(1 - len([p for p in percents if p in wrong_numbers]) / len(percents), 2)
                      if percents else 1.0,
        "wrong_numbers": ", ".join(map(str, wrong_numbers)),
        "order_ok": round(in_order / pairs, 2) if len(firsts) > 1 else 1.0,
        "quote_problems": len(check_quotes(text, names)),
        "invalid_citations": len(result["citations"]["invalid"]),
        "reviewer_notes": len(result["problems"]),
        "revised": any("sent back" in s for s in result["steps"]),
    }


def shown_sources():
    # the excerpts exactly as the writer saw them, numbered like its citations
    return [f"[{n}] {p['title']} at {p['company']}\n" + " ... ".join(p["shown"])
            for n, p in enumerate(SOURCES, start=1)]


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    use_judge = "--no-judge" not in sys.argv
    tests, label = TESTS, "agent"
    if args:
        tests, label = TESTS[: int(args[0])], "test-agent"
    metric = CitationFaithfulnessMetric(GroqJudge(reasoning="medium"), threshold=THRESHOLD) if use_judge else None
    print(f"Agent eval: {len(tests)} requests, judge: {metric.evaluation_model if metric else 'off'}")

    rows = []
    for n, t in enumerate(tests, start=1):
        print(f"\n=== [{n}/{len(tests)}] {t['request']}")
        start = time.time()
        try:
            result = generate_roadmap(t["request"], on_step=lambda text: print("   ", text[:110]))
        except Exception as e:  # one failed run shouldn't stop the others
            print(f"   ERROR {type(e).__name__}: {str(e)[:200]}")
            rows.append({"request": t["request"], "error": f"{type(e).__name__}: {e}"})
            continue
        row = {"request": t["request"], **code_checks(result, t["expect"])}

        sources = shown_sources()
        if metric:
            try:
                # the judge gets the plan too (numbers and order come from it), and only the
                # data part: "General advice (not from the job data)" is outside the data on purpose
                data_part = (result["roadmap"] or "").split("General advice")[0]
                metric.measure(LLMTestCase(input=t["request"], actual_output=data_part,
                                           retrieval_context=sources, context=[result["plan_text"]]))
                row["citation_faithfulness"] = round(metric.score, 2)
                row["judge_reason"] = metric.reason
            except Exception as e:
                row["citation_faithfulness"], row["judge_reason"] = None, f"{type(e).__name__}: {e}"

        row.update({"seconds": round(time.time() - start), "roadmap": result["roadmap"],
                    "plan_text": result["plan_text"], "sources": json.dumps(sources, ensure_ascii=False)})
        rows.append(row)
        shown = {k: v for k, v in row.items() if k not in ("request", "roadmap", "plan_text", "sources", "judge_reason")}
        for k, v in shown.items():
            print(f"    {k:<22} {v}")

    os.makedirs("evals", exist_ok=True)
    path = f"evals/{label}_{date.today()}.csv"
    fields = list(dict.fromkeys(k for r in rows for k in r))
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)

    ok = [r for r in rows if "error" not in r]
    print(f"\n=== SUMMARY ({len(ok)}/{len(rows)} roadmaps built) ===")
    for key in ("intake_ok", "plan_coverage", "numbers_ok", "order_ok", "citation_faithfulness"):
        vals = [float(r[key]) for r in ok if r.get(key) is not None and key in r]
        if vals:
            print(f"  {key:<22} {sum(vals) / len(vals):.2f}")
    for key in ("quote_problems", "invalid_citations", "reviewer_notes"):
        print(f"  {key:<22} {sum(r[key] for r in ok)} in total")
    print(f"  {'revised':<22} {sum(bool(r['revised']) for r in ok)} of {len(ok)} roadmaps")
    print(f"\nSaved: {path}")


if __name__ == "__main__":
    main()
