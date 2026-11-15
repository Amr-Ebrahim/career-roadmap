# roadmap_agent.py - Stage 6: a writer agent (tools -> roadmap) plus a critic that checks
# the draft against the tool results and sends it back once for fixes.
import re
import sys
from typing import List

from dotenv import load_dotenv
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_groq import ChatGroq
from langgraph.graph import END, START, MessagesState, StateGraph
from langgraph.prebuilt import ToolNode
from pydantic import BaseModel, Field

from agent_tools import TOOLS as STATS_TOOLS
from rag_by_hand import check_citations
from search_tool import SOURCES, reset_sources, search_job_posts

load_dotenv()

# 20b while developing: it has its own daily Groq budget. Switch to 120b for final runs.
AGENT_MODEL = "openai/gpt-oss-20b"
TOOLS = STATS_TOOLS + [search_job_posts]
MAX_REVISIONS = 1
# same idea as in citation_faithfulness.py: words that turn data into a generalization
GENERALIZING = re.compile(r"\b(most|typical|typically|common|commonly|consistently|many|usually|"
                          r"generally|often|all jobs|always)\b", re.IGNORECASE)

WRITER = """You build a learning roadmap for someone who wants a specific tech job.
Work in this order:
1. Call top_skills for the role family and level.
2. Call level_progression for the role family, to see which skills grow later.
3. Call search_job_posts once per phase, for that phase's main skill (3 searches),
   so each phase's example is about its own skills.
Then write the roadmap:
- Phase 1 "Foundations", Phase 2 "Core skills", Phase 3 "Next level".
- For each skill give its share from the tools, e.g. "AWS (in 59% of 70 entry posts)".
- Add one cited example per phase, using the source numbers exactly like [3].
Rules:
- Every number and every comparison ("more than", "rises") must match the tool results.
- Never say "most", "typical", "common" or "all jobs"; give the number instead.
- Only name skills that appear in the tool results. If you add general advice that is NOT
  from the data (for example specific AWS services), put it under a final heading
  "General advice (not from the job data)".
- If a tool shows a WARNING about few posts, say the numbers are rough.
- Keep it under 300 words."""

CRITIC = """You check a career roadmap against the EVIDENCE it was built from.
List every problem of these kinds:
- number: a percentage or post count that is not in the evidence or differs from it
- comparison: a claim like "most common", "rises", "more than" that the evidence numbers contradict
- outside_knowledge: a skill, tool or fact that is not in the evidence and is NOT under the
  heading "General advice (not from the job data)"
- citation: an example [n] whose source text in the evidence does not support it
Quote the exact words from the roadmap. If there are no problems, return an empty list.

EVIDENCE (tool results):
{evidence}

ROADMAP:
{draft}"""


class Problem(BaseModel):
    kind: str = Field(description="number, comparison, outside_knowledge or citation")
    quote: str = Field(description="the exact words from the roadmap")
    issue: str = Field(description="what is wrong, using the evidence")


class Critique(BaseModel):
    problems: List[Problem]


class RoadmapState(MessagesState):
    revisions: int
    problems: list


