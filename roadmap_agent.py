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

from planner import CHANGE, make_plan, plan_to_text
from rag_by_hand import check_citations, normalize_citations
from search_tool import SOURCES, Family, Level, reset_sources, search_job_posts

load_dotenv()

# 20b while developing: it has its own daily Groq budget. Switch to 120b for final runs.
AGENT_MODEL = "openai/gpt-oss-20b"
TOOLS = [search_job_posts]
MAX_REVISIONS = 1
MAX_EXTRA_SEARCHES = 2  # searches the writer may do itself, only while revising
# same idea as in citation_faithfulness.py: words that turn data into a generalization
GENERALIZING = re.compile(r"\b(most|typical|typically|common|commonly|consistently|many|usually|"
                          r"generally|often|all jobs|always)\b", re.IGNORECASE)
QUOTED = re.compile(r"[“\"][^”\"]*[”\"]")
CITE = re.compile(r"\[(\d+)\]")
DATA_CLAIM = re.compile(r"\d+\s*%|\b(half|majority|minority|percent)\b", re.IGNORECASE)
JOB_WORDS = re.compile(r"\b(posts?|roles?|jobs?|listings?|employers?|openings?)\b", re.IGNORECASE)


def _plain(text):
    # compare text loosely: lower case, dashes as spaces ("fault-tolerant" = "fault tolerant"),
    # one kind of apostrophe, single spaces
    text = re.sub(r"[-\u2010-\u2015]", " ", text.lower())
    return re.sub(r"\s+", " ", text.replace("’", "'")).strip()


def check_quotes(draft, skills):
    # every quoted example must (1) really be in the source it cites, as the writer saw it,
    # and (2) mention the skill it illustrates
    problems = []
    for line in draft.split("General advice")[0].splitlines():
        quotes = [q.strip("“”\"") for q in QUOTED.findall(line)]
        cites = [int(n) for n in CITE.findall(line)]
        if not quotes or not cites:
            continue
        # every excerpt of the cited posts that the writer was shown
        sources = " ".join(_plain(text) for n in cites if 1 <= n <= len(SOURCES)
                           for text in SOURCES[n - 1]["shown"])
        outside = _plain(QUOTED.sub("", line))
        named = [s for s in skills if re.search(rf"(?<!\w){re.escape(s.lower())}(?!\w)", outside)]
        for q in quotes:
            parts = [p.strip(" .,") for p in re.split(r"…|\.\.\.", _plain(q)) if len(p.strip()) >= 4]
            if any(part not in sources for part in parts):
                problems.append({"kind": "citation", "quote": q[:120],
                                 "issue": f"these words are not in source {cites}"})
            for skill in named:
                words = [w for w in re.findall(r"[\w/#+.]+", skill.lower()) if len(w) >= 3]
                if not any(w in _plain(q) for w in words):
                    problems.append({"kind": "citation", "quote": q[:120],
                                     "issue": f"the example does not mention {skill}"})
    return problems


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
- For each skill, an example from that phase's search results: quote a few words that
  mention the skill and cite the source number exactly like [3]. If none of that phase's
  results mention the skill, write "No example found in the searched posts."
- If the plan has NOTE lines, list them under "Notes". If it has none, leave Notes out.
Rules:
- Use only the plan's skills, phases and numbers. Never invent or change a number.
- Never say "most", "typical", "common" or "all jobs" in your own words; give the number instead.
- General advice that is NOT from the data goes under a final heading
  "General advice (not from the job data)". It must not contain numbers or claims about how
  many posts or roles ask for something (that belongs in the phases).
