# app.py - the web page (Streamlit). It only talks to the API, it never runs the agent itself.
# Start the API first (uvicorn api:app --port 8000), then:  streamlit run app.py
import requests
import streamlit as st

API_URL = "http://127.0.0.1:8000"
EXAMPLES = [
    "I know Python and Excel and I want a junior data analyst job. What should I learn?",
    "I know Linux and Python, I want a junior DevOps job",
    "I want my first help desk job, I already know Windows and Active Directory",
]

st.set_page_config(page_title="Career Roadmap Builder", page_icon="🧭")
st.title("🧭 Career Roadmap Builder")
st.caption("Roadmaps from real job posts: the numbers come from all matching posts, "
           "the examples are quoted from real posts and checked.")

with st.sidebar:
    st.header("API")
    try:
        health = requests.get(f"{API_URL}/health", timeout=3).json()
        st.success(f"Running ({health['model']})")
    except requests.RequestException:
        st.error("Not running. Start it with:\n\n`uvicorn api:app --port 8000`")

choice = st.selectbox("Try an example, or write your own below", EXAMPLES)
request = st.text_area("What job do you want, and what do you already know?", value=choice, height=90)

if st.button("Build my roadmap", type="primary"):
    with st.spinner("Reading job posts, planning, writing and checking (about a minute)..."):
        try:
            r = requests.post(f"{API_URL}/roadmap", json={"request": request}, timeout=300)
            if r.ok:
                st.session_state["result"] = r.json()
            else:
                detail = r.json().get("detail", r.text)
                st.error(f"The API could not build a roadmap ({r.status_code}): {detail}")
        except requests.RequestException as e:
            st.error(f"Could not reach the API: {e}")

result = st.session_state.get("result")
if result and result.get("roadmap"):
    i = result["intake"]
    known = ", ".join(i["known_skills"]) or "nothing listed"
    keyword = f", titles with '{i['title_keyword']}'" if i["title_keyword"] else ""
    st.info(f"Understood: **{i['role_family']}**, **{i['level']}** level{keyword}. You know: {known}.")

    st.markdown(result["roadmap"])

    if result["problems"]:
        notes = "\n".join(f"- {p['issue']}: “{p['quote'][:100]}”" for p in result["problems"])
        st.warning(f"**Reviewer notes (not fixed):**\n{notes}")

    st.subheader("Sources")
    for s in result["sources"]:
        link = f"[{s['title']} – {s['company']}]({s['url']})" if s["url"] else f"{s['title']} – {s['company']}"
        st.markdown(f"[{s['n']}] {link} · {s['level']} · {s['source']}")

    with st.expander("How this roadmap was made"):
        st.markdown("**The plan (computed in code from the job posts):**")
        st.code(result["plan_text"], language=None)
        st.markdown("**Steps:**")
        st.code("\n".join(result["steps"]), language=None)
        c = result["citations"]
        st.caption(f"Citations: {c['total']} · invalid: {c['invalid'] or 'none'}")