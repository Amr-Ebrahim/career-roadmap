# hf_data.py - keeps the project's data in a private Hugging Face dataset repo.
#   python hf_data.py upload          laptop or GitHub Action: send the app data AND the pipeline inputs
#   python hf_data.py download        app data only (search index + skill table)
#   python hf_data.py download --all  app data + pipeline inputs (what the weekly Action needs)
# Online, app.py calls ensure_data() before loading the agent: it downloads the app data if missing.
# The weekly Action updates the data online, so on the laptop: DOWNLOAD before you upload,
# or an old local copy would replace the new one.
import os
import sys

from dotenv import load_dotenv

load_dotenv()  # HF_TOKEN (and HF_DATA_REPO, if set) come from .env on the laptop, from secrets online

from huggingface_hub import HfApi, snapshot_download

REPO_NAME = "career-roadmap-data"
# what the app reads
APP_PATTERNS = ["chroma/**", "processed/jobs_skills.parquet"]
# what the pipeline needs to run again without the laptop: every weekly Arbeitnow snapshot and
# the filtered Kaggle posts (the raw Kaggle CSV stays on the laptop)
PIPELINE_PATTERNS = ["raw/arbeitnow/**", "processed/jobs_tech.parquet"]
NEEDED = ["data/chroma/chroma.sqlite3", "data/processed/jobs_skills.parquet"]


def data_repo(api=None):
    # online / in the Action: HF_DATA_REPO is set; on the laptop it is built from your HF user name
    return os.getenv("HF_DATA_REPO") or f"{(api or HfApi()).whoami()['name']}/{REPO_NAME}"


def upload():
    api = HfApi()
    repo = data_repo(api)
    if api.repo_exists(repo, repo_type="dataset"):
        print(f"Found {repo}")
    else:
        api.create_repo(repo, repo_type="dataset", private=True)
        print(f"Created {repo} (private)")
    print("Uploading...")
    info = api.upload_folder(
        repo_id=repo,
        repo_type="dataset",
        folder_path="data",
        path_in_repo="data",
        allow_patterns=APP_PATTERNS + PIPELINE_PATTERNS,
        delete_patterns=["chroma/**"],  # Chroma renames its index folders: remove old ones online
        commit_message="Update data",
    )
    print("Done:", info.commit_url)
    print(f'\nFor the online app, the secret is: HF_DATA_REPO = "{repo}"')


def download(everything=False):
    patterns = APP_PATTERNS + (PIPELINE_PATTERNS if everything else [])
    snapshot_download(repo_id=data_repo(), repo_type="dataset", local_dir=".",
                      allow_patterns=[f"data/{p}" for p in patterns])


def ensure_data():
    if all(os.path.exists(p) for p in NEEDED):
        return "local"
    download()
    return "downloaded"


if __name__ == "__main__":
    command = sys.argv[1:2]
    if command == ["upload"]:
        upload()
    elif command == ["download"]:
        download(everything="--all" in sys.argv)
        print("Downloaded.")
    else:
        print("Usage: python hf_data.py upload | download [--all]")
