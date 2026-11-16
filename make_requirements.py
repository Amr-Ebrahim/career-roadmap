# make_requirements.py - writes requirements.txt for the ONLINE app (a Linux server).
# Only the packages the app imports, pinned to the versions installed on this laptop.
# The full list for everything else (pipeline, evals) lives in requirements-dev.txt.
#   python make_requirements.py
from importlib.metadata import version

# what app.py and the agent import (numpy and the rest come in with these)
APP_PACKAGES = [
    "streamlit", "requests", "python-dotenv", "huggingface_hub",
    "chromadb", "sentence-transformers", "scikit-learn", "pandas", "pyarrow",
    "groq", "langchain-core", "langchain-groq", "langgraph", "pydantic",
]

torch = version("torch").split("+")[0]  # "2.15.0" (drops any "+cpu" ending)
lines = [
    "# requirements.txt - for the online app. Made by make_requirements.py: edit that, not this.",
    "# CPU-only PyTorch: the normal Linux build pulls ~3 GB of GPU libraries the server can't use",
    "--extra-index-url https://download.pytorch.org/whl/cpu",
    f"torch=={torch}+cpu",
]
lines += [f"{name}=={version(name)}" for name in APP_PACKAGES]

with open("requirements.txt", "w", encoding="utf-8") as f:
    f.write("\n".join(lines) + "\n")
print("\n".join(lines))
print(f"\nWrote requirements.txt ({len(lines) - 3} packages)")