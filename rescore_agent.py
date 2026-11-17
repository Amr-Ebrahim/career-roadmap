# rescore_agent.py - judge the SAVED agent roadmaps again, without building them again.
# The first agent eval gave the judge only the job-post excerpts, but a roadmap's numbers and
# learning order come from the plan (counted by code over all matching posts), so correct
# lines were marked "unsupported". Now the judge also gets the plan, and only the data part of
# the roadmap (the "General advice (not from the job data)" section is outside the data on purpose).
#   python rescore_agent.py evals/agent_2026-11-17.csv
# Budget: one gpt-oss-120b judge call per roadmap (~6-7K tokens each, ~55K for 8).
# No gpt-oss-20b tokens: nothing is built again.
# Result: evals/agent_2026-11-17_rescored.csv (old score kept as citation_faithfulness_v1).
import json
import sys

import pandas as pd

from groq_judge import GroqJudge  # import first: it loads .env before deepeval
from deepeval.test_case import LLMTestCase

from citation_faithfulness import CitationFaithfulnessMetric

THRESHOLD = 0.7


def data_part(roadmap):
    return roadmap.split("General advice")[0]


def main():
    if len(sys.argv) < 2:
        sys.exit("usage: python rescore_agent.py evals/agent_<date>.csv")
    path = sys.argv[1]
    df = pd.read_csv(path)
    metric = CitationFaithfulnessMetric(GroqJudge(reasoning="medium"), threshold=THRESHOLD)
    print(f"Rescoring {len(df)} roadmaps from {path}, judge: {metric.evaluation_model}\n")

    old, new, reasons = [], [], []
    for n, row in enumerate(df.itertuples(), start=1):
        if not isinstance(row.roadmap, str) or not row.roadmap.strip():
            print(f"[{n}] no roadmap saved (the run failed), skipped")
            old.append(None); new.append(None); reasons.append("no roadmap")
            continue
        case = LLMTestCase(input=row.request, actual_output=data_part(row.roadmap),
                           retrieval_context=json.loads(row.sources),
                           context=[row.plan_text])
        try:
            metric.measure(case)
            score, reason = round(metric.score, 2), metric.reason
        except Exception as e:  # one failed judge call shouldn't stop the others
            score, reason = None, f"{type(e).__name__}: {e}"
        old.append(row.citation_faithfulness); new.append(score); reasons.append(reason)
        print(f"[{n}] {row.request[:50]}")
        print(f"    before {row.citation_faithfulness}  ->  now {score}")
        print(f"    {reason}\n")

    df["citation_faithfulness_v1"] = old
    df["citation_faithfulness"] = new
    df["judge_reason"] = reasons
    out = path.replace(".csv", "_rescored.csv")
    df.to_csv(out, index=False, encoding="utf-8")

    done = [(o, s) for o, s in zip(old, new) if s is not None and o is not None]
    if done:
        print(f"=== AVERAGE over {len(done)} roadmaps: before {sum(o for o, _ in done) / len(done):.2f}"
              f"  ->  now {sum(s for _, s in done) / len(done):.2f}")
    print(f"Saved: {out}")


if __name__ == "__main__":
    main()
