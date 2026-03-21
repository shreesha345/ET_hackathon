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
from pathlib import Path
from google import genai
from google.genai import types
import os
from dotenv import load_dotenv

load_dotenv()

# ── Auth: API Key ─────────────────────────────────────────────────────────────
# Uses the key that successfully worked for the user's manual test
API_KEY = os.getenv("VITE_GEMINI_API_KEY")

def load_image(file_path: str) -> types.Image:
    """Reads a local image file and returns a genai Image object."""
    path = Path(file_path)
    
    # Auto-detect mime type from extension
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
    
    return types.Image(
        image_bytes=image_bytes,
        mime_type=mime_type,
    )

def generate_video(start_frame: str, end_frame: str, prompt: str, output_path: str = None) -> dict:
    try:
        client = genai.Client(api_key=API_KEY)

        # 1. Load starting and ending frames
        first_image = load_image(start_frame)
        last_image = load_image(end_frame)

        # 2. Determine output path
        if not output_path:
            videos_dir = os.path.join(os.path.dirname(__file__), "..", "generated_videos")
            os.makedirs(videos_dir, exist_ok=True)
            base_name = f"{Path(start_frame).stem}_to_{Path(end_frame).stem}.mp4"
            output_path = os.path.join(videos_dir, base_name)
        else:
            os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
            
        full_prompt = f"A cinematic transition between the two scenes. {prompt}"

        # 3. Call Veo 3.1 directly as configured
        operation = client.models.generate_videos(
            model="veo-3.1-generate-preview",
            prompt=full_prompt,
            image=first_image,
            config=types.GenerateVideosConfig(
                last_frame=last_image,
                aspect_ratio="9:16",      # Using 9:16 to match the storyboard portrait orientation
                duration_seconds="8",     # Must be 8 for interpolation per user spec
                number_of_videos=1,
            ),
        )

        # 4. Polling for completion
        max_attempts = 60  # ~15 minutes
        attempts = 0
        while not operation.done:
            attempts += 1
            if attempts > max_attempts:
                return {"success": False, "error": "Video generation timed out."}
            time.sleep(15)
            operation = client.operations.get(operation)

        # 5. Save the final video
        if operation.response and operation.response.generated_videos:
            generated_video = operation.response.generated_videos[0]
            
            # Download file context
            client.files.download(file=generated_video.video)
            
            # Save safely to disk
            abs_out_path = os.path.abspath(output_path)
            generated_video.video.save(abs_out_path)
            
            return {
                "success": True,
                "video_path": abs_out_path,
                "start_frame": start_frame,
                "end_frame": end_frame,
                "prompt": full_prompt
            }
        else:
            return {"success": False, "error": "Generation failed or returned no video."}

    except Exception as e:
        return {"success": False, "error": str(e)}


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(json.dumps({"success": False, "error": "No parameters provided."}))
        sys.exit(1)

    try:
        params = json.loads(sys.argv[1])
        start = params.get("start_frame")
        end = params.get("end_frame")
        p = params.get("prompt", "")
        out = params.get("output_path")

        if not start or not end:
            print(json.dumps({"success": False, "error": "Missing 'start_frame' or 'end_frame'."}))
            sys.exit(1)

        result = generate_video(start, end, p, out)
        print(json.dumps(result, indent=2))
        
    except json.JSONDecodeError as e:
        print(json.dumps({"success": False, "error": f"Invalid JSON input: {e}"}))
        sys.exit(1)
    except Exception as e:
        print(json.dumps({"success": False, "error": str(e)}))
        sys.exit(1)