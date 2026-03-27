"""
API server that runs Agent.py and exposes job progress for frontend polling.
"""

from __future__ import annotations

import asyncio
from datetime import datetime
import json
import os
import re
import shutil
import sys
import threading
import uuid
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional

from dotenv import load_dotenv
from fastapi import BackgroundTasks, FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

# Keep compatibility with different key names.
_dry = os.getenv("DRY_RUN")
if _dry is None:
    _dry = os.getenv("dry_run", os.getenv("dry run", "0"))
DRY_RUN = str(_dry).strip() == "1"

_clean = os.getenv("CLEAN_AFTER_ARCHIVE", "1")
CLEAN_AFTER_ARCHIVE = str(_clean).strip() == "1"

UPLOADS_DIR = BASE_DIR / "uploads"
UPLOADS_DIR.mkdir(parents=True, exist_ok=True)

MEMORY_FILE = BASE_DIR / "memory.json"
GENERATED_VIDEOS_DIR = BASE_DIR / "generated_videos"
GENERATED_FRAMES_DIR = BASE_DIR / "generated_frames"
GENERATED_AUDIO_DIR = BASE_DIR / "generated_audio"
JOB_RUNS_DIR = BASE_DIR / "job_runs"
SAMPLE_DRY_RUN_DIR = BASE_DIR / "samples" / "dry_run"
JOB_RUNS_DIR.mkdir(parents=True, exist_ok=True)


class JobStatus(str, Enum):
    queued = "queued"
    running = "running"
    completed = "completed"
    failed = "failed"


class Notification(BaseModel):
    seq: int
    text: str


class Job(BaseModel):
    id: str
    status: JobStatus
    message: str
    image_path: Optional[Path] = None
    result_path: Optional[Path] = None
    archive_dir: Optional[Path] = None
    agent_response: Optional[str] = None
    notifications: List[Notification] = Field(default_factory=list)
    error: Optional[str] = None


jobs: Dict[str, Job] = {}
lock = threading.Lock()

app = FastAPI(title="ET Agent API", version="0.5.0")


def _get_job(job_id: str) -> Job:
    with lock:
        job = jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


def _save_job(job: Job) -> None:
    with lock:
        jobs[job.id] = job


def _push(job_id: str, text: str) -> None:
    words = text.strip().split()
    if len(words) < 2:
        text = f"Status {text.strip()}"
        words = text.split()
    if len(words) > 5:
        text = " ".join(words[:5])

    with lock:
        job = jobs.get(job_id)
        if not job:
            return
        if job.notifications and job.notifications[-1].text == text:
            return
        seq = len(job.notifications) + 1
        job.notifications.append(Notification(seq=seq, text=text))
        jobs[job_id] = job


def _step_notice(description: str, status: str) -> str:
    desc = description.lower()

    if status == "error":
        return "Step failed"

    if "scriptwriter_agent" in desc:
        return "Writing script"
    if "storyboard_artist" in desc:
        return "Creating storyboard"
    if "voiceover_agent" in desc:
        return "Generating narration"
    if "motion_designer_agent" in desc:
        return "Animating scenes"
    if "video_editor_agent" in desc:
        return "Composing final video"

    if "generate_storyboard_image" in desc:
        return "Rendering frame"
    if "generate_video_veo" in desc:
        return "Generating video clip"
    if "generate_voiceover" in desc:
        return "Creating voice track"
    if "compile_videos" in desc:
        return "Compiling clips"
    if "add_audio_to_video" in desc:
        return "Mixing audio"

    if "running tool" in desc:
        return "Running tool"
    if "loading skill" in desc:
        return "Loading specialist"

    if status in ("success", "done"):
        return "Step completed"

    return "Pipeline running"


