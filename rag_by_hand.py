import os
import re
import sys
from datetime import datetime

from dotenv import load_dotenv
from groq import Groq

from retrieval import QUERY_PREFIX, _model, retrieve
from sentence_filter import filter_posts


load_dotenv()

MODEL = "openai/gpt-oss-120b"

SYSTEM = """You are a career advisor who answers ONLY from the job posts provided.
Rules:
- Use only facts found in the sources. Do not use outside knowledge.
- Cite every claim with the source number in square brackets, exactly like [1] or [2][4].
- Do not use any other citation format and do not add line numbers.
- Only describe what these posts say. Do not generalize to "most jobs", "typical" or "the market".
- Preserve distinctions between required, preferred, bonus, and accepted in lieu of experience.
- Do not describe every mentioned certification as mandatory.
- For certification questions, report certifications, not unrelated tools or duties.
- If the sources do not contain enough information, say so clearly.
- Absence from these excerpts does not prove absence from every job post.
- Be concise: a short summary, then bullet points.

Example of a correct bullet:
- Terraform for infrastructure as code [2][5]"""


def source_blocks(posts):
    """These exact blocks are used for generation and evaluation."""
    blocks = []

    for index, post in enumerate(posts, start=1):
        try:
            posted_date = datetime.fromtimestamp(
                float(post["posted_ts"])
            ).date()
        except (
            KeyError,
            TypeError,
            ValueError,
            OverflowError,
            OSError,
        ):
            posted_date = "date unknown"

        header = (
            f"[{index}] {post.get('title', 'Unknown title')} "
            f"at {post.get('company', 'Unknown company')} "
            f"({post.get('level', 'unknown')}, "
            f"{post.get('source', 'unknown')}, "
            f"{posted_date})"
        )

        blocks.append(header + "\n" + post["text"])

    return blocks


def format_sources(posts):
    return "\n\n".join(source_blocks(posts))


def encode(texts, is_query=False):
    if is_query:
        texts = [
            QUERY_PREFIX + text
            for text in texts
        ]

    return _model.encode(
        texts,
        normalize_embeddings=True,
    )


def prepare_posts(
    question,
    role_family=None,
    level=None,
    mode="vector",
):
    valid_modes = {
        "vector",
        "hybrid",
        "vector+sentences",
        "hybrid+sentences",
    }

    if mode not in valid_modes:
        raise ValueError(
            f"Unknown mode {mode!r}. "
            f"Choose from {sorted(valid_modes)}"
        )

    search, _, extra = mode.partition("+")

    posts = retrieve(
        question,
        role_family=role_family,
        level=level,
        mode=search,
    )

    if extra == "sentences":
        posts = filter_posts(question, posts, encode)

    return posts


def ask_llm(system, user):
    # Create the client only when an API call is needed.
    client = Groq(
        api_key=os.getenv("GROQ_API_KEY")
    )

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

    return (
        choice.message.content or "",
        choice.finish_reason,
        response.usage,
    )


def normalize_citations(text):
    return re.sub(
        r"【(\d+)(?:†[^】]*)?】",
        r"[\1]",
        text,
    )


def check_citations(text, n_sources):
    cited = [
        int(number)
        for number in re.findall(r"$$(\d+)$$", text)
    ]

    used = set(cited)

    invalid = sorted(
        number
        for number in used
        if number < 1 or number > n_sources
    )

    unused = [
        number
        for number in range(1, n_sources + 1)
        if number not in used
    ]

    return len(cited), invalid, unused


def rag_answer(
    question,
    role_family=None,
    level=None,
    mode="vector",
):
    posts = prepare_posts(
        question,
        role_family,
        level,
        mode,
    )

    blocks = source_blocks(posts)

    if not posts:
        answer = (
            "No supporting excerpts were selected for this "
            "question. This does not establish that the "
            "information is absent from all job posts."
        )

        return {
            "answer": answer,
            "raw_answer": answer,
            "posts": [],
            "sources": [],
            "finish": "no_evidence",
            "usage": None,
        }

    user_message = (
        "Job posts:\n\n"
        + "\n\n".join(blocks)
        + "\n\nQuestion: "
        + question
    )

    raw_answer, finish, usage = ask_llm(
        SYSTEM,
        user_message,
    )

    return {
        "answer": normalize_citations(raw_answer),
        "raw_answer": raw_answer,
        "posts": posts,
        "sources": blocks,
        "finish": finish,
        "usage": usage,
    }


if __name__ == "__main__":
    preview = "--preview" in sys.argv

    if preview:
        # Inspect the question that scored 0.208.
        question = (
            "Which certifications do entry-level "
            "IT support jobs mention?"
        )

        posts = prepare_posts(
            question,
            role_family="networking_it",
            level="entry",
            mode="hybrid+sentences",
        )

        print("=== FILTERED CONTEXT PREVIEW ===")
        print("Question:", question)
        print("Selected sources:", len(posts))
        print("No Groq or DeepEval calls were made.")

        for index, post in enumerate(posts, start=1):
            print(
                f"\nSource {index}: "
                f"{post.get('title', 'Unknown title')} "
                f"| kept {post.get('kept', '?')} "
                f"| {post.get('filter_strategy', '?')}"
            )
            print(post["text"])

    else:
        question = (
            "What skills do I need to get an "
            "entry-level cloud engineer job?"
        )

        result = rag_answer(
            question,
            role_family="devops_cloud",
            level="entry",
            mode="hybrid+sentences",
        )

        print("=== RAG ANSWER ===")
        print(result["answer"])

        usage = result["usage"]

        if usage is not None:
            print(
                f"\n(finish: {result['finish']}, "
                f"input tokens: {usage.prompt_tokens}, "
                f"output tokens: {usage.completion_tokens})"
            )

        total, invalid, unused = check_citations(
            result["answer"],
            len(result["posts"]),
        )

        print(
            f"Citations: {total} | "
            f"invalid numbers: {invalid or 'none'} | "
            f"sources never cited: {unused or 'none'}"
        )

        if "--show" in sys.argv:
            for block in result["sources"]:
                print("\n" + block)