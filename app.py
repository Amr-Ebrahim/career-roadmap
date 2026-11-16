# app.py - the web page (Streamlit).
# Two ways to run it:
#   Direct (default, also online):  streamlit run app.py
#       the page runs the agent itself, in one program
#   Through the API:                set ROADMAP_API_URL=http://127.0.0.1:8000
#       (start the API first with: uvicorn api:app --port 8000)   then: streamlit run app.py
import html
import os
import re
import threading

import requests
import streamlit as st
from dotenv import load_dotenv

load_dotenv()  # on the laptop; online, Streamlit turns the secrets into environment variables
API_URL = os.getenv("ROADMAP_API_URL")  # empty -> direct mode

EXAMPLES = {
    "📊 Data analyst": "I know Python and Excel and I want a junior data analyst job. What should I learn?",
    "☁️ DevOps engineer": "I know Linux and Python, I want a junior DevOps job",
    "🛠️ Help desk": "I want my first help desk job, I already know Windows and Active Directory",
}
FAMILY_NAMES = {"software": "Software", "backend": "Backend", "frontend": "Frontend",
                "mobile": "Mobile", "data": "Data", "ai_ml": "AI / ML",
                "devops_cloud": "DevOps / Cloud", "security": "Security",
                "networking_it": "Networking / IT", "qa": "QA / Testing",
                "architecture": "Architecture"}
PHASES = [("Foundations", "1", "Asked for most often at your level: learn these first"),
          ("Core skills", "2", "The next most requested skills"),
          ("Next level", "3", "Become more important as you get more senior")]


@st.cache_resource(show_spinner="Loading the job data and the agent (first start takes 1-2 minutes)...")
def load_agent():
    """Direct mode only. Runs once per server, then every visitor shares it.
    The data must be in place BEFORE roadmap_agent is imported: retrieval opens Chroma on import."""
    from hf_data import ensure_data
    ensure_data()
    from roadmap_agent import AGENT_MODEL, generate_roadmap
    return AGENT_MODEL, generate_roadmap, threading.Lock()  # lock: one roadmap at a time (Groq limits)


def build_roadmap(request_text):
    """Returns the result dict, the same shape in both modes. Errors are raised."""
    if API_URL:
        r = requests.post(f"{API_URL}/roadmap", json={"request": request_text}, timeout=300)
        if not r.ok:
            raise RuntimeError(f"API error {r.status_code}: {r.json().get('detail', r.text)}")
        return r.json()
    _, generate_roadmap, lock = load_agent()
    if not 10 <= len(request_text.strip()) <= 500:  # same rule the API checks
        raise ValueError("Please write between 10 and 500 characters.")
    with lock:
        return generate_roadmap(request_text, on_step=lambda text: st.write(text))


def goal_name(plan):
    job = plan["title_keyword"].title() if plan["title_keyword"] else \
        FAMILY_NAMES.get(plan["role_family"], plan["role_family"])
    return f"{plan['level'].title()}-level {job} job"