- Keep it under 350 words.
When revising, you may call search_job_posts (at most twice) to find a better example."""

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
    searches: int
    problems: list


def build_graph(llm, judge_llm):
    # The prompt alone did not stop the writer from searching again and again (online it hit
    # LangGraph's 25-step limit). So code decides: same tool, but tool_choice="none" forbids calling it.
    writer_can_search = llm.bind_tools(TOOLS)
    writer_no_search = llm.bind_tools(TOOLS, tool_choice="none")
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
        # code, not the LLM, decides the searches: one per phase, with all of the phase's
        # skills in the query, so keyword search finds posts that mention several of them
        plan = state["plan"]
        job = plan["title_keyword"] or plan["role_family"].replace("_", " ")
        parts = []
        for phase, skills in plan["phases"].items():
            if not skills:
                continue
            query = " ".join(s["skill"] for s in skills) + f" {job}"
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
        # first draft: no searching (the researcher already searched);
        # revision: at most MAX_EXTRA_SEARCHES, then it must write
        can_search = state["revisions"] > 0 and state["searches"] < MAX_EXTRA_SEARCHES
        model = writer_can_search if can_search else writer_no_search
        reply = model.invoke([SystemMessage(WRITER)] + state["messages"])
        if not reply.tool_calls:  # gpt-oss sometimes cites like 【3】: turn it into [3]
            reply.content = normalize_citations(reply.content)
        return {"messages": [reply], "searches": state["searches"] + len(reply.tool_calls)}

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
            print(f"  [critic] LLM check failed ({type(e).__name__}: {str(e)[:150]}), "
                  "using code checks only")
            problems = []

        # checks done by code, not by the LLM: they are free and never miss
        _, invalid, _ = check_citations(draft, len(SOURCES))
        for n in invalid:
            problems.append({"kind": "citation", "quote": f"[{n}]", "issue": "no such source"})
        # "rises"/"falls" only where the plan says so (the plan uses a 10-point rule)
        trends = {s["skill"]: s["trend"] for skills in state["plan"]["phases"].values()
                  for s in skills}
        problems += check_quotes(draft, list(trends))
        data_part = draft.split("General advice")[0]  # the labeled advice section may generalize
        for line in data_part.splitlines():
            own_words = QUOTED.sub("", line)  # words quoted from a job post are not our claim
            if GENERALIZING.search(own_words):
                problems.append({"kind": "comparison", "quote": line.strip()[:120],
                                 "issue": "generalizing word; give the number instead"})
            for word in ("rises", "falls"):
                if word not in own_words.lower():
                    continue
                for skill, trend in trends.items():
                    named = re.search(rf"(?<!\w){re.escape(skill)}(?!\w)", own_words, re.IGNORECASE)
                    if named and trend != word:
                        problems.append({"kind": "comparison", "quote": line.strip()[:120],
                                         "issue": f"the plan does not mark {skill} as '{word}' "
                                                  f"(it uses a {CHANGE}-point rule)"})

        # the advice section may generalize, but it must not make claims about the job data
        advice = draft.split("General advice", 1)[1] if "General advice" in draft else ""
        for line in advice.splitlines():
            if DATA_CLAIM.search(line) or (GENERALIZING.search(line) and JOB_WORDS.search(line)):
                problems.append({"kind": "outside_knowledge", "quote": line.strip()[:120],
                                 "issue": "general advice makes a claim about the job data; "
                                          "numbers belong in the phases"})

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


def generate_roadmap(request, llm=None, judge_llm=None, on_step=print):
    # runs the whole graph and RETURNS everything (the CLI, the API and the app all use this);
    # on_step gets a short text for each step, e.g. to print progress
    reset_sources()
    llm = llm or ChatGroq(model=AGENT_MODEL, temperature=0.2, max_tokens=1500,
                          reasoning_effort="low", max_retries=6)
    judge_llm = judge_llm or ChatGroq(model=AGENT_MODEL, temperature=0, max_tokens=2000,
                                      reasoning_effort="medium", max_retries=6)
    app = build_graph(llm, judge_llm)

    result = {"request": request, "intake": None, "plan": None, "plan_text": "",
              "roadmap": None, "problems": [], "steps": []}

    def step(text):
        result["steps"].append(text)
        on_step(text)

    start = {"request": request, "messages": [], "revisions": 0, "searches": 0, "problems": []}
    for update_by_node in app.stream(start, {"recursion_limit": 25}, stream_mode="updates"):
        for node, update in update_by_node.items():
            if node == "intake":
                result["intake"] = update["intake"]
                step(f"[intake] {update['intake']}")
            elif node == "planner":
                result["plan"], result["plan_text"] = update["plan"], update["plan_text"]
                step(f"[planner] plan based on {update['plan']['n_posts']} {update['plan']['group']}")
            elif node == "researcher":
                step("[researcher] one example search per phase done")
            elif node == "tools":
                step(f"[tools] {len(update['messages'])} extra search(es) during revision")
            elif node == "writer":
                msg = update["messages"][-1]
                if msg.tool_calls:
                    step(f"[writer] asked for {len(msg.tool_calls)} search(es)")
                else:
                    result["roadmap"] = msg.content
                    step("[writer] draft written")
            elif node == "critic":
                result["problems"] = update["problems"]
                sent_back = bool(update.get("messages"))
                step(f"[critic] {len(update['problems'])} problem(s)"
                     + (", sent back for one revision" if sent_back else ""))

    total, invalid, unused = check_citations(result["roadmap"] or "", len(SOURCES))
    result["citations"] = {"total": total, "invalid": invalid, "never_cited": unused}
    result["sources"] = [{"n": i, "title": p["title"], "company": p["company"],
                          "level": p["level"], "source": p["source"], "url": p.get("url")}
                         for i, p in enumerate(SOURCES, start=1)]
    return result


def print_result(result):
    print(f"\n[planner]\n{result['plan_text']}")
    print("\n=== FINAL ROADMAP ===")
    print(result["roadmap"])
    if result["problems"]:  # the last review still found something: show it, don't hide it
        print("\nReviewer notes (not fixed):")
        for p in result["problems"]:
            print(f"- [{p['kind']}] \"{p['quote'][:90]}\": {p['issue']}")
    c = result["citations"]
    print(f"\nCitations: {c['total']} | invalid numbers: {c['invalid'] or 'none'} "
          f"| sources never cited: {c['never_cited'] or 'none'}")
    print("\nSources:")
    for s in result["sources"]:
        print(f"  [{s['n']}] {s['title']} | {s['company']} | {s['url'] or 'no link'}")


if __name__ == "__main__":
    request = (" ".join(sys.argv[1:]) or
               "I know Python and Excel and I want a junior data analyst job. What should I learn?")
    print("REQUEST:", request, "\n")
    print_result(generate_roadmap(request))