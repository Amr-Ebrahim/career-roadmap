# app.py - the web page (Streamlit).
# Two ways to run it:
#   Direct (default, also online):  streamlit run app.py
#       the page runs the agent itself, in one program
#   Through the API:                set ROADMAP_API_URL=http://127.0.0.1:8000
#       (start the API first with: uvicorn api:app --port 8000)   then: streamlit run app.py
import ast
import html
import os
import random
import re
import threading
import time
from datetime import datetime

import requests
import streamlit as st
from dotenv import load_dotenv

load_dotenv()  # on the laptop; online, Streamlit turns the secrets into environment variables
API_URL = os.getenv("ROADMAP_API_URL")  # empty -> direct mode

AUTHOR = "Amr Ebrahim"
AUTHOR_URL = "https://github.com/Amr-Ebrahim"

EXAMPLES = {
    "Data analyst": "I know Python and Excel and I want a junior data analyst job. What should I learn?",
    "DevOps engineer": "I know Linux and Python, I want a junior DevOps job",
    "Help desk": "I want my first help desk job, I already know Windows and Active Directory",
}
FAMILY_NAMES = {"software": "Software", "backend": "Backend", "frontend": "Frontend",
                "mobile": "Mobile", "data": "Data", "ai_ml": "AI / ML",
                "devops_cloud": "DevOps / Cloud", "security": "Security",
                "networking_it": "Networking / IT", "qa": "QA / Testing",
                "architecture": "Architecture"}
PHASES = [("Foundations", "1", "Asked for most often at your level: learn these first"),
          ("Core skills", "2", "The next most requested skills"),
          ("Next level", "3", "Become more important as you get more senior")]

# the five agents: name, icon, what kind of worker it is, what it does while you wait
AGENTS = {
    "intake": ("Intake", ":material/hearing:", "AI", "is reading your goal"),
    "planner": ("Planner", ":material/calculate:", "counts in code", "is counting skills in the job posts"),
    "researcher": ("Researcher", ":material/travel_explore:", "searches in code",
                   "is finding real posts as examples"),
    "writer": ("Writer", ":material/edit_note:", "AI", "is writing your roadmap"),
    "critic": ("Critic", ":material/fact_check:", "AI, checked by code",
               "is checking every number and quote"),
}
AGENTS["tools"] = AGENTS["researcher"]
NEXT = {"intake": "planner", "planner": "researcher", "researcher": "writer",
        "writer": "critic", "tools": "writer"}

