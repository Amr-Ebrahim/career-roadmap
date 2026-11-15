# api.py - the roadmap agent as a web API (FastAPI).
# Start it:  uvicorn api:app --port 8000      Try it:  http://127.0.0.1:8000/docs
import threading

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from roadmap_agent import AGENT_MODEL, generate_roadmap

app = FastAPI(title="Career Roadmap API",
              description="Learning roadmaps built from real job posts.")
_lock = threading.Lock()  # one roadmap at a time: the search tool keeps per-run sources


class RoadmapRequest(BaseModel):
    request: str = Field(min_length=10, max_length=500,
                         examples=["I know Linux and Python, I want a junior DevOps job"])


@app.get("/health")
def health():
    return {"status": "ok", "model": AGENT_MODEL}


@app.post("/roadmap")
def roadmap(body: RoadmapRequest):
    with _lock:
        try:
            return generate_roadmap(body.request, on_step=lambda text: print("  " + text))
        except Exception as e:  # e.g. Groq limit reached: tell the caller instead of a bare 500
            raise HTTPException(status_code=502, detail=f"{type(e).__name__}: {str(e)[:300]}")