def _read_memory() -> List[dict]:
    if not MEMORY_FILE.exists():
        return []
    try:
        with MEMORY_FILE.open("r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, list) else []
    except Exception:
        return []


def _pump_memory(job_id: str, seen_ids: set[int], seen_status: Dict[int, str]) -> None:
    for step in _read_memory():
        step_id = int(step.get("id", 0))
        if step_id <= 0:
            continue

        status = str(step.get("status", "pending"))
        desc = str(step.get("description", ""))

        if step_id not in seen_ids:
            seen_ids.add(step_id)
            seen_status[step_id] = status
            _push(job_id, _step_notice(desc, status))
        elif seen_status.get(step_id) != status:
            seen_status[step_id] = status
            if status == "error":
                _push(job_id, "Step failed")


def _build_query(message: str, image_path: Optional[Path]) -> str:
    if not image_path:
        return message

    return (
        f"{message}\n\n"
        f"Reference style image path: {image_path}\n"
        "Use this image as the visual style reference for storyboard and motion; "
        "follow the style described in the main message."
    )


def _extract_video_path(text: str) -> Optional[Path]:
    if not text:
        return None

    matches = re.findall(r"([A-Za-z]:\\[^\s\"']+\.mp4|[\w./\\-]+\.mp4)", text)
    for match in matches:
        p = Path(match)
        if not p.is_absolute():
            p = BASE_DIR / p
        p = p.resolve()
        if p.exists() and p.suffix.lower() == ".mp4":
            return p
    return None


def _resolve_final_video() -> Optional[Path]:
    candidates = [
        BASE_DIR / "output.mp4",
        BASE_DIR / "final_output.mp4",
        GENERATED_VIDEOS_DIR / "output.mp4",
        GENERATED_VIDEOS_DIR / "final_output.mp4",
    ]
    for p in candidates:
        if p.exists():
            return p.resolve()

    if GENERATED_VIDEOS_DIR.exists():
        others = [
            p for p in GENERATED_VIDEOS_DIR.glob("*.mp4")
            if p.is_file() and not p.name.startswith("sense_")
        ]
        if others:
            others.sort(key=lambda x: x.stat().st_mtime, reverse=True)
            return others[0].resolve()

    return None


def _run_agent(query: str) -> str:
    from Agent import Agent

    agent = Agent()
    agent.memory.clear()
    return agent.run(query)


def _ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def _clear_dir(path: Path) -> None:
    if not path.exists():
        return
    for item in path.iterdir():
        try:
            if item.is_dir():
                shutil.rmtree(item)
            else:
                item.unlink()
        except Exception:
            pass


def _write_text(path: Path, content: str) -> None:
    _ensure_dir(path.parent)
    path.write_text(content, encoding="utf-8")


def _write_json(path: Path, data: dict) -> None:
    _ensure_dir(path.parent)
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def _copy_file_if_exists(src: Path, dst: Path) -> None:
    if src.exists():
        _ensure_dir(dst.parent)
        shutil.copy2(src, dst)


def _copy_tree_if_exists(src: Path, dst: Path) -> None:
    if src.exists() and src.is_dir():
        shutil.copytree(src, dst, dirs_exist_ok=True)


def _load_sample_notifications() -> List[str]:
    notif_file = SAMPLE_DRY_RUN_DIR / "notifications.json"
    if notif_file.exists():
        try:
            with notif_file.open("r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, list):
                notes = [str(x).strip() for x in data if str(x).strip()]
                filtered = [n for n in notes if n not in {"Archiving outputs", "Video ready", "Workspace cleaned"}]
                if filtered:
                    return filtered
        except Exception:
            pass
    return [
        "Writing script",
        "Creating storyboard",
        "Generating narration",
        "Animating scenes",
        "Composing final video",
    ]


def _cleanup_workspace_outputs() -> None:
    for d in [GENERATED_FRAMES_DIR, GENERATED_AUDIO_DIR, GENERATED_VIDEOS_DIR, BASE_DIR / "temp_merges"]:
        _clear_dir(d)

    for f in [BASE_DIR / "script.json", BASE_DIR / "output.mp4", BASE_DIR / "final_output.mp4"]:
        if f.exists():
            try:
                f.unlink()
            except Exception:
                pass

    if MEMORY_FILE.exists():
        MEMORY_FILE.write_text("[]\n", encoding="utf-8")


def _materialize_dry_run_sample() -> Path:
    if not SAMPLE_DRY_RUN_DIR.exists():
        raise FileNotFoundError(f"Dry-run sample folder missing: {SAMPLE_DRY_RUN_DIR}")

    _cleanup_workspace_outputs()

    _copy_file_if_exists(SAMPLE_DRY_RUN_DIR / "script.json", BASE_DIR / "script.json")
    _copy_file_if_exists(SAMPLE_DRY_RUN_DIR / "memory.json", MEMORY_FILE)
    _copy_file_if_exists(SAMPLE_DRY_RUN_DIR / "output.mp4", BASE_DIR / "output.mp4")
    _copy_file_if_exists(SAMPLE_DRY_RUN_DIR / "final_output.mp4", BASE_DIR / "final_output.mp4")

    _copy_tree_if_exists(SAMPLE_DRY_RUN_DIR / "generated_frames", GENERATED_FRAMES_DIR)
    _copy_tree_if_exists(SAMPLE_DRY_RUN_DIR / "generated_audio", GENERATED_AUDIO_DIR)
    _copy_tree_if_exists(SAMPLE_DRY_RUN_DIR / "generated_videos", GENERATED_VIDEOS_DIR)

    final_video = _resolve_final_video()
    if not final_video:
        raise FileNotFoundError("Dry-run sample does not contain a usable final mp4")
    return final_video


def _archive_job_outputs(job: Job) -> tuple[Path, Optional[Path]]:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    run_dir = JOB_RUNS_DIR / f"{timestamp}_{job.id[:8]}"
    input_dir = run_dir / "input"
    artifacts_dir = run_dir / "artifacts"
    result_dir = run_dir / "result"

    _ensure_dir(input_dir)
    _ensure_dir(artifacts_dir)
    _ensure_dir(result_dir)

    _write_text(input_dir / "message.txt", job.message)
    if job.image_path and job.image_path.exists():
        shutil.copy2(job.image_path, input_dir / job.image_path.name)

    files_to_copy = [
        BASE_DIR / "script.json",
        BASE_DIR / "output.mp4",
        BASE_DIR / "final_output.mp4",
        MEMORY_FILE,
    ]
    for src in files_to_copy:
        if src.exists():
            shutil.copy2(src, artifacts_dir / src.name)

    dir_map = {
        GENERATED_FRAMES_DIR: artifacts_dir / "generated_frames",
        GENERATED_AUDIO_DIR: artifacts_dir / "generated_audio",
        GENERATED_VIDEOS_DIR: artifacts_dir / "generated_videos",
    }
    for src, dst in dir_map.items():
        if src.exists():
            shutil.copytree(src, dst, dirs_exist_ok=True)

    result_src = job.result_path if job.result_path and job.result_path.exists() else _resolve_final_video()
    archived_result = None
    if result_src and result_src.exists():
        archived_result = result_dir / result_src.name
        shutil.copy2(result_src, archived_result)

    manifest = {
        "job_id": job.id,
        "created_at": datetime.now().isoformat(),
        "status": job.status.value,
        "dry_run": DRY_RUN,
        "result_file": str(archived_result) if archived_result else None,
    }
    _write_json(run_dir / "manifest.json", manifest)
    return run_dir.resolve(), archived_result.resolve() if archived_result else None


def _finalize_success(job_id: str, response_text: str, final_video: Path) -> None:
    job = _get_job(job_id)
    job.status = JobStatus.completed
    job.result_path = final_video.resolve()
    job.agent_response = response_text
    _save_job(job)

    _push(job_id, "Archiving outputs")
    archive_dir, archived_result = _archive_job_outputs(job)

    job = _get_job(job_id)
    job.archive_dir = archive_dir
    if archived_result:
        job.result_path = archived_result
    _save_job(job)

    if CLEAN_AFTER_ARCHIVE:
        _cleanup_workspace_outputs()
        _push(job_id, "Workspace cleaned")

    _push(job_id, "Video ready")


async def _simulate_job(job_id: str) -> None:
    for phase in _load_sample_notifications():
        _push(job_id, phase)
        await asyncio.sleep(0.2)

    final_video = _materialize_dry_run_sample()
    _finalize_success(job_id, "Dry run sample replay complete", final_video)


async def _run_job(job_id: str) -> None:
    job = _get_job(job_id)
    job.status = JobStatus.running
    _save_job(job)
    _push(job_id, "Agent started")

    if DRY_RUN:
        await _simulate_job(job_id)
        return

    seen_ids: set[int] = set()
    seen_status: Dict[int, str] = {}

    try:
        query = _build_query(job.message, job.image_path)
        task = asyncio.create_task(asyncio.to_thread(_run_agent, query))

        while not task.done():
            _pump_memory(job_id, seen_ids, seen_status)
            await asyncio.sleep(1.0)

        response_text = await task
        _pump_memory(job_id, seen_ids, seen_status)

        final_video = _extract_video_path(response_text) or _resolve_final_video()
        if not final_video:
            raise FileNotFoundError("Final mp4 not found after pipeline completion")

        _finalize_success(job_id, response_text, final_video)
    except Exception as exc:
        job = _get_job(job_id)
        job.status = JobStatus.failed
        job.error = str(exc)
        _save_job(job)
        _push(job_id, "Job failed")


def _save_upload(job_id: str, image: UploadFile) -> Path:
    suffix = Path(image.filename or "reference.jpg").suffix or ".jpg"
    out = UPLOADS_DIR / f"{job_id}{suffix}"
    with out.open("wb") as f:
        shutil.copyfileobj(image.file, f)
    return out.resolve()


@app.post("/start")
async def start_job(
    background_tasks: BackgroundTasks,
    message: str = Form(..., description="Main instruction including style details"),
    image: Optional[UploadFile] = File(None, description="Optional reference image"),
):
    with lock:
        active = any(j.status in (JobStatus.queued, JobStatus.running) for j in jobs.values())
    if active:
        raise HTTPException(status_code=409, detail="Another job is already running")

    job_id = str(uuid.uuid4())
    image_path = _save_upload(job_id, image) if image else None

    job = Job(
        id=job_id,
        status=JobStatus.queued,
        message=message,
        image_path=image_path,
    )
    _save_job(job)
    _push(job_id, "Job queued")

    background_tasks.add_task(_run_job, job_id)
    return {"job_id": job_id, "status": job.status}


@app.get("/jobs/{job_id}")
async def get_job(job_id: str):
    job = _get_job(job_id)
    return {
        "id": job.id,
        "status": job.status,
        "message": job.message,
        "image_path": str(job.image_path) if job.image_path else None,
        "has_result": job.result_path is not None,
        "result_path": str(job.result_path) if job.result_path else None,
        "archive_dir": str(job.archive_dir) if job.archive_dir else None,
        "result_endpoint": f"/result/{job.id}" if job.result_path else None,
        "agent_response": job.agent_response,
        "error": job.error,
    }


@app.get("/notifications/{job_id}")
async def get_notifications(job_id: str, after: int = 0):
    job = _get_job(job_id)
    updates = [n for n in job.notifications if n.seq > after]
    return {"job_id": job_id, "notifications": updates}


@app.get("/result/{job_id}")
async def get_result(job_id: str):
    job = _get_job(job_id)
    if job.status != JobStatus.completed or not job.result_path:
        raise HTTPException(status_code=409, detail="Result not ready")
    if not job.result_path.exists():
        raise HTTPException(status_code=500, detail="Result file missing")

    return FileResponse(str(job.result_path), media_type="video/mp4", filename=job.result_path.name)


@app.get("/health")
async def health():
    return {
        "status": "ok",
        "dry_run": DRY_RUN,
        "clean_after_archive": CLEAN_AFTER_ARCHIVE,
        "dry_run_sample_dir": str(SAMPLE_DRY_RUN_DIR),
    }


if __name__ == "__main__":
    import uvicorn

    host = os.getenv("API_HOST", "0.0.0.0")
    port = int(os.getenv("API_PORT", "8000"))
    reload = os.getenv("API_RELOAD", "0") == "1"

    if reload:
        target = "main:app" if Path.cwd().resolve() == Path(__file__).resolve().parent else "api.main:app"
        uvicorn.run(target, host=host, port=port, reload=True)
    else:
        uvicorn.run(app, host=host, port=port, reload=False)
