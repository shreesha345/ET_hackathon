# ET Agent API

This document is the full runtime guide for the API in `api/main.py`.
If process memory/context is lost, recover by reading this file first.

## Purpose

The API runs the video pipeline through `Agent.py` and exposes:
- Job start endpoint (`message` + optional style reference image)
- Pollable short progress notifications
- Final video download endpoint
- Dry-run simulation mode that does not consume model/API credits

## Run

From `D:\Coding\ET_agent\api`:

```powershell
uv run main.py
```

## Environment Variables

Set in `D:\Coding\ET_agent\.env`.

- `DRY_RUN=0|1`
  - `0`: real pipeline via `Agent.py`
  - `1`: replay sample artifacts from `samples/dry_run` (no credit usage)
- `CLEAN_AFTER_ARCHIVE=0|1`
  - `1` (default): after successful archive, cleans generated workspace outputs
- `NOTIFICATION_INTERVAL_SECONDS=<float>`
  - default interval between dry-run notifications and real-mode heartbeat notifications
  - default: `10`
- `REAL_MEMORY_POLL_SECONDS=<float>`
  - poll interval for reading `memory.json` during real mode
  - default: `1`
- `API_HOST` (default `0.0.0.0`)
- `API_PORT` (default `8000`)
- `API_RELOAD=0|1` (default `0`)
- `CORS_ALLOW_ORIGINS`
  - comma-separated allowed frontend origins
  - default: `http://localhost:5173,http://127.0.0.1:5173,http://localhost:8080,http://127.0.0.1:8080`

## Input Contract (`POST /start`)

Only two primary inputs are required by design:
- `message` (required)
  - include article URL + style instruction text in this field
- `image` (optional)
  - style/reference image upload
- `image_url` (optional)
  - style/reference image URL (used when a built-in style thumbnail is selected)

Optional testing input:
- `notification_interval_seconds` (optional, `> 0`)
  - overrides notification interval for that job

Rules:
- Only one active job at a time
- If an `image` is provided, its path is appended to the agent query as style reference context

## Endpoints

### `POST /start`
Starts a job.

Response:
```json
{
  "job_id": "<uuid>",
  "status": "queued"
}
```

### `GET /jobs/{job_id}`
Returns current job state and output metadata.

Response fields:
- `id`, `status`, `message`
- `image_path`
- `has_result`
- `result_path`
- `archive_dir`
- `notification_interval_seconds`
- `result_endpoint`
- `agent_response`
- `error`

### `GET /notifications/{job_id}?after=<seq>`
Returns short 2–5 word status updates after the given sequence ID.

Response:
```json
{
  "job_id": "<uuid>",
  "notifications": [
    {"seq": 1, "text": "Job queued"},
    {"seq": 2, "text": "Agent started"}
  ]
}
```

### `GET /result/{job_id}`
Returns the final video as `video/mp4` when job is completed.

### `GET /health`
Returns service and config state:
- `dry_run`
- `clean_after_archive`
- `default_notification_interval_seconds`
- `real_memory_poll_seconds`
- `dry_run_sample_dir`

## Real Mode (`DRY_RUN=0`)

Flow:
1. API starts job and runs `Agent.py` in background thread.
2. API tails `memory.json` and maps each step to short frontend notifications.
3. API resolves final video path from:
   - explicit path in agent text response, or
   - fallback candidates: `output.mp4`, `final_output.mp4`, `generated_videos/output.mp4`, `generated_videos/final_output.mp4`.
4. API archives artifacts into one run folder.
5. If `CLEAN_AFTER_ARCHIVE=1`, workspace generated outputs are cleaned.

## Dry Mode (`DRY_RUN=1`)

Dry-run does not call model/tool APIs.

Flow:
1. Emits notifications from `samples/dry_run/notifications.json` at configured interval.
2. Copies sample artifacts from `samples/dry_run` into workspace output locations.
3. Finalizes job exactly like real mode (archive + optional cleanup).

Sample source folder:
- `samples/dry_run/script.json`
- `samples/dry_run/memory.json`
- `samples/dry_run/output.mp4` (or equivalent final video)
- `samples/dry_run/generated_frames/*`
- `samples/dry_run/generated_audio/*`
- `samples/dry_run/generated_videos/*`
- `samples/dry_run/notifications.json`

## Output and Archive Layout

Runtime generation folders (workspace root):
- `generated_frames/`
- `generated_audio/`
- `generated_videos/`
- root-level `script.json`, `output.mp4`, `final_output.mp4`

Per completed job archive:
- `job_runs/<timestamp>_<jobid>/input/`
- `job_runs/<timestamp>_<jobid>/artifacts/`
- `job_runs/<timestamp>_<jobid>/result/`
- `job_runs/<timestamp>_<jobid>/manifest.json`

When cleanup is enabled, runtime generation folders are cleared after archiving.

## Frontend Polling Pattern

1. Call `POST /start`.
2. Poll `GET /notifications/{job_id}?after=<last_seq>`.
3. Poll `GET /jobs/{job_id}` until `status` is `completed` or `failed`.
4. When completed, play/download video from `GET /result/{job_id}`.

## Recovery Rule

If runtime context/memory is reset:
1. Read this file (`api/README.md`).
2. Check `api/main.py` endpoint signatures against this document.
3. Check `.env` values.
4. Verify sample assets exist under `samples/dry_run` for dry-run mode.

This file is the canonical operational description for API behavior.
