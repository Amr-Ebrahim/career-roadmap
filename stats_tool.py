# stats_tool.py - exact counts over ALL job posts (no LLM, no tokens).
# RAG answers "what do these 5 posts say"; this answers "how common is X across all posts".
import pandas as pd

DATA_PATH = "data/processed/jobs_skills.parquet"
COLUMNS = ["job_id", "company_name", "title", "role_family", "level",
           "source", "posted_date", "remote_allowed", "skills"]
FEW_POSTS = 30  # below this many posts, percentages are not reliable

_df = pd.read_parquet(DATA_PATH, columns=COLUMNS).drop_duplicates("job_id")
_known = {s.lower() for skills in _df["skills"] for s in skills}  # every skill we ever found


def filter_posts(role_family=None, level=None, source=None):
    df = _df
    if role_family:
        df = df[df["role_family"] == role_family]
    if level:
        df = df[df["level"] == level]
    if source:
        df = df[df["source"] == source]
    return df


def skill_share(role_family=None, level=None, source=None, top=15):
    # what % of the matching posts mention each skill
    posts = filter_posts(role_family, level, source)
    n = len(posts)
    counts = posts["skills"].explode().dropna().value_counts()
    table = pd.DataFrame({"posts": counts, "share_%": (100 * counts / n).round(1)})
    table.index.name = "skill"
    return table.head(top), n


def skill_lookup(skill, role_family=None, level=None, source=None):
    # one skill: in how many of the matching posts does it appear?
    posts = filter_posts(role_family, level, source)
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


def compare_levels(role_family, levels=("entry", "mid", "senior"), top=12):
    # % of posts mentioning each top skill, per level, side by side
    posts = filter_posts(role_family)
    posts = posts[posts["level"].isin(levels)]
    sizes = posts.groupby("level").size().reindex(levels, fill_value=0)

    long = posts[["job_id", "level", "skills"]].explode("skills").dropna()
    counts = long.groupby(["skills", "level"]).size().unstack(fill_value=0)
    counts = counts.reindex(columns=list(levels), fill_value=0)
    shares = (100 * counts / sizes).round(1)

    top_skills = counts.sum(axis=1).sort_values(ascending=False).head(top).index
    return shares.loc[top_skills], sizes


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