# roadmap_agent.py - Stage 6: the full roadmap pipeline in LangGraph.
#   intake (LLM)      -> what the person wants and already knows
#   planner (code)    -> gap finder + curriculum from the stats (planner.py)
#   researcher (code) -> one example search per phase
#   writer (LLM)      -> writes the roadmap (may search again when revising)
#   critic (LLM + code) -> checks the draft against the plan and the examples, one revision
import re
import sys
from typing import List, Optional

from dotenv import load_dotenv
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_groq import ChatGroq
from langgraph.graph import END, START, MessagesState, StateGraph
from langgraph.prebuilt import ToolNode
from pydantic import BaseModel, Field

from planner import make_plan, plan_to_text
from rag_by_hand import check_citations, normalize_citations
from search_tool import SOURCES, Family, Level, reset_sources, search_job_posts

load_dotenv()

# 20b while developing: it has its own daily Groq budget. Switch to 120b for final runs.
AGENT_MODEL = "openai/gpt-oss-20b"
TOOLS = [search_job_posts]
MAX_REVISIONS = 1
# same idea as in citation_faithfulness.py: words that turn data into a generalization
GENERALIZING = re.compile(r"\b(most|typical|typically|common|commonly|consistently|many|usually|"
                          r"generally|often|all jobs|always)\b", re.IGNORECASE)
QUOTED = re.compile(r"[“\"][^”\"]*[”\"]")

INTAKE = """Read a person's request for a tech career roadmap and fill in the fields.
role_family, pick the closest:
  software (general software engineer/developer), backend, frontend, mobile,
  data (data analyst, data scientist, data engineer, BI), ai_ml (ML engineer, AI engineer),
  devops_cloud (DevOps, SRE, cloud, platform engineer), security,
  networking_it (help desk, IT support, network engineer, system administrator),
  qa (software testing), architecture (solutions/software architect)
level: entry for junior, graduate, beginner or no experience; intern for internships;
  otherwise the level they ask for. If they don't say, entry.
title_keyword: a word from job titles that narrows a family holding different jobs, e.g.
  data -> "analyst", "scientist" or "engineer"; networking_it -> "help desk", "support",
  "network" or "administrator"; security -> "analyst" or "engineer". Use null when the
  family already matches the job (e.g. DevOps engineer, frontend developer).
known_skills: skills the person says they already have, with standard names
  (k8s -> Kubernetes, powerbi -> Power BI, js -> JavaScript). Empty list if none.

REQUEST: {request}"""

WRITER = """You write a learning roadmap from a PLAN and SEARCH RESULTS taken from real job posts.
Write:
- One line on what the plan is based on (number and kind of posts).
- "Already have" if the plan lists skills the person has.
- The phases in the plan's order: Foundations, Core skills, Next level. For each skill give the
  share from the plan, e.g. "SQL (in 44% of the posts)". Write "rises with seniority" or
  "falls with seniority" ONLY for skills the plan marks (rises) or (falls).
- One example per phase, taken from that phase's search results: quote a few words that
  mention the skill and cite the source number exactly like [3]. If none of that phase's
  results mention the skill, write "No example found in the searched posts."
- If the plan has NOTE lines, list them under "Notes". If it has none, leave Notes out.
Rules:
- Use only the plan's skills, phases and numbers. Never invent or change a number.
- Never say "most", "typical", "common" or "all jobs" in your own words; give the number instead.
- General advice that is NOT from the data goes under a final heading
  "General advice (not from the job data)".
- Keep it under 300 words.
When revising, you may call search_job_posts to find a better example."""

CRITIC = """You check a career roadmap against the EVIDENCE it was built from.
List every problem of these kinds:
- number: a percentage or post count that is not in the evidence or differs from it
- comparison: a claim like "rises", "more than" that the evidence numbers contradict
- outside_knowledge: a skill, tool or fact that is not in the evidence and is NOT under the
  heading "General advice (not from the job data)"
- citation: an example [n] whose source text in the evidence does not mention what it is used for
Quote the exact words from the roadmap. If there are no problems, return an empty list.

EVIDENCE (the plan and the search results):
{evidence}

ROADMAP:
{draft}"""


class Intake(BaseModel):
    role_family: Family
    level: Level
    title_keyword: Optional[str] = Field(description="word from job titles, or null")
    known_skills: List[str]


class Problem(BaseModel):
    kind: str = Field(description="number, comparison, outside_knowledge or citation")
    quote: str = Field(description="the exact words from the roadmap")
    issue: str = Field(description="what is wrong, using the evidence")


class Critique(BaseModel):
    problems: List[Problem]


class RoadmapState(MessagesState):
    request: str
    intake: dict
    plan: dict
    plan_text: str
    research: str
    revisions: int
    problems: list


