"""
cleanup.py — Safely remove generated artifacts created by the Agent.

What it deletes (allow‑list):
- generated_frames/*
- generated_audio/*
- generated_videos/*
- extra/* (often used for temp assets)
- script.json (active project script)

It never touches source code, skills, tools, or this script itself.
"""

from __future__ import annotations

import argparse
import shutil
from pathlib import Path


ALLOW_DIRS = [
    "generated_frames",
    "generated_audio",
    "generated_videos",
]

ALLOW_FILES = [
    "script.json",
]


def purge_dir(path: Path) -> int:
    """Delete all contents of path if it exists; keep the folder itself."""
    if not path.exists():
        return 0
    removed = 0
    for item in path.iterdir():
        try:
            if item.is_dir():
                shutil.rmtree(item)
            else:
                item.unlink()
            removed += 1
        except Exception as exc:  # pragma: no cover - best‑effort cleanup
            print(f"[WARN] Could not remove {item}: {exc}")
    return removed


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Clean generated artifacts produced by the Agent (frames, audio, videos, extras)."
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be deleted without removing files.",
    )
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parent
    total_removed = 0

    for rel in ALLOW_DIRS:
        target = repo_root / rel
        if not target.exists():
            continue
        if args.dry_run:
            contents = list(target.iterdir())
            if contents:
                print(f"[DRY] {target} -> would remove {len(contents)} item(s)")
            continue
        removed = purge_dir(target)
        if removed:
            print(f"[OK] Cleared {removed} item(s) in {target}")
        total_removed += removed

    # Remove allow-listed files (except memory.json which is truncated separately)
    for rel in ALLOW_FILES:
        target = repo_root / rel
        if not target.exists():
            continue
        if args.dry_run:
            print(f"[DRY] {target} -> would delete file")
            continue
        try:
            target.unlink()
            total_removed += 1
            print(f"[OK] Deleted {target}")
        except Exception as exc:  # pragma: no cover
            print(f"[WARN] Could not delete {target}: {exc}")

    # Truncate memory.json instead of deleting
    mem_file = repo_root / "memory.json"
    if mem_file.exists():
        if args.dry_run:
            print(f"[DRY] {mem_file} -> would truncate file to empty JSON []")
        else:
            try:
                mem_file.write_text("[]\n", encoding="utf-8")
                print(f"[OK] Truncated {mem_file}")
            except Exception as exc:  # pragma: no cover
                print(f"[WARN] Could not truncate {mem_file}: {exc}")

    if not args.dry_run:
        print(f"Done. Removed {total_removed} item(s).")
    else:
        print("Dry run complete. No files were deleted.")


if __name__ == "__main__":
    main()
