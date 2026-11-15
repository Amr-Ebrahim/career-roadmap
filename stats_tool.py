# stats_tool.py - exact counts over ALL job posts (no LLM, no tokens).
# RAG answers "what do these 5 posts say"; this answers "how common is X across all posts".
import pandas as pd

DATA_PATH = "data/processed/jobs_skills.parquet"
COLUMNS = ["job_id", "company_name", "title", "role_family", "level",
           "source", "posted_date", "remote_allowed", "skills"]
FEW_POSTS = 30  # below this many posts, percentages are not reliable

_df = pd.read_parquet(DATA_PATH, columns=COLUMNS).drop_duplicates("job_id")
_known = {s.lower() for skills in _df["skills"] for s in skills}  # every skill we ever found


def filter_posts(role_family=None, level=None, source=None, title_keyword=None):
    # title_keyword narrows a broad family, e.g. "analyst" inside "data"
    df = _df
    if role_family:
        df = df[df["role_family"] == role_family]
    if level:
        df = df[df["level"] == level]
    if source:
        df = df[df["source"] == source]
    if title_keyword:
        df = df[df["title"].str.contains(title_keyword, case=False, regex=False)]
    return df


def skill_share(role_family=None, level=None, source=None, top=15, title_keyword=None):
    # what % of the matching posts mention each skill
    posts = filter_posts(role_family, level, source, title_keyword)
    n = len(posts)
    counts = posts["skills"].explode().dropna().value_counts()
    table = pd.DataFrame({"posts": counts, "share_%": (100 * counts / n).round(1)})
    table.index.name = "skill"
    return table.head(top), n


def skill_lookup(skill, role_family=None, level=None, source=None, title_keyword=None):
    # one skill: in how many of the matching posts does it appear?
    posts = filter_posts(role_family, level, source, title_keyword)
    n = len(posts)
    wanted = skill.lower()
    count = int(posts["skills"].apply(lambda s: any(x.lower() == wanted for x in s)).sum())
    return {
        "skill": skill,
        "posts": count,
        "out_of": n,
        "share_%": round(100 * count / n, 1) if n else None,
        "few_posts": n < FEW_POSTS,
        "known_skill": wanted in _known,  # False = not in our dictionary at all
    }


def compare_levels(role_family, levels=("entry", "mid", "senior"), top=12, title_keyword=None):
    # % of posts mentioning each top skill, per level, side by side
    posts = filter_posts(role_family, title_keyword=title_keyword)
    posts = posts[posts["level"].isin(levels)]
    sizes = posts.groupby("level").size().reindex(levels, fill_value=0)

    long = posts[["job_id", "level", "skills"]].explode("skills").dropna()
    counts = long.groupby(["skills", "level"]).size().unstack(fill_value=0)
    counts = counts.reindex(columns=list(levels), fill_value=0)
    shares = (100 * counts / sizes.where(sizes > 0)).round(1).fillna(0)

    top_skills = counts.sum(axis=1).sort_values(ascending=False).head(top).index
    return shares.loc[top_skills], sizes


def skill_trend(skill, source, role_family=None, level=None, freq="M"):
    # share of posts mentioning a skill per month, inside ONE source only:
    # mixing sources would mix "later in time" with "different market"
    if not source:
        raise ValueError("Trends must use a single source, e.g. source='arbeitnow'")
    posts = filter_posts(role_family, level, source)
    wanted = skill.lower()
    has = posts["skills"].apply(lambda s: any(x.lower() == wanted for x in s))
    period = posts["posted_date"].dt.to_period(freq)
    table = pd.DataFrame({
        "posts": has.groupby(period).size(),
        "with_skill": has.groupby(period).sum().astype(int),
    })
    table["share_%"] = (100 * table["with_skill"] / table["posts"]).round(1)
    table["few_posts"] = table["posts"] < FEW_POSTS
    table.index.name = "period"
    return table


if __name__ == "__main__":
    pd.set_option("display.width", 120)

    table, n = skill_share("devops_cloud", "entry")
    print(f"=== Top skills, entry-level devops_cloud ({n} posts)")
    print(table)

    print("\n=== Lookups (entry-level devops_cloud)")
    for skill in ["Terraform", "Kubernetes", "Python", "Fortran"]:
        print(skill_lookup(skill, "devops_cloud", "entry"))

    shares, sizes = compare_levels("devops_cloud")
    print(f"\n=== devops_cloud: % of posts per level  (posts: {sizes.to_dict()})")
    print(shares)

    print("\n=== Trend: Python in Arbeitnow posts (all tech families)")
    print(skill_trend("Python", source="arbeitnow"))

    print("\n=== Whole 'data' family vs only titles with 'analyst' (entry level)")
    for keyword in (None, "analyst"):
        table, n = skill_share("data", "entry", top=8, title_keyword=keyword)
        shares = ", ".join(f"{s} {r['share_%']:.0f}%" for s, r in table.iterrows())
        print(f"  {keyword or 'all data titles'} ({n} posts): {shares}")