CSS = """
<style>
/* Colors come from the text color (currentColor), which Streamlit switches with the theme:
   the page does not rerun when someone picks light or dark, so CSS has to adapt by itself. */
:root { --marker:#FFE066; --pen:#1F4FD8; --ink-on-marker:#1B2A41; }
.hero h1 { font-family: Archivo, sans-serif; font-stretch: 72%; font-weight: 800;
           font-size: clamp(2.6rem, 5.2vw, 4.4rem); line-height: .96; letter-spacing: -.01em;
           margin: .4rem 0 1.1rem; padding: 0; text-wrap: balance; color: inherit; }
.hero .lede { font-size: 1.15rem; line-height: 1.55; max-width: 32em; margin: 0 0 1rem; }
.hero .lede b { font-weight: 700; }
mark.found { color: var(--ink-on-marker); padding: 0 .12em; border-radius: 2px;
             background-image: linear-gradient(var(--marker), var(--marker));
             background-repeat: no-repeat; background-position: 0 70%; background-size: 100% 72%;
             background-color: transparent; animation: sweep .45s ease-out both; }
@keyframes sweep { from { background-size: 0% 72%; } to { background-size: 100% 72%; } }
.clip { background: color-mix(in srgb, currentColor 4%, transparent);
        border: 1px solid color-mix(in srgb, currentColor 14%, transparent); border-radius: 6px;
        padding: 1.15rem 1.3rem 1rem; transform: rotate(-.6deg);
        box-shadow: 0 18px 30px -24px rgba(0,0,0,.45); }
.clip .meta, .clip .foot, .legend, .typing, .footer { color: color-mix(in srgb, currentColor 68%, transparent); }
.clip .meta { font-size: .85rem; margin-bottom: .55rem; }
.clip .meta b, .typing b, .footer .who { color: currentColor; }
.clip .meta b { font-weight: 600; }
.clip .body { font-size: .98rem; line-height: 1.65; }
.clip .foot { border-top: 1px dashed color-mix(in srgb, currentColor 18%, transparent);
              margin-top: .8rem; padding-top: .6rem; font-size: .85rem; }
.legend { font-size: .9rem; line-height: 1.9; }
.legend .q { border-bottom: 2px dotted color-mix(in srgb, var(--pen) 70%, currentColor); }
.tag { font-size: .75rem; padding: .1rem .45rem; border-radius: 99px; margin-left: .35rem;
       border: 1px solid color-mix(in srgb, currentColor 20%, transparent); font-weight: 500;
       white-space: nowrap; color: color-mix(in srgb, currentColor 70%, transparent); }
.tag.code { background: var(--marker); border-color: #E8C93A; color: var(--ink-on-marker); }
.typing { font-size: .95rem; padding: .3rem 0 .2rem .2rem; }
.typing i { display: inline-block; width: .32rem; height: .32rem; margin-left: .18rem;
            border-radius: 50%; background: currentColor; animation: blink 1.2s infinite both; }
.typing i:nth-child(2) { animation-delay: .2s; } .typing i:nth-child(3) { animation-delay: .4s; }
@keyframes blink { 0%, 80%, 100% { opacity: .2; } 40% { opacity: 1; } }
.goal { font-family: Archivo, sans-serif; font-stretch: 80%; font-weight: 800; font-size: 2rem;
        line-height: 1.1; margin: .2rem 0 .3rem; }
.footer { border-top: 1px solid color-mix(in srgb, currentColor 14%, transparent); margin-top: 3rem;
          padding-top: 1.2rem; font-size: .9rem; line-height: 1.7; }
.footer a { color: color-mix(in srgb, var(--pen) 70%, currentColor); }
.footer .who { font-size: 1rem; }

/* agent messages slide in as each agent finishes */
[data-testid="stChatMessage"] { animation: arrive .35s ease-out both; }
@keyframes arrive { from { opacity: 0; transform: translateY(8px); } to { opacity: 1; transform: none; } }

/* the flowchart: theme-aware colors + the learning order revealing itself step by step */
[data-testid="stGraphVizChart"] svg text[fill="#1B2A41" i] { fill: currentColor; }
[data-testid="stGraphVizChart"] svg text[fill="#5F6673" i] { fill: color-mix(in srgb, currentColor 65%, transparent); }
[data-testid="stGraphVizChart"] svg text[fill="#1F4FD8" i] { fill: color-mix(in srgb, #1F4FD8 60%, currentColor); }
[data-testid="stGraphVizChart"] svg text[fill="#9A6700" i] { fill: color-mix(in srgb, #B7950B 70%, currentColor); }
[data-testid="stGraphVizChart"] svg [fill="#FFFFFF" i] { fill: color-mix(in srgb, currentColor 5%, transparent); }
[data-testid="stGraphVizChart"] svg [fill="#F1F2EC" i] { fill: transparent; }
[data-testid="stGraphVizChart"] svg [stroke="#C9CBBE" i], [data-testid="stGraphVizChart"] svg [stroke="#DCDDD2" i]
  { stroke: color-mix(in srgb, currentColor 28%, transparent); }
[data-testid="stGraphVizChart"] svg [stroke="#1B2A41" i] { stroke: currentColor; }
[data-testid="stGraphVizChart"] svg [fill="#1B2A41" i] { fill: currentColor; }
[data-testid="stGraphVizChart"] svg g.node, [data-testid="stGraphVizChart"] svg g.edge
  { animation: arrive .4s ease-out both; }
[data-testid="stGraphVizChart"] svg g.edge { animation-name: fade; animation-delay: 1.6s; }
@keyframes fade { from { opacity: 0; } to { opacity: 1; } }
STEP_DELAYS

@media (prefers-reduced-motion: reduce) {
  mark.found, .typing i, [data-testid="stChatMessage"],
  [data-testid="stGraphVizChart"] svg g.node, [data-testid="stGraphVizChart"] svg g.edge { animation: none; }
}
@media (max-width: 640px) { .clip { transform: none; } }
</style>
""".replace("STEP_DELAYS", "\n".join(  # step 1 appears first, then 2, 3... (the learning order)
    f'[data-testid="stGraphVizChart"] svg g.s{n} {{ animation-delay: {0.15 + 0.11 * n:.2f}s; }}'
    for n in range(0, 25)))


