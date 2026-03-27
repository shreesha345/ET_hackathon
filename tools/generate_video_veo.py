"""
generate_video_veo.py — Video Generation Engine for Veo 3.1
===========================================================
Generates a video clip (interpolation) between two frames using
Google GenAI (Veo 3.1).

Usage:
    python generate_video_veo.py '{"start_frame": "frame_1.jpg", "end_frame": "frame_2.jpg", "prompt": "...", "output_path": "scene_1.mp4"}'
"""

import sys
import json
import time
import base64
from typing import Optional
from pathlib import Path
from google import genai  # type: ignore[import-not-found]
from google.genai import types  # type: ignore[import-not-found]
import os
from dotenv import load_dotenv  # type: ignore[import-not-found]

load_dotenv()

# ── Auth: API Key ─────────────────────────────────────────────────────────────
API_KEY = os.getenv("VITE_VERTEX_API_KEY")

def load_image(file_path: str) -> types.Image:
    """Reads a local image file and returns a genai Image object."""
    path = Path(file_path)
    mime_map = {
        ".png":  "image/png",
        ".jpg":  "image/jpeg",
        ".jpeg": "image/jpeg",
        ".webp": "image/webp",
    }
    mime_type = mime_map.get(path.suffix.lower(), "image/jpeg")
    if not os.path.exists(path):
        raise FileNotFoundError(f"Image not found at {path}")
    with open(path, "rb") as f:
        image_bytes = f.read()
    return types.Image(image_bytes=image_bytes, mime_type=mime_type)

def generate_video(start_frame: str, end_frame: Optional[str] = None, prompt: str = "", speech: Optional[str] = None, output_path: Optional[str] = None, duration_seconds: int = 8) -> dict:
    try:
        # 1. Initialize GenAI Client
        use_vertex = os.getenv("VITE_GOOGLE_GENAI_USE_VERTEXAI", "true").lower() == "true"
        
        if use_vertex:
            # Vertex AI mode: project and location are required, api_key must be None
            client = genai.Client(
                project=os.getenv("VITE_GOOGLE_CLOUD_PROJECT", "agentic-project-488820"),
                location=os.getenv("VITE_GOOGLE_CLOUD_LOCATION", "us-central1"),
                vertexai=True
            )
        else:
            # Gemini API mode: api_key is required, project and location must be None
            client = genai.Client(
                api_key=API_KEY
            )

        # 2. Adjust duration to supported values (4, 6, 8 seconds for Veo 3.1)
        supported_durations = [4, 6, 8]
        if duration_seconds not in supported_durations:
            new_duration = min(supported_durations, key=lambda x: abs(x - duration_seconds))
            # Progress logs go to stderr so stdout stays valid JSON for the manager
            print(f"Warning: Duration {duration_seconds}s not supported by Veo 3.1. Snapping to {new_duration}s.", file=sys.stderr)
            duration_seconds = new_duration

        # 3. Load frames — require distinct start/end frames
        if not end_frame:
            raise ValueError("'end_frame' is required and must be different from 'start_frame'.")
        if end_frame == start_frame:
            raise ValueError("'start_frame' and 'end_frame' must be different images to avoid static outputs.")
        first_image = load_image(start_frame)
        last_image = load_image(end_frame)

        # 3. Determine output path
        if not output_path:
            videos_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "generated_videos"))
            os.makedirs(videos_dir, exist_ok=True)
            base_name = f"{Path(start_frame).stem}_to_{Path(end_frame).stem}.mp4"
            output_path = os.path.join(videos_dir, base_name)
        else:
            os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
            
        if start_frame == end_frame:
            full_prompt = f"A cinematic video starting from the reference image. {prompt}"
        else:
            full_prompt = f"A cinematic transition between the two scenes. {prompt}"
        # Sound design only; no narration/voices.
        full_prompt += "\n\nAdd rich ambient and foley sound effects that match the motion; absolutely no narration or voices."

        # 4. Prompt & Source Setup
        source = types.GenerateVideosSource(
            prompt=full_prompt,
            image=first_image
        )

        config = types.GenerateVideosConfig(
            last_frame=last_image,
            aspect_ratio="9:16",
            number_of_videos=1,
            duration_seconds=int(duration_seconds),
            person_generation="allow_all",
            generate_audio=True,  # enable ambient SFX (no narration)
            resolution="720p",
            seed=0,
        )

        # 5. Generate the video generation request
        print(f"Generating Vertex AI Video for {output_path} (Duration: {duration_seconds}s)...", file=sys.stderr)
        operation = client.models.generate_videos(
            model="veo-3.1-generate-001", 
            source=source, 
            config=config
        )

        # 6. Polling for completion
        while not operation.done:
            print(f"Video for {os.path.basename(output_path)} is still in progress... Check again in 15 seconds. (Done: {operation.done})", file=sys.stderr)
            time.sleep(15)
            operation = client.operations.get(operation)

        print("Operation finished.", file=sys.stderr)
        # Try to print some info about the operation if it supports it
        try:
            print(f"DEBUG: Full Operation Object: {operation}", file=sys.stderr)
        except:
            pass

        # 7. Extract and Save Result
        response = operation.result
        
        if response and response.generated_videos and len(response.generated_videos) > 0:
            generated_video = response.generated_videos[0]
            
            # Save safely to disk
            abs_out_path = os.path.abspath(output_path)
            generated_video.video.save(abs_out_path)
            
            return {
                "success": True,
                "video_path": abs_out_path,
                "start_frame": start_frame,
                "end_frame": end_frame,
                "duration": duration_seconds,
                "prompt": full_prompt
            }
        else:
            # Check for error in operation metadata
            error_msg = "Generation completed but returned no video response."
            
            # Safely check for errors in operation or metadata
            try:
                op_json = str(operation)
                if "partial_errors" in op_json or "error" in op_json:
                    error_msg += f" Details: {op_json}"
            except:
                pass
                
            return {"success": False, "error": error_msg}

    except Exception as e:
        import traceback
        return {"success": False, "error": f"{str(e)}\n{traceback.format_exc()}"}


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(json.dumps({"success": False, "error": "No parameters provided."}))
        sys.exit(1)

    try:
        params = json.loads(sys.argv[1])
        start = params.get("start_frame")
        end = params.get("end_frame")
        p = params.get("prompt", "")
        speech = params.get("speech", None)
        out = params.get("output_path")
        dur = params.get("duration_seconds", 8) # Default to 8 if not provided

        if not start:
            print(json.dumps({"success": False, "error": "Missing 'start_frame' or 'end_frame'."}))
            sys.exit(1)

        result = generate_video(start, end, p, speech, out, dur)
        print(json.dumps(result, indent=2))

        
    except json.JSONDecodeError as e:
        print(json.dumps({"success": False, "error": f"Invalid JSON input: {e}"}))
        sys.exit(1)
    except Exception as e:
        print(json.dumps({"success": False, "error": str(e)}))
        sys.exit(1)
