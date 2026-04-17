"""Research Studio — FastAPI web application."""

from __future__ import annotations

import asyncio
import json
import pathlib
import re
import uuid
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv
load_dotenv()

from fastapi import BackgroundTasks, FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles

from src.course_parser import load_course_content
from src.document_generator import DocumentGenerator
from src.slide_deck_generator import SlideDeckGenerator
from src.topic_research import research_topics

# ── Paths ────────────────────────────────────────────────────────────────────
ROOT       = pathlib.Path(__file__).parent
STATIC_DIR = ROOT / "static"
OUTPUT_DIR = ROOT / "output"
UPLOAD_DIR = ROOT / "uploads"

OUTPUT_DIR.mkdir(exist_ok=True)
UPLOAD_DIR.mkdir(exist_ok=True)

# ── Job store (in-memory + file-backed) ──────────────────────────────────────
jobs: Dict[str, Dict[str, Any]] = {}


def _job_file(job_id: str) -> pathlib.Path:
    return OUTPUT_DIR / job_id / "job.json"


def _persist_job(job_id: str) -> None:
    """Write current job state to disk so restarts don't lose it."""
    job_dir = OUTPUT_DIR / job_id
    job_dir.mkdir(parents=True, exist_ok=True)
    _job_file(job_id).write_text(json.dumps(jobs[job_id]))


def _load_job(job_id: str) -> Optional[Dict[str, Any]]:
    """Read job state from disk (used when not in memory after a restart)."""
    f = _job_file(job_id)
    if f.exists():
        try:
            return json.loads(f.read_text())
        except Exception:
            pass
    return None


def _get_job(job_id: str) -> Optional[Dict[str, Any]]:
    """Return job from memory, falling back to disk."""
    if job_id in jobs:
        return jobs[job_id]
    data = _load_job(job_id)
    if data:
        jobs[job_id] = data  # re-hydrate memory cache
    return data


# ── App ──────────────────────────────────────────────────────────────────────
app = FastAPI(title="Research Studio")


# ── API routes (must be defined before static mount) ─────────────────────────

@app.get("/api/health")
async def health():
    import os
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    try:
        import anthropic as _a
        sdk_version = _a.__version__
    except Exception:
        sdk_version = "not installed"
    return {
        "status": "ok",
        "anthropic_sdk": sdk_version,
        "api_key_set": bool(api_key),
        "api_key_prefix": (api_key[:8] + "...") if api_key else None,
    }


@app.post("/api/generate")
async def generate(
    background_tasks: BackgroundTasks,
    topic: str = Form(...),
    guiding_questions: str = Form("[]"),
    output_type: str = Form("slides"),
    author: str = Form("Research Studio"),
    files: Optional[List[UploadFile]] = File(default=None),
):
    topic = topic.strip()
    if not topic:
        raise HTTPException(status_code=422, detail="Topic is required.")

    questions: List[str] = []
    try:
        questions = json.loads(guiding_questions)
        if not isinstance(questions, list):
            questions = []
    except (ValueError, TypeError):
        questions = []

    job_id = str(uuid.uuid4())
    upload_path = UPLOAD_DIR / job_id
    upload_path.mkdir(parents=True, exist_ok=True)

    # Save uploaded files synchronously before the background task starts
    if files:
        for f in files:
            if f and f.filename:
                content = await f.read()
                (upload_path / f.filename).write_bytes(content)

    jobs[job_id] = {
        "status": "pending",
        "status_message": "Starting…",
        "topic": topic,
        "output_type": output_type,
        "output_path": None,
        "filename": None,
        "error": None,
    }
    _persist_job(job_id)

    background_tasks.add_task(
        _run_generation,
        job_id,
        topic,
        questions,
        output_type,
        author.strip() or "Research Studio",
        upload_path,
    )

    return {"job_id": job_id}


@app.get("/api/status/{job_id}")
async def get_status(job_id: str):
    job = _get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found.")
    return {
        "status": job["status"],
        "status_message": job.get("status_message", ""),
        "topic": job.get("topic"),
        "filename": job.get("filename"),
        "error": job.get("error"),
    }


@app.get("/api/download/{job_id}")
async def download(job_id: str):
    job = _get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found.")
    if job["status"] != "complete":
        raise HTTPException(status_code=400, detail="Job not yet complete.")
    output_path = pathlib.Path(job["output_path"])
    if not output_path.exists():
        raise HTTPException(status_code=404, detail="Output file missing.")
    filename = job["filename"]
    content  = output_path.read_bytes()
    return Response(
        content=content,
        media_type="application/octet-stream",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Content-Length": str(len(content)),
        },
    )


# ── Frontend ──────────────────────────────────────────────────────────────────

@app.get("/")
async def serve_index():
    return FileResponse(STATIC_DIR / "index.html")


app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


# ── Background job ────────────────────────────────────────────────────────────

def _update_status(job_id: str, message: str) -> None:
    """Update the human-readable status message on the job (thread-safe for reads)."""
    if job_id in jobs:
        jobs[job_id]["status_message"] = message
        _persist_job(job_id)


async def _run_generation(
    job_id: str,
    topic: str,
    guiding_questions: List[str],
    output_type: str,
    author: str,
    upload_path: pathlib.Path,
):
    jobs[job_id]["status"] = "running"
    jobs[job_id]["status_message"] = "Searching the web…"
    _persist_job(job_id)
    try:
        on_status = lambda msg: _update_status(job_id, msg)
        brief = await asyncio.to_thread(
            _sync_research, topic, guiding_questions, upload_path, on_status
        )
        artifact_label = "slides" if output_type == "slides" else "report"
        _update_status(job_id, f"Building {artifact_label}…")
        output_path, filename = await asyncio.to_thread(
            _sync_generate, job_id, topic, brief, output_type, author
        )
        jobs[job_id]["output_path"] = str(output_path)
        jobs[job_id]["filename"]    = filename
        jobs[job_id]["status"]      = "complete"
        _persist_job(job_id)
    except Exception as exc:
        jobs[job_id]["status"] = "error"
        jobs[job_id]["error"]  = str(exc)
        _persist_job(job_id)


def _sync_research(topic, guiding_questions, upload_path, on_status=None):
    """Blocking research call — runs in a thread pool."""
    course_content = None
    if upload_path.exists() and any(upload_path.iterdir()):
        if on_status:
            on_status("Loading uploaded files…")
        try:
            course_content = load_course_content(upload_path)
        except Exception:
            pass

    briefs = research_topics(
        [topic],
        course_content=course_content,
        guiding_questions=guiding_questions or None,
        on_status=on_status,
    )
    return briefs[0]


def _sync_generate(job_id, topic, brief, output_type, author):
    """Blocking artifact generation — runs in a thread pool."""
    out_dir = OUTPUT_DIR / job_id
    out_dir.mkdir(parents=True, exist_ok=True)

    safe_name = re.sub(r"[^\w\-]", "_", topic)[:50]

    if output_type == "slides":
        filename = f"{safe_name}.pptx"
        out_path = out_dir / filename
        gen = SlideDeckGenerator(out_path)
        gen.build_research_deck(topic, brief, topic, author)
        gen.save()
    else:
        filename = f"{safe_name}.md"
        out_path = out_dir / filename
        gen = DocumentGenerator(out_path)
        gen.build(topic, brief, author)

    return out_path, filename
