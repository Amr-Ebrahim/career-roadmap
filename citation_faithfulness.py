# citation_faithfulness.py - our own DeepEval metric.
# Checks every line of the answer against the RAW text of the sources it cites,
# in ONE judge call per answer. (DeepEval's built-in Faithfulness first summarizes
# all sources into a list of "truths", which loses details and source numbers.)
import re
from typing import List, Literal

from pydantic import BaseModel
from deepeval.metrics import BaseMetric
from deepeval.test_case import LLMTestCase

CITE = re.compile(r"\[(\d+)\]")
GENERALIZING = re.compile(
    r"\b(most|typical|typically|common|commonly|consistently|many|usually|generally|often)\b",
    re.IGNORECASE,
)
POINTS = {"supported": 1.0, "partly": 0.5, "unsupported": 0.0}

PROMPT = """You check an answer that was written ONLY from the job posts below.

SOURCES (each starts with its number):
{sources}

ANSWER LINES:
{lines}

Give a verdict for EVERY answer line:
- "no_claim": a heading, or a line that states nothing about the jobs.
- "supported": everything the line states is written in the source(s) it cites. Paraphrase is fine.
- "partly": some items are in the cited sources, some are not.
- "unsupported": the main content is not in the cited sources.
If a line cites no source, check it against all sources.
"missing": each specific item (tool, skill, certification, number, requirement) in the line
that the cited sources do NOT contain.
"other_source": the items from "missing" that DO appear in a source the line did not cite.
Use only the sources. Never use your own knowledge about jobs or tools."""


class LineVerdict(BaseModel):
    line: int
    verdict: Literal["supported", "partly", "unsupported", "no_claim"]
    missing: List[str] = []
    other_source: List[str] = []


class Verdicts(BaseModel):
    verdicts: List[LineVerdict]


class CitationFaithfulnessMetric(BaseMetric):
    def __init__(self, model, threshold=0.7):
        self.model = model
        self.threshold = threshold
        self.evaluation_model = model.get_model_name()
        self.async_mode = False
        self.include_reason = True
        self.details = []

    def _ask_judge(self, prompt):
        # one retry: if the reply breaks the schema once, ask again
        for attempt in range(2):
            try:
                return self.model.generate(prompt, schema=Verdicts)
            except Exception:
                if attempt == 1:
                    raise

    def measure(self, test_case: LLMTestCase, *args, **kwargs) -> float:
        self.error = None
        lines = [l.strip() for l in test_case.actual_output.splitlines() if l.strip()]
        numbered = "\n".join(f"{i}. {text}" for i, text in enumerate(lines, start=1))
        prompt = PROMPT.format(sources="\n\n".join(test_case.retrieval_context),
                               lines=numbered)

        by_line = {v.line: v for v in self._ask_judge(prompt).verdicts}

        self.details = []
        points, claims = 0.0, 0
        for i, text in enumerate(lines, start=1):
            v = by_line.get(i)
            verdict = v.verdict if v else "skipped"  # the judge forgot this line
            self.details.append({
                "line": i,
                "text": text,
                "verdict": verdict,
                "cites": [int(n) for n in CITE.findall(text)],
                "missing": v.missing if v else [],
                "other_source": v.other_source if v else [],
                "generalizing": GENERALIZING.findall(text),
            })
            if verdict in POINTS:
                claims += 1
                points += POINTS[verdict]

        self.score = points / claims if claims else 1.0
        self.success = self.score >= self.threshold
        self.reason = self._make_reason(claims)
        return self.score

    def _make_reason(self, claims):
        count = lambda name: sum(d["verdict"] == name for d in self.details)
        missing = [m for d in self.details for m in d["missing"]]
        moved = [m for d in self.details for m in d["other_source"]]
        general = [d["line"] for d in self.details if d["generalizing"]]
        parts = [f"{count('supported')} supported, {count('partly')} partly, "
                 f"{count('unsupported')} unsupported of {claims} claim lines"]
        if count("skipped"):
            parts.append(f"{count('skipped')} lines skipped by the judge")
        if missing:
            parts.append("not in cited sources: " + ", ".join(missing))
        if moved:
            parts.append("wrong citation for: " + ", ".join(moved))
        if general:
            parts.append(f"generalizing words in lines {general}")
        return ". ".join(parts) + "."

    async def a_measure(self, test_case: LLMTestCase, *args, **kwargs) -> float:
        return self.measure(test_case)

    @property
    def __name__(self):
        return "Citation Faithfulness"