# hf_data.py - keeps the app's data in a private Hugging Face dataset repo.
# Laptop (after the weekly pipeline):  python hf_data.py upload
# Online, app.py calls ensure_data() before loading the agent: it downloads the data if it is missing.
import os
import sys

from dotenv import load_dotenv

load_dotenv()  # HF_TOKEN (and HF_DATA_REPO, if set) come from .env on the laptop, from secrets online

from huggingface_hub import HfApi, snapshot_download

REPO_NAME = "career-roadmap-data"
# the only data the app reads; raw files and backups stay on the laptop
APP_PATTERNS = ["chroma/**", "processed/jobs_skills.parquet"]
NEEDED = ["data/chroma/chroma.sqlite3", "data/processed/jobs_skills.parquet"]


def data_repo(api=None):
    # online: HF_DATA_REPO is set in the secrets; on the laptop it is built from your HF user name
    return os.getenv("HF_DATA_REPO") or f"{(api or HfApi()).whoami()['name']}/{REPO_NAME}"


def upload():
    api = HfApi()
    repo = data_repo(api)
    api.create_repo(repo, repo_type="dataset", private=True, exist_ok=True)
    print(f"Uploading to {repo} (private dataset)...")
    info = api.upload_folder(
        repo_id=repo,
        repo_type="dataset",
        folder_path="data",
        path_in_repo="data",
        allow_patterns=APP_PATTERNS,
        delete_patterns=["chroma/**"],  # Chroma renames its index folders: remove old ones online
        commit_message="Update app data",
    )
    print("Done:", info.commit_url)
    print(f'\nFor the online app, the secret will be: HF_DATA_REPO = "{repo}"')


def ensure_data():
    if all(os.path.exists(p) for p in NEEDED):
        return "local"
    snapshot_download(repo_id=data_repo(), repo_type="dataset", local_dir=".",
                      allow_patterns=[f"data/{p}" for p in APP_PATTERNS])
    return "downloaded"


if __name__ == "__main__":
    if sys.argv[1:] == ["upload"]:
        upload()
    elif sys.argv[1:] == ["download"]:
        print(ensure_data())
    else:
        print("Usage: python hf_data.py upload | download")