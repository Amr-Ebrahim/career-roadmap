# search_tool.py - the RAG retrieval as a tool the agent can call.
# Sources get numbers that keep counting across searches, so [n] stays unique in the final answer.
import threading
from typing import Literal, Optional

from langchain_core.tools import tool

from retrieval import retrieve

Family = Literal["software", "backend", "frontend", "mobile", "data", "ai_ml", "devops_cloud",
                 "security", "networking_it", "qa", "architecture"]
Level = Literal["intern", "entry", "mid", "senior", "leadership"]

MAX_CHARS = 500  # per post: keeps each request under Groq's 8K tokens-per-minute limit
SOURCES = []     # every post shown to the agent in this run, in citation order
_lock = threading.Lock()  # the agent can run 2 searches at once; numbers must not clash


def reset_sources():
    SOURCES.clear()


@tool
def search_job_posts(query: str, role_family: Optional[Family] = None,
                     level: Optional[Level] = None, title_keyword: Optional[str] = None) -> str:
    """Search real job posts and return short excerpts, each with a source number [n].
    Use it to find concrete examples of what employers write about a skill or tool.
    title_keyword keeps only posts whose title contains that word (e.g. 'analyst').
    Cite these numbers in the final answer."""
    with _lock:
        posts = retrieve(query, role_family=role_family, level=level, n_posts=10, mode="hybrid")
        if title_keyword:
            matching = [p for p in posts if title_keyword.lower() in str(p["title"]).lower()]
            posts = matching or posts  # nothing with that title: better a near example than none
        posts = posts[:3]
        if not posts:
            return "No matching posts."
        blocks = []
        for p in posts:
            known = [s["job_id"] for s in SOURCES]
            if p["job_id"] in known:          # same post found again: keep its first number
                n = known.index(p["job_id"]) + 1
            else:
                SOURCES.append(p)
                n = len(SOURCES)
            text = p["text"][:MAX_CHARS].replace("\n", " ")
            blocks.append(f"[{n}] {p['title']} at {p['company']} ({p['level']}): {text}")
    return "\n\n".join(blocks)