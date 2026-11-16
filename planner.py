# planner.py - gap finder + curriculum + learning order, in plain code (no LLM, no tokens).
# Same request -> same plan, and every decision can be explained by a rule.
import stats_tool as st
from prereqs import GROUP_OF, PREREQS

GENERIC = {"DevOps", "Site Reliability Engineering", "Troubleshooting", "Agile", "SDLC"}
MIN_SHARE = 5                      # ignore skills in fewer than 5% of the posts
PHASE1, PHASE2, PHASE3 = 3, 4, 3   # how many skills per phase
CHANGE = 10                        # entry -> senior change (points) that counts as rises/falls
PHASE_NAMES = ["Foundations", "Core skills", "Next level"]


def learning_order(phases, known_lower, info_for):
    """Puts every skill AFTER the skills it needs (prereqs.py), like courses with prerequisites.
    A needed skill the person doesn't have and the plan doesn't include is added to the plan.
    Returns the phases again, numbered in learning order."""
    by_name, phase_of, planned = {}, {}, []
    for p, name in enumerate(PHASE_NAMES):
        for s in phases[name]:
            by_name[s["skill"]], phase_of[s["skill"]] = s, p
            planned.append(s["skill"])

    def needs_of(skill):
        needs = []
        for item in PREREQS.get(skill, []):
            options = item if isinstance(item, tuple) else (item,)
            if any(o.lower() in known_lower for o in options):
                continue  # the person already has it (or one of the alternatives)
            in_plan = [o for o in options if o in by_name]
            if in_plan:
                needs.append(in_plan[0])
                continue
            # not in the plan yet: add it (of several alternatives, the one asked for most)
            pick = max(options, key=lambda o: info_for(o)["share"])
            by_name[pick] = {**info_for(pick), "added_for": skill}
            phase_of[pick] = phase_of[skill]
            needs.append(pick)
        return needs

    # depth-first: before placing a skill, place what it needs
    order, placed, visiting = [], set(), set()

    def visit(skill):
        if skill in placed or skill in visiting:  # "visiting" guards against a loop in PREREQS
            return
        visiting.add(skill)
        needs = needs_of(skill)
        by_name[skill]["after"] = needs
        for need in needs:
            visit(need)
        visiting.discard(skill)
        placed.add(skill)
        order.append(skill)

    for skill in planned:
        visit(skill)

    # a needed skill moves up to the phase of the skill that needs it (never later)
    for _ in range(len(order)):
        for skill in order:
            for need in by_name[skill]["after"]:
                phase_of[need] = min(phase_of[need], phase_of[skill])

    ordered = sorted(order, key=lambda s: (phase_of[s], order.index(s)))
    result = {name: [] for name in PHASE_NAMES}
    for step, skill in enumerate(ordered, start=1):
        by_name[skill]["step"] = step
        result[PHASE_NAMES[phase_of[skill]]].append(by_name[skill])
    return result


