# agent_tools.py - the stats tool wrapped as tools an LLM agent can call (Stage 6).
# Each tool returns a short text with the numbers AND how many posts they come from.
from typing import Literal, Optional

from langchain_core.tools import tool

import stats_tool as st

Family = Literal["software", "backend", "frontend", "mobile", "data", "ai_ml", "devops_cloud",
                 "security", "networking_it", "qa", "architecture"]
Level = Literal["intern", "entry", "mid", "senior", "leadership"]

# role names and process words, not things you learn as a tool or technology
GENERIC = {"DevOps", "Site Reliability Engineering", "Troubleshooting", "Agile", "SDLC"}


def _group(role_family, level):
    return f"{level + '-level ' if level else ''}{role_family} posts"


def _warning(n):
    return f" WARNING: only {n} posts, treat these numbers as rough." if n < st.FEW_POSTS else ""


@tool
def top_skills(role_family: Family, level: Optional[Level] = None, top: int = 10) -> str:
    """Most requested skills for a role family (and optional level), as % of ALL matching
    job posts. Use this to decide what to learn for a role."""
    table, n = st.skill_share(role_family, level, top=top + len(GENERIC))
    if n == 0:
        return f"No {_group(role_family, level)} found."
    table = table[~table.index.isin(GENERIC)].head(top)
    items = ", ".join(f"{skill} {row['share_%']:.0f}%" for skill, row in table.iterrows())
    return f"{_group(role_family, level).capitalize()} ({n} posts): {items}.{_warning(n)}"


@tool
def skill_frequency(skill: str, role_family: Optional[Family] = None,
                    level: Optional[Level] = None) -> str:
    """How many job posts mention ONE skill, e.g. 'Terraform'. Use this to check a claim
    like 'most jobs ask for X' before writing it."""
    r = st.skill_lookup(skill, role_family, level)
    group = _group(role_family or "tech", level)
    if not r["known_skill"]:
        return (f"'{skill}' is not in the skills dictionary, so it cannot be counted "
                f"(this does NOT mean no job asks for it).")
    if r["out_of"] == 0:
        return f"No {group} found."
    return (f"{skill}: {r['posts']} of {r['out_of']} {group} ({r['share_%']:.0f}%)."
            f"{_warning(r['out_of'])}")


@tool
def level_progression(role_family: Family, top: int = 8) -> str:
    """How the top skills of a role family change from entry to mid to senior level.
    Use this to order a roadmap: what to learn first, what matters more later."""
    shares, sizes = st.compare_levels(role_family, top=top + len(GENERIC))
    shares = shares[~shares.index.isin(GENERIC)].head(top)
    lines = [f"{role_family} posts per level: " + ", ".join(f"{k} {v}" for k, v in sizes.items())]
    for skill, row in shares.iterrows():
        change = row["senior"] - row["entry"]
        trend = "rises" if change >= 10 else "falls" if change <= -10 else "about the same"
        lines.append(f"- {skill}: entry {row['entry']:.0f}% -> mid {row['mid']:.0f}% "
                     f"-> senior {row['senior']:.0f}% ({trend})")
    if sizes.min() < st.FEW_POSTS:
        lines.append(f"WARNING: some levels have fewer than {st.FEW_POSTS} posts.")
    return "\n".join(lines)


TOOLS = [top_skills, skill_frequency, level_progression]


if __name__ == "__main__":
    print(top_skills.invoke({"role_family": "devops_cloud", "level": "entry"}))
    print()
    print(skill_frequency.invoke({"skill": "Kubernetes", "role_family": "devops_cloud", "level": "entry"}))
    print(skill_frequency.invoke({"skill": "Fortran"}))
    print()
    print(level_progression.invoke({"role_family": "devops_cloud"}))
    print("\n=== What the LLM sees for one tool")
    print(top_skills.name, "-", top_skills.description)
    print(top_skills.args)