def roadmap_flowchart(plan):
    """Builds the flowchart as Graphviz DOT text: You today -> phase 1 -> 2 -> 3 -> Goal.
    Every number in it comes from the plan (code), not from the AI's text."""
    esc = html.escape  # skill names like "C#" or "R&D" must not break the HTML-style labels
    dot = [
        "digraph roadmap {",
        'rankdir=LR; compound=true; nodesep=0.22; ranksep=0.55; bgcolor="transparent";',
        'node [shape=box, style="rounded,filled", fontname="Helvetica", fontsize=12, '
        'color="#C7D2FE", fillcolor="white", fontcolor="#1F2937", penwidth=1.2, margin="0.2,0.1"];',
        'edge [color="#6366F1", penwidth=1.8, arrowsize=0.8];',
    ]

    # start: what the person already has
    have = "".join(f'<br/>✓ {esc(h["skill"])}' for h in plan["have"]) or "<br/>Starting from scratch"
    dot.append(f'start [label=<<b>YOU TODAY</b>{have}>, '
               'fillcolor="#ECFDF5", color="#10B981", fontcolor="#065F46"];')

    # one box (cluster) per phase, one node per skill
    prev, prev_cluster = "start", None
    for i, (name, number, _) in enumerate(PHASES, start=1):
        skills = plan["phases"].get(name, [])
        if not skills:
            continue
        cluster = f"cluster_{i}"
        dot.append(f"subgraph {cluster} {{")
        dot.append(f'label=<<b>{number} · {name}</b>>; style="rounded,filled"; fillcolor="#EEF2FF"; '
                   'color="#C7D2FE"; fontcolor="#312E81"; fontname="Helvetica"; fontsize=13; margin=12;')
        ids = []
        # left-to-right charts stack nodes bottom-up, so go in reverse: most asked ends up on top
        for j, s in reversed(list(enumerate(skills))):
            node = f"p{i}_{j}"
            ids.append(node)
            label = (f'<b>{esc(s["skill"])}</b>'
                     f'<br/><font point-size="10" color="#6B7280">in {s["share"]:.0f}% of posts</font>')
            extra = ""
            if s.get("trend") == "rises":
                _, senior = s["entry_to_senior"]
                label += f'<br/><font point-size="10" color="#7C3AED">↑ {senior:.0f}% at senior level</font>'
                extra = ', color="#8B5CF6", penwidth=1.8'
            dot.append(f"{node} [label=<{label}>{extra}];")
        dot.append("}")

        # one visible arrow between the boxes; invisible ones keep every skill in the same column
        middle = ids[len(ids) // 2]
        tail = f", ltail={prev_cluster}" if prev_cluster else ""
        dot.append(f"{prev} -> {middle} [lhead={cluster}{tail}];")
        for node in ids:
            if node != middle:
                dot.append(f"{prev} -> {node} [style=invis];")
        prev, prev_cluster = middle, cluster

    # goal
    dot.append(f'goal [label=<<font point-size="10">GOAL</font><br/><b>{esc(goal_name(plan))}</b>>, '
               'fillcolor="#4F46E5", color="#4F46E5", fontcolor="white"];')
    tail = f" [ltail={prev_cluster}]" if prev_cluster else ""
    dot.append(f"{prev} -> goal{tail};")
    dot.append("}")
    return "\n".join(dot)


st.set_page_config(page_title="Career Roadmap Builder", page_icon="🧭", layout="wide")

# ---------------- sidebar: status and how it works ----------------
with st.sidebar:
    st.markdown("## 🧭 Career Roadmap Builder")
    if API_URL:
        try:
            health = requests.get(f"{API_URL}/health", timeout=3).json()
            st.success(f"API running · {health['model']}", icon=":material/check_circle:")
        except requests.RequestException:
            st.error("API not running. Start it with:\n\n`uvicorn api:app --port 8000`",
                     icon=":material/error:")
    else:
        try:
            model, _, _ = load_agent()
            st.success(f"Ready · {model}", icon=":material/check_circle:")
        except Exception as e:
            st.error(f"Could not load the data or the agent: {type(e).__name__}: {str(e)[:200]}",
                     icon=":material/error:")
    st.markdown("#### How it works")
    st.markdown(
        "1. **Intake** reads what you want and what you know\n"
        "2. **Planner** counts skills across all matching job posts\n"
        "3. **Researcher** finds real posts as examples\n"
        "4. **Writer** turns it into a roadmap\n"
        "5. **Critic** checks every number and quote")
    st.caption("Data: LinkedIn posts (April 2024) and Arbeitnow posts (since October 2026). "
               "Numbers come from code, not from the AI.")

# ---------------- input ----------------
st.title("Plan your path into tech")
st.markdown("Tell us the job you want and what you already know. "
            "You get a roadmap built from **real job posts**, with the numbers to back it up.")


def use_example():
    choice = st.session_state.get("example")
    if choice:
        st.session_state["request"] = EXAMPLES[choice]


if "request" not in st.session_state:
    st.session_state["request"] = EXAMPLES["📊 Data analyst"]

with st.container(border=True):
    st.pills("Try an example", list(EXAMPLES), key="example", on_change=use_example)
    st.text_area("Your goal", key="request", height=90,
                 placeholder="e.g. I know Python and SQL and I want a junior data engineer job")
    build = st.button("Build my roadmap", type="primary", icon=":material/route:")

if build:
    with st.status("Building your roadmap (about a minute)...", expanded=True) as status:
        try:
            st.session_state["result"] = build_roadmap(st.session_state["request"])
            status.update(label="Roadmap ready", state="complete", expanded=False)
        except Exception as e:
            status.update(label="Something went wrong", state="error", expanded=True)
            st.error(f"Could not build a roadmap: {type(e).__name__}: {str(e)[:300]}")

# ---------------- result ----------------
result = st.session_state.get("result")
if result and result.get("roadmap"):
    i, plan = result["intake"], result["plan"]

    st.divider()
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Role", FAMILY_NAMES.get(i["role_family"], i["role_family"]), border=True)
    c2.metric("Level", i["level"].title(), border=True)
    c3.metric("Job title filter", plan["title_keyword"] or "none", border=True)
    c4.metric("Job posts analyzed", plan["n_posts"], border=True)

    if plan["have"]:
        with st.container(horizontal=True, vertical_alignment="center"):
            st.markdown("**You already have:**")
            for h in plan["have"]:
                st.badge(f"{h['skill']} · {h['share']:.0f}%", icon=":material/check:", color="green")
    for note in plan["notes"]:
        st.info(note, icon=":material/info:")

    # the plan, drawn from the numbers (not from the AI's text): as a flowchart or as cards
    with st.container(horizontal=True, vertical_alignment="bottom"):
        st.subheader("Your roadmap")
        view = st.segmented_control("View", ["Flowchart", "Cards"], default="Flowchart",
                                    key="view", label_visibility="collapsed")

    if view == "Cards":
        for col, (name, number, hint) in zip(st.columns(3), PHASES):
            with col.container(border=True):
                st.markdown(f"### {number} · {name}")
                st.caption(hint)
                skills = plan["phases"].get(name, [])
                if not skills:
                    st.caption("Nothing extra in this phase.")
                for s in skills:
                    st.progress(min(s["share"] / 100, 1.0),
                                text=f"**{s['skill']}** · in {s['share']:.0f}% of posts")
                    if s.get("trend") == "rises":
                        _, senior = s["entry_to_senior"]
                        st.badge(f"rises to {senior:.0f}% at senior level",
                                 icon=":material/trending_up:", color="violet")
    else:
        with st.container(border=True):
            st.graphviz_chart(roadmap_flowchart(plan), width="stretch")
            st.caption(f"% = share of the {plan['n_posts']} job posts that ask for the skill. "
                       "↑ = asked for much more often at senior level.")

    cited = {int(n) for n in re.findall(r"\[(\d+)\]", result["roadmap"])}
    tab_text, tab_sources, tab_how = st.tabs(
        ["📝 Written roadmap", f"🔎 Sources ({len(cited)})", "⚙️ How it was made"])

    with tab_text:
        if result["problems"]:
            notes = "\n".join(f"- {p['issue']}: “{p['quote'][:100]}”" for p in result["problems"])
            st.warning(f"**Reviewer notes (not fixed):**\n{notes}", icon=":material/rate_review:")
        with st.container(border=True):
            st.markdown(result["roadmap"])
        # the same text as a file: the roadmap, then the numbered sources it cites
        source_list = "\n".join(f"[{s['n']}] {s['title']} - {s['company']} ({s['url'] or 'no link'})"
                                for s in result["sources"] if s["n"] in cited)
        st.download_button("Download roadmap (.md)",
                           data=f"# My roadmap: {goal_name(plan)}\n\n{result['roadmap']}"
                                f"\n\n## Sources\n{source_list}\n",
                           file_name="my_roadmap.md", mime="text/markdown",
                           icon=":material/download:")

    with tab_sources:
        def source_line(s):
            title = f"{s['title']} – {s['company']}"
            link = f"[{title}]({s['url']})" if s["url"] else title
            return f"**[{s['n']}]** {link}  \n:gray[{s['level']} · {s['source']}]"

        for s in result["sources"]:
            if s["n"] in cited:
                st.markdown(source_line(s))
        others = [s for s in result["sources"] if s["n"] not in cited]
        if others:
            with st.expander(f"Searched but not cited ({len(others)})"):
                for s in others:
                    st.markdown(source_line(s))

    with tab_how:
        st.markdown("**The plan, computed in code from the job posts:**")
        st.code(result["plan_text"], language=None)
        st.markdown("**Steps:**")
        st.code("\n".join(result["steps"]), language=None)
        c = result["citations"]
        st.caption(f"Citations: {c['total']} · invalid: {c['invalid'] or 'none'}")