def build_graph(llm, judge_llm):
    writer_llm = llm.bind_tools(TOOLS)
    # json_schema + strict: Groq's constrained decoding, replies MUST match the schema
    intake_llm = judge_llm.with_structured_output(Intake, method="json_schema", strict=True)
    critic = judge_llm.with_structured_output(Critique, method="json_schema", strict=True)

    def intake(state: RoadmapState):
        parsed = intake_llm.invoke(INTAKE.format(request=state["request"]))
        return {"intake": parsed.model_dump()}

    def planner(state: RoadmapState):
        i = state["intake"]
        plan = make_plan(i["role_family"], i["level"], i["title_keyword"], i["known_skills"])
        return {"plan": plan, "plan_text": plan_to_text(plan)}

    def researcher(state: RoadmapState):
        # code, not the LLM, decides the searches: one per phase, for its first skill,
        # so no phase is skipped and every example search is about the right skill
        plan = state["plan"]
        job = plan["title_keyword"] or plan["role_family"].replace("_", " ")
        parts = []
        for phase, skills in plan["phases"].items():
            if not skills:
                continue
            query = f"{skills[0]['skill']} {job}"
            result = search_job_posts.invoke({
                "query": query, "role_family": plan["role_family"], "level": plan["level"],
                "title_keyword": plan["title_keyword"]})
            parts.append(f"{phase} (searched: '{query}'):\n{result}")
            print(f"  [researcher] {phase}: searched '{query}'")
        research = "\n\n".join(parts)
        message = (f"Request: {state['request']}\n"
                   f"role_family={plan['role_family']}, level={plan['level']}, "
                   f"title_keyword={plan['title_keyword']}\n\n{state['plan_text']}\n\n"
                   f"SEARCH RESULTS:\n{research}")
        return {"research": research, "messages": [HumanMessage(message)]}

    def writer(state: RoadmapState):
        reply = writer_llm.invoke([SystemMessage(WRITER)] + state["messages"])
        if not reply.tool_calls:  # gpt-oss sometimes cites like 【3】: turn it into [3]
            reply.content = normalize_citations(reply.content)
        return {"messages": [reply]}

    def after_writer(state: RoadmapState):
        return "tools" if state["messages"][-1].tool_calls else "critic"

    def review(state: RoadmapState):
        draft = state["messages"][-1].content
        results = [m.content for m in state["messages"] if m.type == "tool"]
        evidence = "\n\n".join([state["plan_text"], state["research"]] + results)
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
            own_words = QUOTED.sub("", line)  # words quoted from a job post are not our claim
            if GENERALIZING.search(own_words):
                problems.append({"kind": "comparison", "quote": line.strip()[:120],
                                 "issue": "generalizing word; give the number instead"})

        update = {"problems": problems}
        if problems and state["revisions"] < MAX_REVISIONS:
            notes = "\n".join(f"- [{p['kind']}] \"{p['quote']}\": {p['issue']}" for p in problems)
            update["messages"] = [HumanMessage(
                "A reviewer checked your roadmap against the plan and the search results and "
                f"found these problems:\n{notes}\nRewrite the whole roadmap and fix all of them. "
                "You may search again for better examples.")]
            update["revisions"] = state["revisions"] + 1
        return update

    def after_review(state: RoadmapState):
        sent_back = state["messages"][-1].type == "human"
        return "writer" if sent_back else END

    graph = StateGraph(RoadmapState)
    graph.add_node("intake", intake)
    graph.add_node("planner", planner)
    graph.add_node("researcher", researcher)
    graph.add_node("writer", writer)
    graph.add_node("tools", ToolNode(TOOLS))
    graph.add_node("critic", review)
    graph.add_edge(START, "intake")
    graph.add_edge("intake", "planner")
    graph.add_edge("planner", "researcher")
    graph.add_edge("researcher", "writer")
    graph.add_conditional_edges("writer", after_writer)
    graph.add_edge("tools", "writer")
    graph.add_conditional_edges("critic", after_review)
    return graph.compile()


def show_problems(title, problems):
    print(f"\n=== {title}: {len(problems)} problem(s)")
    for p in problems:
        print(f"  [{p['kind']}] \"{p['quote'][:90]}\" -> {p['issue']}")


def run(request, llm=None, judge_llm=None):
    reset_sources()
    llm = llm or ChatGroq(model=AGENT_MODEL, temperature=0.2, max_tokens=1500,
                          reasoning_effort="low", max_retries=6)
    judge_llm = judge_llm or ChatGroq(model=AGENT_MODEL, temperature=0, max_tokens=2000,
                                      reasoning_effort="medium", max_retries=6)
    app = build_graph(llm, judge_llm)

    final, open_problems = None, []
    start = {"request": request, "messages": [], "revisions": 0, "problems": []}
    for step in app.stream(start, {"recursion_limit": 25}, stream_mode="updates"):
        for node, update in step.items():
            if node == "intake":
                print(f"[intake] {update['intake']}")
            if node == "planner":
                print(f"\n[planner]\n{update['plan_text']}\n")
            if node == "researcher":
                continue  # its searches are printed as they happen; skip the long message
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
    request = (" ".join(sys.argv[1:]) or
               "I know Python and Excel and I want a junior data analyst job. What should I learn?")
    print("REQUEST:", request, "\n")
    run(request)