@st.cache_resource(show_spinner="Loading the job data and the agent (first start takes 1-2 minutes)...")
def load_agent():
    """Direct mode only. Runs once per server, then every visitor shares it.
    The data must be in place BEFORE roadmap_agent is imported: retrieval opens Chroma on import."""
    from hf_data import ensure_data
    ensure_data()
    import retrieval
    import skill_matcher
    import stats_tool
    from roadmap_agent import AGENT_MODEL, generate_roadmap
    return {"model": AGENT_MODEL, "generate": generate_roadmap,
            "lock": threading.Lock(),  # one roadmap at a time (Groq limits)
            "n_posts": len(stats_tool._df), "collection": retrieval._collection,
            "patterns": skill_matcher.PATTERNS}


def highlight(text, patterns):
    """Wraps every skill the matcher finds in <mark>: the same matcher that counts the skills."""
    # longest match first at the same start: "GitHub Actions" wins over "Git"
    spans = sorted((m.start(), -m.end()) for _, p in patterns for m in p.finditer(text))
    spans = [(start, -neg_end) for start, neg_end in spans]
    out, pos, n = [], 0, 0
    for start, end in spans:
        if start < pos:  # overlaps a mark already placed (e.g. "Spring" inside "Spring Boot")
            continue
        out.append(html.escape(text[pos:start]))
        out.append(f'<mark class="found" style="animation-delay:{.35 + .12 * n:.2f}s">'
                   f'{html.escape(text[start:end])}</mark>')
        pos, n = end, n + 1
    out.append(html.escape(text[pos:]))
    return "".join(out), n


def sample_post(agent, tries=15):
    """A random real post excerpt with at least 3 skills in it, for the hero."""
    col = agent["collection"]
    for _ in range(tries):
        got = col.get(offset=random.randrange(col.count()), limit=1, include=["documents", "metadatas"])
        meta, doc = got["metadatas"][0], got["documents"][0].split("\n", 1)[-1]
        first = min((m.start() for _, p in agent["patterns"] for m in p.finditer(doc)), default=None)
        if first is None:
            continue
        start = doc.rfind(" ", 0, max(0, first - 110)) + 1
        cut = len(doc) > start + 430  # is the end of the post cut off?
        window = doc[start:start + 430]
        window = window[:window.rfind(" ")].rstrip(" ,.;:") if cut else window
        marked, n = highlight(window, agent["patterns"])
        if n >= 3:
            return {"meta": meta, "html": ("…" if start else "") + marked + ("…" if cut else ""), "n": n}
    return None


def share_text(s):
    return f"in {s['share']:.0f}% of posts" if s["share"] >= 0.5 else "not asked in these posts"


def goal_name(plan):
    job = plan["title_keyword"].title() if plan["title_keyword"] else \
        FAMILY_NAMES.get(plan["role_family"], plan["role_family"])
    return f"{plan['level'].title()}-level {job} job"


