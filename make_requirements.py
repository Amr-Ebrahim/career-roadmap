# make_requirements.py - writes the package lists for the two Linux machines:
#   requirements.txt           the ONLINE app (Streamlit Community Cloud)
#   requirements-pipeline.txt  the weekly GitHub Action (the app's list + what the pipeline adds)
# Only the packages that code imports, pinned to the versions installed on this laptop.
# The full list for everything else (evals, notebooks) lives in requirements-dev.txt.
#   python make_requirements.py
from importlib.metadata import version

# what app.py and the agent import (numpy and the rest come in with these)
APP_PACKAGES = [
    "streamlit", "requests", "python-dotenv", "huggingface_hub",
    "chromadb", "sentence-transformers", "scikit-learn", "pandas", "pyarrow",
    "groq", "langchain-core", "langchain-groq", "langgraph", "pydantic",
]
# what the data pipeline needs on top: HTML cleaning and language detection (process_arbeitnow.py)
PIPELINE_EXTRA = ["beautifulsoup4", "langdetect"]

torch = version("torch").split("+")[0]  # "2.15.0" (drops any "+cpu" ending)
HEADER = [
    "# CPU-only PyTorch: the normal Linux build pulls ~3 GB of GPU libraries the server can't use",
    "--extra-index-url https://download.pytorch.org/whl/cpu",
    f"torch=={torch}+cpu",
]


def write(path, title, packages):
    lines = [f"# {path} - {title}. Made by make_requirements.py: edit that, not this."] + HEADER
    lines += [f"{name}=={version(name)}" for name in packages]
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    print(f"Wrote {path} ({len(packages) + 1} packages)")


write("requirements.txt", "for the online app", APP_PACKAGES)
write("requirements-pipeline.txt", "for the weekly GitHub Action", APP_PACKAGES + PIPELINE_EXTRA)
