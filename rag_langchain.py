# rag_langchain.py - the same RAG as rag_by_hand.py, built from LangChain pieces.
# Same retrieval, same prompt, same model settings -> eval scores are comparable.
import sys

from dotenv import load_dotenv
from langchain_core.documents import Document
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnableLambda, RunnablePassthrough
from langchain_groq import ChatGroq

from rag_by_hand import MODEL, SYSTEM, check_citations, normalize_citations, source_blocks
from retrieval import retrieve

load_dotenv()  # ChatGroq reads GROQ_API_KEY from the environment


# ---- 1. Retrieval: our retrieve() wrapped so it returns LangChain Documents ----
def retrieve_docs(inputs):
    posts = retrieve(inputs["question"], role_family=inputs.get("role_family"),
                     level=inputs.get("level"))
    return [Document(page_content=p["text"],
                     metadata={k: v for k, v in p.items() if k != "text"})
            for p in posts]


def to_posts(docs):
    # back from Documents to our dicts, so we can reuse source_blocks()
    return [{**d.metadata, "text": d.page_content} for d in docs]


def format_docs(docs):
    return "\n\n".join(source_blocks(to_posts(docs)))


# ---- 2. Prompt: the same SYSTEM text, with {placeholders} for the variable parts ----
prompt = ChatPromptTemplate.from_messages([
    ("system", SYSTEM),
    ("human", "Job posts:\n\n{sources}\n\nQuestion: {question}"),
])


# ---- 3. The chain: each step's output flows into the next ----
def build_chain(llm):
    answer_chain = prompt | llm | StrOutputParser() | RunnableLambda(normalize_citations)
    return (
        RunnablePassthrough.assign(docs=RunnableLambda(retrieve_docs))
        .assign(sources=lambda x: format_docs(x["docs"]))
        .assign(answer=answer_chain)
    )


llm = ChatGroq(model=MODEL, temperature=0.2, max_tokens=1500, reasoning_effort="low")
chain = build_chain(llm)


def rag_answer(question, role_family=None, level=None):
    # same return shape as rag_by_hand.rag_answer, so eval_rag.py can use either one
    result = chain.invoke({"question": question, "role_family": role_family, "level": level})
    posts = to_posts(result["docs"])
    return {"answer": result["answer"], "posts": posts, "sources": source_blocks(posts)}


if __name__ == "__main__":
    question = "What skills do I need to get an entry-level cloud engineer job?"
    result = rag_answer(question, role_family="devops_cloud", level="entry")
    answer, posts = result["answer"], result["posts"]

    print("=== RAG ANSWER (LangChain) ===")
    print(answer)
    total, invalid, unused = check_citations(answer, len(posts))
    print(f"\nCitations: {total} | invalid numbers: {invalid or 'none'} | sources never cited: {unused or 'none'}")

    print("\nSources:")
    for i, p in enumerate(posts, start=1):
        print(f"  [{i}] {p['title']} | {p['company']} | {p['url'] or 'no link'}")

    if "--show" in sys.argv:
        for i, p in enumerate(posts, start=1):
            print(f"\n----- SOURCE [{i}] -----")
            print(p["text"])