def friendly(node, text, seen):
    """Turns one agent step into what that agent would say."""
    body = text.split("] ", 1)[-1]
    if node == "intake":
        try:
            d = ast.literal_eval(body)
        except (ValueError, SyntaxError):
            return body
        job = d["title_keyword"] or FAMILY_NAMES.get(d["role_family"], d["role_family"])
        known = (f"You already know {', '.join(d['known_skills'])}." if d["known_skills"]
                 else "You're starting from scratch.")
        return f"You're aiming for an {d['level']}-level **{job}** job. {known}"
    if node == "planner":
        for key, name in FAMILY_NAMES.items():  # "devops_cloud posts" -> "DevOps / Cloud posts"
            body = body.replace(f" {key} posts", f" {name} posts")
        return (f"I counted every skill in {body.replace('plan based on ', '')}. "
                "Every percentage you'll see comes from those posts.")
    if node == "researcher":
        return "I pulled real job posts as examples for each phase of the plan."
    if node == "tools":
        return "Here are more posts to choose an example from."
    if node == "writer":
        if "search" in body:
            return "I need a better example. Searching the job posts again."
        return "Draft written from the plan's numbers. Over to the critic." if seen.count("writer") == 0 \
            else "The fixed draft is ready."
    if node == "critic":
        n = int(re.match(r"\d+", body).group()) if re.match(r"\d+", body) else 0
        if "sent back" in body:
            return f"Found {n} thing{'s' * (n != 1)} to fix. Sending it back to the writer."
        if n == 0:
            return "Every number and quote checks out against the job posts."
        return f"{n} note{'s' * (n != 1)} left. I'll show {'them' if n != 1 else 'it'} next to the roadmap."
    return body


def say(node, message):
    name, icon, kind, _ = AGENTS[node]
    with st.chat_message(name, avatar=icon):
        tag_class = "tag code" if "code" in kind else "tag"
        st.html(f"<b>{name}</b><span class='{tag_class}'>{kind}</span>")
        st.markdown(message)


def typing(node):
    name, _, _, doing = AGENTS[node]
    return f"<div class='typing'><b>{name}</b> {doing}<i></i><i></i><i></i></div>"


def run_with_chat(request_text, box):
    """Builds the roadmap while the agents 'talk' in the box. Returns (result, chat)."""
    chat, seen = [], []
    with box:
        waiting = st.empty()
    waiting.html(typing("intake"))

    def on_step(text):
        nonlocal waiting
        node = text[1:text.index("]")] if text.startswith("[") else ""
        if node not in AGENTS:
            return
        message = friendly(node, text, seen)
        seen.append(node)
        chat.append((node, message))
        waiting.empty()
        with box:
            say(node, message)
            waiting = st.empty()
        nxt = "writer" if (node == "critic" and "sent back" in text) else NEXT.get(node)
        if nxt:
            waiting.html(typing(nxt))

    if API_URL:
        r = requests.post(f"{API_URL}/roadmap", json={"request": request_text}, timeout=300)
        if not r.ok:
            raise RuntimeError(f"API error {r.status_code}: {r.json().get('detail', r.text)}")
        result = r.json()
        for step in result["steps"]:  # replay the steps so the conversation still shows
            on_step(step)
            time.sleep(0.35)
    else:
        agent = load_agent()
        if not 10 <= len(request_text.strip()) <= 500:  # same rule the API checks
            raise ValueError("Please write between 10 and 500 characters.")
        with agent["lock"]:
            result = agent["generate"](request_text, on_step=on_step)
    waiting.empty()
    return result, chat


def mark_numbers(text):
    """Percentages in the AI's text come from the plan: mark them like the data."""
    return re.sub(r"(?<![\w.])(\d{1,3}(?:\.\d)?\s?%)", r'<mark class="found">\1</mark>', text)