def make_plan(role_family, level="entry", title_keyword=None, known_skills=()):
    notes = []

    # 1. which posts: the narrow title if it has enough posts, else the whole family
    table, n = st.skill_share(role_family, level, top=500, title_keyword=title_keyword)
    if title_keyword and n < st.FEW_POSTS:
        notes.append(f"Only {n} {level}-level posts with '{title_keyword}' in the title, "
                     f"so the plan uses all {role_family} posts instead.")
        title_keyword = None
        table, n = st.skill_share(role_family, level, top=500)
    if n < st.FEW_POSTS:
        notes.append(f"Only {n} matching posts: treat all percentages as rough.")
    group = f"{level}-level {role_family} posts" + (f" with '{title_keyword}' in the title"
                                                     if title_keyword else "")

    # 2. how each skill changes with seniority (only if both ends have enough posts)
    shares, sizes = st.compare_levels(role_family, top=500, title_keyword=title_keyword)
    can_compare = sizes.get("entry", 0) >= st.FEW_POSTS and sizes.get("senior", 0) >= st.FEW_POSTS
    if not can_compare:
        notes.append("Too few entry or senior posts to compare levels.")

    def info_for(skill):
        # share + seniority trend of one skill (0% if no matching post mentions it)
        share = float(table.loc[skill, "share_%"]) if skill in table.index else 0.0
        info = {"skill": skill, "share": share, "trend": None}
        if can_compare and skill in shares.index:
            entry, senior = shares.loc[skill, "entry"], shares.loc[skill, "senior"]
            info["entry_to_senior"] = (float(entry), float(senior))
            info["trend"] = ("rises" if senior - entry >= CHANGE else
                             "falls" if entry - senior >= CHANGE else None)
        return info

    # 3. gap finder: skills the person already has are taken out
    known_lower = {k.lower(): k for k in known_skills}
    have, gaps = [], []
    for skill, row in table.iterrows():
        if skill in GENERIC or row["share_%"] < MIN_SHARE:
            continue
        (have if skill.lower() in known_lower else gaps).append(info_for(skill))

    # 3b. groups (prereqs.py): alternatives and same-topic skills become ONE step.
    #     The member asked for most stays; the others are shown on it ("or ..."/"includes ...").
    #     Knowing any member already counts for the whole group.
    kept, by_group, covered = [], {}, []
    for g in gaps:  # gaps are sorted by share, so the first member of a group is the most asked
        kind, members = GROUP_OF.get(g["skill"], (None, None))
        if members is None:
            kept.append(g)
            continue
        has = [m for m in members if m.lower() in known_lower]
        if has:
            covered.append(f"{g['skill']} ({g['share']:.0f}%, covered by {has[0]})")
        elif members in by_group:
            by_group[members].setdefault(kind, []).append({"skill": g["skill"], "share": g["share"]})
        else:
            by_group[members] = g
            kept.append(g)
    gaps = kept
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

    # 5. learning order: what a skill needs comes first (prereqs.py, not the job data)
    phases = learning_order({"Foundations": phase1, "Core skills": phase2, "Next level": phase3},
                            known_lower, info_for)

    return {"role_family": role_family, "level": level, "title_keyword": title_keyword,
            "group": group, "n_posts": n, "notes": notes, "have": have,
            "rarely_asked": rarely_asked, "not_counted": not_counted, "covered": covered,
            "phases": phases}


def plan_to_text(plan):
    # the plan as short text: what the writer LLM reads and what the critic checks against
    lines = [f"PLAN based on {plan['n_posts']} {plan['group']}.",
             "Skills are numbered in learning order: what a skill needs comes first "
             "(the order comes from a prerequisite list, not from the job data)."]
    for name, skills in plan["phases"].items():
        lines.append(f"\n{name}:")
        if not skills:
            lines.append("- (none)")
        for s in skills:
            share = (f"in {s['share']:.0f}% of the posts" if s["share"] >= 0.5
                     else "not asked in these posts")
            line = f"{s['step']}. {s['skill']}: {share}"
            # the seniority numbers are shown ONLY when the change passes the rule:
            # small differences (e.g. 31% -> 25%) made the writer invent "falls"
            if s["trend"]:
                e, sr = s["entry_to_senior"]
                line += f"; {s['trend']} with seniority (entry {e:.0f}% -> senior {sr:.0f}%)"
            if s.get("or"):
                line += "; or " + ", ".join(f"{o['skill']} ({o['share']:.0f}%)" for o in s["or"]) + \
                        " (pick one)"
            if s.get("includes"):
                line += "; includes " + ", ".join(f"{o['skill']} ({o['share']:.0f}%)"
                                                  for o in s["includes"])
            if s.get("added_for"):
                line += f"; added because {s['added_for']} needs it"
            elif s.get("after"):
                line += f"; learn after {', '.join(s['after'])}"
            lines.append(line)
    if plan["have"]:
        lines.append("\nAlready has: " + ", ".join(f"{h['skill']} (in {h['share']:.0f}% of the posts)"
                                                  for h in plan["have"]))
    if plan["rarely_asked"]:
        lines.append("Has, but rarely asked in these posts: " + ", ".join(plan["rarely_asked"]))
    if plan.get("covered"):
        lines.append("Not a separate step (the person has an alternative): " + ", ".join(plan["covered"]))
    if plan["not_counted"]:
        lines.append("Not in the skills dictionary (cannot be counted): " + ", ".join(plan["not_counted"]))
    for note in plan["notes"]:
        lines.append("NOTE: " + note)
    return "\n".join(lines)


if __name__ == "__main__":
    print(plan_to_text(make_plan("data", "entry", "analyst", known_skills=["Python", "Excel", "Dancing"])))
    print("\n" + "=" * 80 + "\n")
    print(plan_to_text(make_plan("devops_cloud", "entry", known_skills=["Linux", "Python"])))
    print("\n" + "=" * 80 + "\n")
    print(plan_to_text(make_plan("devops_cloud", "entry")))
