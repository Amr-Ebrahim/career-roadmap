# planner.py - gap finder + curriculum, in plain code (no LLM, no tokens).
# Same request -> same plan, and every phase decision can be explained by a rule.
import stats_tool as st

GENERIC = {"DevOps", "Site Reliability Engineering", "Troubleshooting", "Agile", "SDLC"}
MIN_SHARE = 5                      # ignore skills in fewer than 5% of the posts
PHASE1, PHASE2, PHASE3 = 3, 4, 3   # how many skills per phase
CHANGE = 10                        # entry -> senior change (points) that counts as rises/falls


def make_plan(role_family, level="entry", title_keyword=None, known_skills=()):
    notes = []

    # 1. which posts: the narrow title if it has enough posts, else the whole family
    table, n = st.skill_share(role_family, level, top=40, title_keyword=title_keyword)
    if title_keyword and n < st.FEW_POSTS:
        notes.append(f"Only {n} {level}-level posts with '{title_keyword}' in the title, "
                     f"so the plan uses all {role_family} posts instead.")
        title_keyword = None
        table, n = st.skill_share(role_family, level, top=40)
    if n < st.FEW_POSTS:
        notes.append(f"Only {n} matching posts: treat all percentages as rough.")
    group = f"{level}-level {role_family} posts" + (f" with '{title_keyword}' in the title"
                                                     if title_keyword else "")

    # 2. how each skill changes with seniority (only if both ends have enough posts)
    shares, sizes = st.compare_levels(role_family, top=40, title_keyword=title_keyword)
    can_compare = sizes.get("entry", 0) >= st.FEW_POSTS and sizes.get("senior", 0) >= st.FEW_POSTS
    if not can_compare:
        notes.append("Too few entry or senior posts to compare levels.")

    # 3. gap finder: skills the person already has are taken out
    known_lower = {k.lower(): k for k in known_skills}
    have, gaps = [], []
    for skill, row in table.iterrows():
        if skill in GENERIC or row["share_%"] < MIN_SHARE:
            continue
        info = {"skill": skill, "share": row["share_%"], "trend": None}
        if can_compare and skill in shares.index:
            entry, senior = shares.loc[skill, "entry"], shares.loc[skill, "senior"]
            info["entry_to_senior"] = (entry, senior)
            info["trend"] = ("rises" if senior - entry >= CHANGE else
                             "falls" if entry - senior >= CHANGE else None)
        (have if skill.lower() in known_lower else gaps).append(info)
    have_lower = {h["skill"].lower() for h in have}
    not_counted = [k for low, k in known_lower.items() if low not in st._known]
    rarely_asked = [k for low, k in known_lower.items()
                    if low in st._known and low not in have_lower]

    # 4. curriculum, by rule instead of by the LLM's taste:
    #    Foundations = the 3 most requested gaps at this level
    #    Next level  = remaining gaps that grow with seniority (up to 3)
    #    Core skills = the next 4 by share among what is left
    phase1 = gaps[:PHASE1]
    rest = gaps[PHASE1:]
    phase3 = [g for g in rest if g["trend"] == "rises"][:PHASE3]
    phase2 = [g for g in rest if g not in phase3][:PHASE2]

    return {"role_family": role_family, "level": level, "title_keyword": title_keyword,
            "group": group, "n_posts": n, "notes": notes, "have": have,
            "rarely_asked": rarely_asked, "not_counted": not_counted,
            "phases": {"Foundations": phase1, "Core skills": phase2, "Next level": phase3}}


def plan_to_text(plan):
    # the plan as short text: what the writer LLM reads and what the critic checks against
    lines = [f"PLAN based on {plan['n_posts']} {plan['group']}."]
    for name, skills in plan["phases"].items():
        lines.append(f"\n{name}:")
        if not skills:
            lines.append("- (none)")
        for s in skills:
            line = f"- {s['skill']}: in {s['share']:.0f}% of the posts"
            # the seniority numbers are shown ONLY when the change passes the rule:
            # small differences (e.g. 31% -> 25%) made the writer invent "falls"
            if s["trend"]:
                e, sr = s["entry_to_senior"]
                line += f"; {s['trend']} with seniority (entry {e:.0f}% -> senior {sr:.0f}%)"
            lines.append(line)
    if plan["have"]:
        lines.append("\nAlready has: " + ", ".join(f"{h['skill']} (in {h['share']:.0f}% of the posts)"
                                                  for h in plan["have"]))
    if plan["rarely_asked"]:
        lines.append("Has, but rarely asked in these posts: " + ", ".join(plan["rarely_asked"]))
    if plan["not_counted"]:
        lines.append("Not in the skills dictionary (cannot be counted): " + ", ".join(plan["not_counted"]))
    for note in plan["notes"]:
        lines.append("NOTE: " + note)
    return "\n".join(lines)


if __name__ == "__main__":
    print(plan_to_text(make_plan("data", "entry", "analyst", known_skills=["Python", "Excel", "Dancing"])))
    print("\n" + "=" * 80 + "\n")
    print(plan_to_text(make_plan("devops_cloud", "entry", known_skills=["Linux", "Python"])))