def build_graph(llm, critic_llm):
    writer_llm = llm.bind_tools(TOOLS)
    # json_schema + strict: Groq's constrained decoding, the reply MUST match Critique
    critic = critic_llm.with_structured_output(Critique, method="json_schema", strict=True)

    def writer(state: RoadmapState):
        reply = writer_llm.invoke([SystemMessage(WRITER)] + state["messages"])
        return {"messages": [reply]}

    def after_writer(state: RoadmapState):
        return "tools" if state["messages"][-1].tool_calls else "critic"

    def review(state: RoadmapState):
        draft = state["messages"][-1].content
        evidence = "\n\n".join(m.content for m in state["messages"] if m.type == "tool")
        try:
            problems = [p.model_dump() for p in
                        critic.invoke(CRITIC.format(evidence=evidence, draft=draft)).problems]
        except Exception as e:  # a failed review shouldn't throw away the roadmap
            print(f"  [critic] LLM check failed ({type(e).__name__}), using code checks only")
            problems = []

        # checks done by code, not by the LLM: they are free and never miss
        _, invalid, _ = check_citations(draft, len(SOURCES))
        for n in invalid:
            problems.append({"kind": "citation", "quote": f"[{n}]", "issue": "no such source"})
        data_part = draft.split("General advice")[0]  # the labeled advice section may generalize
        for line in data_part.splitlines():
            if GENERALIZING.search(line):
                problems.append({"kind": "comparison", "quote": line.strip()[:120],
                                 "issue": "generalizing word; give the number instead"})

        update = {"problems": problems}
        if problems and state["revisions"] < MAX_REVISIONS:
            notes = "\n".join(f"- [{p['kind']}] \"{p['quote']}\": {p['issue']}" for p in problems)
            update["messages"] = [HumanMessage(
                "A reviewer checked your roadmap against the tool results and found these "
                f"problems:\n{notes}\nRewrite the whole roadmap and fix all of them. "
                "You may call the tools again to check numbers.")]
            update["revisions"] = state["revisions"] + 1
        return update

    def after_review(state: RoadmapState):
        sent_back = state["messages"][-1].type == "human"
        return "writer" if sent_back else END

    graph = StateGraph(RoadmapState)
    graph.add_node("writer", writer)
    graph.add_node("tools", ToolNode(TOOLS))
    graph.add_node("critic", review)
    graph.add_edge(START, "writer")
    graph.add_conditional_edges("writer", after_writer)
    graph.add_edge("tools", "writer")
    graph.add_conditional_edges("critic", after_review)
    return graph.compile()


def show_problems(title, problems):
    print(f"\n=== {title}: {len(problems)} problem(s)")
    for p in problems:
        print(f"  [{p['kind']}] \"{p['quote'][:90]}\" -> {p['issue']}")


def run(request, llm=None, critic_llm=None):
    reset_sources()
    llm = llm or ChatGroq(model=AGENT_MODEL, temperature=0.2, max_tokens=1500,
                          reasoning_effort="low", max_retries=6)
    critic_llm = critic_llm or ChatGroq(model=AGENT_MODEL, temperature=0, max_tokens=2000,
                                        reasoning_effort="medium", max_retries=6)
    app = build_graph(llm, critic_llm)

    final, open_problems = None, []
    for step in app.stream({"messages": [HumanMessage(request)], "revisions": 0, "problems": []},
                           {"recursion_limit": 25}, stream_mode="updates"):
        for node, update in step.items():
            for msg in update.get("messages", []):
                for call in getattr(msg, "tool_calls", []) or []:
                    print(f"  -> {call['name']}({call['args']})")
                if msg.type == "tool":
                    print(f"  <- {msg.name}: {len(msg.content)} characters")
                if node == "writer" and msg.type == "ai" and not msg.tool_calls:
                    final = msg.content
                    print("  [writer] draft written")
            if node == "critic":
                open_problems = update["problems"]
                show_problems("CRITIC", open_problems)
                if update.get("messages"):
                    print("  [critic] sent back to the writer for one revision")

    print("\n=== FINAL ROADMAP ===")
    print(final)
    if open_problems:  # the last review still found something: show it, don't hide it
        print("\nReviewer notes (not fixed):")
        for p in open_problems:
            print(f"- [{p['kind']}] \"{p['quote'][:90]}\": {p['issue']}")
    total, invalid, unused = check_citations(final, len(SOURCES))
    print(f"\nCitations: {total} | invalid numbers: {invalid or 'none'} | sources never cited: {unused or 'none'}")
    print("\nSources:")
    for i, p in enumerate(SOURCES, start=1):
        print(f"  [{i}] {p['title']} | {p['company']} | {p.get('url') or 'no link'}")
    return final, open_problems


if __name__ == "__main__":
    request = " ".join(sys.argv[1:]) or "I want an entry-level DevOps / cloud engineer job. What should I learn?"
    print("REQUEST:", request, "\n")
    run(request)