def roadmap_flowchart(plan):
    """Builds the flowchart as Graphviz DOT text: You today -> phase 1 -> 2 -> 3 -> Goal.
    Every number in it comes from the plan (code), not from the AI's text."""
    esc = html.escape  # skill names like "C#" or "R&D" must not break the HTML-style labels
    dot = [
        "digraph roadmap {",
        'rankdir=LR; compound=true; nodesep=0.22; ranksep=0.55; bgcolor="transparent";',
        'node [shape=box, style="rounded,filled", fontname="Helvetica", fontsize=12, '
        'color="#C9CBBE", fillcolor="#FFFFFF", fontcolor="#1B2A41", penwidth=1.2, margin="0.16,0.08"];',
        'edge [color="#1B2A41", penwidth=1.6, arrowsize=0.8];',
    ]

    have = "".join(f'<br/>✓ {esc(h["skill"])}' for h in plan["have"]) or "<br/>Starting from scratch"
    dot.append(f'start [label=<<b>YOU TODAY</b>{have}>, color="#1B2A41", class="s0"];')

    prev, prev_cluster = "start", None
    for i, (name, number, _) in enumerate(PHASES, start=1):
        skills = plan["phases"].get(name, [])
        if not skills:
            continue
        cluster = f"cluster_{i}"
        dot.append(f"subgraph {cluster} {{")
        dot.append(f'label=<<b>{number} · {name}</b>>; style="rounded,filled"; fillcolor="#F1F2EC"; '
                   'color="#DCDDD2"; fontcolor="#1B2A41"; fontname="Helvetica"; fontsize=13; margin=12;')
        ids = []
        # left-to-right charts stack nodes bottom-up, so go in reverse: step 1 ends up on top
        for j, s in reversed(list(enumerate(skills))):
            node = f"p{i}_{j}"
            ids.append(node)
            step = f'{s["step"]} · ' if s.get("step") else ""
            rows = [f'<tr><td><b>{step}{esc(s["skill"])}</b></td></tr>',
                    # the yellow cell = counted from job posts, same meaning as on the rest of the page
                    # its text color is set on purpose (#1B2A40): the CSS recolors #1B2A41 for dark mode,
                    # but text on yellow must stay dark
                    f'<tr><td bgcolor="#FFE066"><font point-size="10" color="#1B2A40">{share_text(s)}</font></td></tr>']
            extra = ""
            if s.get("trend") == "rises":
                _, senior = s["entry_to_senior"]
                rows.append(f'<tr><td><font point-size="10" color="#1F4FD8">'
                            f'↑ {senior:.0f}% at senior level</font></td></tr>')
                extra = ', color="#1F4FD8", penwidth=1.8'
            for key in ("or", "includes"):  # pick-one / same-topic groups
                if s.get(key):
                    others = ", ".join(f'{esc(o["skill"])} {o["share"]:.0f}%' for o in s[key])
                    rows.append(f'<tr><td><font point-size="10" color="#5F6673">{key} {others}</font></td></tr>')
            if s.get("added_for"):  # a prerequisite the plan added: dashed border
                rows.append(f'<tr><td><font point-size="10" color="#9A6700">'
                            f'needed for {esc(s["added_for"])}</font></td></tr>')
                extra += ', style="rounded,filled,dashed", color="#B7950B"'
            elif s.get("after"):
                rows.append(f'<tr><td><font point-size="10" color="#5F6673">'
                            f'after {esc(", ".join(s["after"]))}</font></td></tr>')
            table = '<table border="0" cellborder="0" cellspacing="1" cellpadding="1">' + "".join(rows) + "</table>"
            dot.append(f'{node} [label=<{table}>, class="s{s.get("step", 0)}"{extra}];')
        dot.append("}")

        # one visible arrow between the boxes; invisible ones keep every skill in the same column
        middle = ids[len(ids) // 2]
        tail = f", ltail={prev_cluster}" if prev_cluster else ""
        dot.append(f"{prev} -> {middle} [lhead={cluster}{tail}];")
        for node in ids:
            if node != middle:
                dot.append(f"{prev} -> {node} [style=invis];")
        prev, prev_cluster = middle, cluster

    last = max((s.get("step", 0) for skills in plan["phases"].values() for s in skills), default=0)
    dot.append(f'goal [label=<<font point-size="10">GOAL</font><br/><b>{esc(goal_name(plan))}</b>>, '
               f'fillcolor="#1F4FD8", color="#1F4FD8", fontcolor="#FFFFFE", class="s{last + 1}"];')
    tail = f" [ltail={prev_cluster}]" if prev_cluster else ""
    dot.append(f"{prev} -> goal{tail};")
    dot.append("}")
    return "\n".join(dot)


st.set_page_config(page_title="Career Roadmap Builder", page_icon="🧭", layout="wide")
st.html(CSS)

agent, load_error = None, None
if not API_URL:
    try:
        agent = load_agent()
    except Exception as e:
        load_error = f"{type(e).__name__}: {str(e)[:200]}"

# ---------------- hero: a real job post, read the way the planner reads it ----------------
n_posts = f"{agent['n_posts']:,}" if agent else "thousands of"
left, right = st.columns([1.15, 1], gap="large", vertical_alignment="center")
with left:
    st.html(f"""<div class="hero">
      <h1>Learn what tech jobs actually ask for.</h1>
      <p class="lede">Tell it the job you want and what you already know. You get a learning
      roadmap where <b>every number is counted from {n_posts} real job posts</b>.
      The AI writes the words. It doesn't make up the data.</p>
    </div>""")
with right:
    if agent:
        if "sample" not in st.session_state:
            st.session_state["sample"] = sample_post(agent)
        post = st.session_state["sample"]
        if post:
            meta = post["meta"]
            date = datetime.fromtimestamp(meta["posted_ts"]).strftime("%b %Y")
            st.html(f"""<div class="clip">
              <div class="meta"><b>{html.escape(meta['title'])}</b> at {html.escape(meta['company'])},
              {date}</div>
              <div class="body">{post['html']}</div>
              <div class="foot">One of {n_posts} posts. The highlighted words are the {post['n']} skill
              mentions the planner counted here.</div></div>""")
            if st.button("Show another post", type="tertiary", icon=":material/refresh:"):
                st.session_state["sample"] = sample_post(agent)
                st.rerun()
    elif load_error:
        st.error(f"Could not load the job data: {load_error}", icon=":material/error:")

# ---------------- input ----------------
def use_example():
    choice = st.session_state.get("example")
    if choice:
        st.session_state["request"] = EXAMPLES[choice]


if "request" not in st.session_state:
    st.session_state["request"] = EXAMPLES["Data analyst"]

st.write("")
with st.container(border=True):
    st.text_area("What job do you want, and what do you already know?", key="request", height=90,
                 placeholder="e.g. I know Python and SQL and I want a junior data engineer job")
    with st.container(horizontal=True, vertical_alignment="center"):
        build = st.button("Build my roadmap", type="primary", icon=":material/route:")
        st.pills("Or try", list(EXAMPLES), key="example", on_change=use_example,
                 label_visibility="collapsed")

if build:
    st.subheader("The agents at work")
    box = st.container(border=True)
    try:
        result, chat = run_with_chat(st.session_state["request"], box)
        result["chat"] = chat
        st.session_state["result"] = result
    except Exception as e:
        st.error(f"Could not build a roadmap: {type(e).__name__}: {str(e)[:300]}",
                 icon=":material/error:")

# ---------------- result ----------------
result = st.session_state.get("result")
if result and result.get("roadmap"):
    i, plan = result["intake"], result["plan"]

    st.divider()
    st.html(f"<div class='goal'>Your roadmap: {html.escape(goal_name(plan))}</div>")
    st.html("<div class='legend'><mark class='found'>44%</mark> counted from real job posts. "
            "<span class='q'>“quoted”</span> [n] copied word for word from a post. "
            "Everything else is written by AI and checked against both.</div>")

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Role", FAMILY_NAMES.get(i["role_family"], i["role_family"]), border=True)
    c2.metric("Level", i["level"].title(), border=True)
    c3.metric("Job title filter", plan["title_keyword"] or "none", border=True)
    c4.metric("Job posts counted", plan["n_posts"], border=True)

    if plan["have"]:
        with st.container(horizontal=True, vertical_alignment="center"):
            st.markdown("**You already have:**")
            for h in plan["have"]:
                st.badge(f"{h['skill']} {h['share']:.0f}%", icon=":material/check:", color="green")
    for note in plan["notes"]:
        st.info(note, icon=":material/info:")

    with st.container(horizontal=True, vertical_alignment="bottom"):
        st.subheader("Your learning order")
        view = st.segmented_control("View", ["Flowchart", "Cards"], default="Flowchart",
                                    key="view", label_visibility="collapsed")

    if view == "Cards":
        for col, (name, number, hint) in zip(st.columns(3), PHASES):
            with col.container(border=True):
                st.markdown(f"#### {number} · {name}")
                st.caption(hint)
                skills = plan["phases"].get(name, [])
                if not skills:
                    st.caption("Nothing extra in this phase.")
                for s in skills:
                    step = f"{s['step']}. " if s.get("step") else ""
                    st.progress(min(s["share"] / 100, 1.0),
                                text=f"**{step}{s['skill']}**, {share_text(s)}")
                    if s.get("trend") == "rises":
                        _, senior = s["entry_to_senior"]
                        st.badge(f"rises to {senior:.0f}% at senior level",
                                 icon=":material/trending_up:", color="blue")
                    for key in ("or", "includes"):
                        if s.get(key):
                            st.caption(f"{key} " + ", ".join(f"{o['skill']} ({o['share']:.0f}%)"
                                                             for o in s[key]))
                    if s.get("added_for"):
                        st.badge(f"needed for {s['added_for']}", icon=":material/link:",
                                 color="orange")
                    elif s.get("after"):
                        st.caption(f"Learn after {', '.join(s['after'])}")
    else:
        with st.container(border=True):
            st.graphviz_chart(roadmap_flowchart(plan), width="stretch")
            st.caption("Numbers give the learning order: what a skill needs comes first (from a "
                       "prerequisite list, not the job data). Yellow = share of posts that ask for "
                       "the skill. Blue = asked for much more at senior level. Dashed = added because "
                       "a later skill needs it. \"or\" = pick one; \"includes\" = learning it covers the other.")

    cited = {int(n) for n in re.findall(r"\[(\d+)\]", result["roadmap"])}
    tab_text, tab_sources, tab_how = st.tabs(
        ["Written roadmap", f"Job posts cited ({len(cited)})", "How the agents worked"])

    with tab_text:
        if result["problems"]:
            notes = "\n".join(f"- {p['issue']}: “{p['quote'][:100]}”" for p in result["problems"])
            st.warning(f"**The critic left these notes:**\n{notes}", icon=":material/rate_review:")
        with st.container(border=True):
            st.markdown(mark_numbers(result["roadmap"]), unsafe_allow_html=True)
        source_list = "\n".join(f"[{s['n']}] {s['title']} - {s['company']} ({s['url'] or 'no link'})"
                                for s in result["sources"] if s["n"] in cited)
        st.download_button("Download roadmap (.md)",
                           data=f"# My roadmap: {goal_name(plan)}\n\n{result['roadmap']}"
                                f"\n\n## Sources\n{source_list}\n",
                           file_name="my_roadmap.md", mime="text/markdown",
                           icon=":material/download:")

    with tab_sources:
        def source_line(s):
            title = f"{s['title']} at {s['company']}"
            link = f"[{title}]({s['url']})" if s["url"] else title
            return f"**[{s['n']}]** {link}  \n:gray[{s['level']} level, {s['source']}]"

        for s in result["sources"]:
            if s["n"] in cited:
                st.markdown(source_line(s))
        others = [s for s in result["sources"] if s["n"] not in cited]
        if others:
            with st.expander(f"Searched but not cited ({len(others)})"):
                for s in others:
                    st.markdown(source_line(s))

    with tab_how:
        for node, message in result.get("chat", []):
            say(node, message)
        with st.expander("The plan as the writer saw it, computed in code"):
            st.code(result["plan_text"], language=None)
        c = result["citations"]
        st.caption(f"Citations: {c['total']}. Invalid source numbers: {c['invalid'] or 'none'}.")

# ---------------- footer ----------------
model = agent["model"] if agent else "gpt-oss on Groq"
st.html(f"""<div class="footer">
  <div class="who">Designed and built by <a href="{AUTHOR_URL}" target="_blank">{AUTHOR}</a>.</div>
  Job data: the LinkedIn job postings dataset on Kaggle (April 2024) and the Arbeitnow job board API
  (refreshed weekly since October 2026). Skills are counted by a dictionary matcher, the plan and its
  order are computed in code, and the text is written by {html.escape(model)} on Groq.
</div>""")
