import os
import re
import sys
from datetime import datetime
from dotenv import load_dotenv
from groq import Groq
from retrieval import retrieve

load_dotenv()
client = Groq(api_key=os.getenv("GROQ_API_KEY"))
MODEL = "openai/gpt-oss-120b"

SYSTEM = """You are a career advisor who answers ONLY from the job posts provided.
Rules:
- Use only facts found in the sources. Do not use outside knowledge.
- Cite every claim with the source number in square brackets, exactly like [1] or [2][4].
- Do not use any other citation format and do not add line numbers.
- Only describe what these posts say. Do not generalize to "most jobs", "typical" or "the market".
- If the sources do not contain enough information, say so clearly.
- Be concise: a short summary, then bullet points.

Example of a correct bullet:
- Terraform for infrastructure as code [2][5]"""


def source_blocks(posts):
    # one text block per post, exactly as the LLM sees it
    blocks = []
    for i, p in enumerate(posts, start=1):
        date = datetime.fromtimestamp(p["posted_ts"]).date()
        header = f"[{i}] {p['title']} at {p['company']} ({p['level']}, {p['source']}, {date})"
        blocks.append(header + "\n" + p["text"])
    return blocks


def format_sources(posts):
    return "\n\n".join(source_blocks(posts))


def ask_llm(system, user):
    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        temperature=0.2,
        max_completion_tokens=1500,
        reasoning_effort="low",
    )
    choice = response.choices[0]
    return choice.message.content, choice.finish_reason, response.usage


def normalize_citations(text):
    return re.sub(r"【(\d+)†[^】]*】", r"[\1]", text)


def check_citations(text, n_sources):
    cited = [int(n) for n in re.findall(r"\[(\d+)\]", text)]
    used = set(cited)
    invalid = sorted(n for n in used if n < 1 or n > n_sources)
    unused = [n for n in range(1, n_sources + 1) if n not in used]
    return len(cited), invalid, unused


def rag_answer(question, role_family=None, level=None):
    # the whole RAG in one call: retrieve -> build prompt -> ask -> fix citations
    posts = retrieve(question, role_family=role_family, level=level)
    user_message = f"Job posts:\n\n{format_sources(posts)}\n\nQuestion: {question}"
    raw_answer, finish, usage = ask_llm(SYSTEM, user_message)
    answer = normalize_citations(raw_answer)
    return {
        "answer": answer,
        "raw_answer": raw_answer,
        "posts": posts,
        "sources": source_blocks(posts),
        "finish": finish,
        "usage": usage,
    }


if __name__ == "__main__":
    question = "What skills do I need to get an entry-level cloud engineer job?"
    result = rag_answer(question, role_family="devops_cloud", level="entry")
    answer, posts, usage = result["answer"], result["posts"], result["usage"]

    print("=== RAG ANSWER ===")
    print(answer)
    print(f"\n(finish: {result['finish']}, input tokens: {usage.prompt_tokens}, output tokens: {usage.completion_tokens})")

    total, invalid, unused = check_citations(answer, len(posts))
    print(f"Citations: {total} | invalid numbers: {invalid or 'none'} | sources never cited: {unused or 'none'}")
    print("Model used its own citation format:", "yes (fixed)" if answer != result["raw_answer"] else "no")

    print("\nSources:")
    for i, p in enumerate(posts, start=1):
        print(f"  [{i}] {p['title']} | {p['company']} | {p['url'] or 'no link'}")

    if "--show" in sys.argv:
        for i, p in enumerate(posts, start=1):
            print(f"\n----- SOURCE [{i}] -----")
            print(p["text"])