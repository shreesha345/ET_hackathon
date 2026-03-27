@echo off
setlocal

cd /d "%~dp0"

echo [1/5] Checking uv installation...
where uv >nul 2>nul
if errorlevel 1 (
  echo ERROR: 'uv' is not installed or not in PATH.
  echo Install: https://docs.astral.sh/uv/
  exit /b 1
)

echo [2/5] Ensuring .env exists...
if not exist ".env" (
  if exist ".env.example" (
    copy /Y ".env.example" ".env" >nul
    echo Created .env from .env.example. Fill required keys before real runs.
  ) else (
    echo ERROR: .env and .env.example both missing.
    exit /b 1
  )
)

echo [3/5] Installing/syncing dependencies...
uv sync
if errorlevel 1 (
  echo ERROR: uv sync failed.
  exit /b 1
)

echo [4/5] Creating runtime folders...
if not exist "generated_frames" mkdir "generated_frames"
if not exist "generated_audio" mkdir "generated_audio"
if not exist "generated_videos" mkdir "generated_videos"
if not exist "job_runs" mkdir "job_runs"
if not exist "uploads" mkdir "uploads"

echo [5/5] Starting API server...
cd api
uv run main.py

endlocal
