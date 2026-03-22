import json
import os
import wave
import sys
import subprocess
from google import genai
from google.genai import types
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def wave_file(filename, pcm, channels=1, rate=24000, sample_width=2):
    """
    Saves PCM data to a wave file.
    Default rate for Gemini TTS is 24kHz.
    """
    with wave.open(filename, "wb") as wf:
        wf.setnchannels(channels)
        wf.setsampwidth(sample_width)
        wf.setframerate(rate)
        wf.writeframes(pcm)

def convert_to_wav(input_path, output_path):
    """
    Converts any audio file to .wav using ffmpeg.
    Useful if some audios are .mp3 etc.
    """
    if input_path == output_path:
        # Don't overwrite if same name but different ext
        return False
    
    cmd = [
        "ffmpeg", "-y",
        "-i", input_path,
        "-acodec", "pcm_s16le",
        "-ar", "24000",
        "-ac", "1",
        output_path
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    return result.returncode == 0

def convert_dir_to_wav(directory):
    """
    Scans a directory for audio files and converts them to .wav
    """
    if not os.path.exists(directory):
        return {"success": False, "error": f"Directory {directory} not found."}
    
    files = os.listdir(directory)
    converted = []
    for f in files:
        if f.lower().endswith((".mp3", ".m4a", ".ogg", ".aac", ".flac")) and not f.endswith(".wav"):
            input_path = os.path.join(directory, f)
            output_name = os.path.splitext(f)[0] + ".wav"
            output_path = os.path.join(directory, output_name)
            if convert_to_wav(input_path, output_path):
                converted.append(f)
    
    return {"success": True, "message": f"Converted {len(converted)} files to .wav", "converted_files": converted}

def get_wav_duration(filename):
    """Returns the duration of a wav file in seconds."""
    try:
        with wave.open(filename, "rb") as wf:
            frames = wf.getnframes()
            rate = wf.getframerate()
            duration = frames / float(rate)
            return round(duration, 2)
    except:
        return 0

def generate_sense_audio(sense_id, text, voice_name="Kore"):
    # Initialize client
    api_key = os.getenv("VITE_GEMINI_API_KEY")
    client = genai.Client(api_key=api_key)

    # Ensure output directory exists
    audio_dir = "generated_audio"
    if not os.path.exists(audio_dir):
        os.makedirs(audio_dir)

    output_filename = os.path.join(audio_dir, f"sense_{sense_id}.wav")

    # Define the advanced, improved Vox-style prompt
    prompt = f"""
# VOICE PROFILE: The Global Narrator (Vox Documentary Style)
## CHARACTER: 
A seasoned investigative journalist. Authoritative, intelligent, and deeply engaging. 
Not overly dramatic, but serious and analytical.

## WORLD: 
A high-end recording booth. The air is dry and quiet. Every syllable is crisp.

## EMOTIONAL BEATS:
* Informative and Precise: Speak with the weight of facts.
* Engaging Curiosity: Slight lift in tone when presenting a question or a "hook".
* Grave Reality: Drop the pitch slightly for serious or tragic segments.

## PACING & FLOW:
* Moderate-Slow Pacing: Allow space for the viewer to process complex information.
* Mid-Sentence Pauses: Use natural, slight pauses after commas for clarity.
* Emphasis: Subtle stress on crucial dates, figures, and names.

### TRANSCRIPT TO PERFORM:
{text}
"""

    print(f"Generating audio for sense {sense_id}...")
    
    try:
        # Use voice model from env if available
        model_name = os.getenv("VITE_GEMINI_VOICE_MODEL_AUDIO") or os.getenv("VITE_GEMINI_VISION_MODEL") or "gemini-2.0-flash"
        
        response = client.models.generate_content(
            model=model_name,
            contents=prompt,
            config=types.GenerateContentConfig(
                response_modalities=["AUDIO"],
                speech_config=types.SpeechConfig(
                    voice_config=types.VoiceConfig(
                        prebuilt_voice_config=types.PrebuiltVoiceConfig(
                            voice_name=voice_name,
                        )
                    )
                ),
            )
        )

        # Get audio data
        audio_part = response.candidates[0].content.parts[0]
        if hasattr(audio_part, 'inline_data'):
            data = audio_part.inline_data.data
            wave_file(output_filename, data)
            duration = get_wav_duration(output_filename)
            return {
                "success": True, 
                "message": f"Saved segment {sense_id} audio to {output_filename}", 
                "audio_path": output_filename,
                "duration": duration,
                "segment_id": sense_id
            }
        else:
            return {"success": False, "error": "No audio data found in response."}

    except Exception as e:
        return {"success": False, "error": str(e)}

def generate_all_audio(script_path="script.json", voice_name="Kore"):
    """
    Reads script.json, and generates audio for each sense in it.
    """
    if not os.path.exists(script_path):
        return {"success": False, "error": f"Script file {script_path} not found."}

    try:
        with open(script_path, "r") as f:
            script_data = json.load(f)
    except Exception as e:
        return {"success": False, "error": f"Failed to read {script_path}: {str(e)}"}

    segments = script_data.get("segments", [])
    if not segments:
        return {"success": False, "error": "No segments found in script."}

    results = []
    durations = {}
    for seg in segments:
        segment_id = seg.get("segment_id")
        text = seg.get("narrator_speech")
        if segment_id is not None and text:
            res = generate_sense_audio(segment_id, text, voice_name)
            results.append(res)
            if res.get("success"):
                durations[segment_id] = res.get("duration")
        else:
            results.append({"success": False, "segment_id": segment_id, "error": "Missing segment_id or narrator_speech"})

    success_count = sum(1 for r in results if r.get("success"))
    return {
        "success": True, 
        "message": f"Processed {len(segments)} segments, {success_count} successful.",
        "results": results,
        "durations": durations
    }


def full_process(script_path="script.json", voice_name="Kore"):
    """
    1. Generates all audio files from script.json
    2. Merges them with videos in generated_videos/
    3. Produces final output.mp4
    """
    print("Step 1: Generating all audio files...")
    audio_res = generate_all_audio(script_path, voice_name)
    if not audio_res.get("success"):
        return audio_res
    
    print("Step 2: Merging audio with videos and concatenating...")
    merge_res = merge_audio_and_video()
    return merge_res

def merge_audio_and_video(videos_dir="generated_videos", audio_dir="generated_audio", output_final="output.mp4"):
    """
    Merges all sense_i.mp4 from videos_dir/ with sense_i.wav from audio_dir/
    and then concatenates them.
    """
    temp_dir = "temp_merges"
    if not os.path.exists(videos_dir):
        return {"success": False, "error": f"Folder {videos_dir} not found."}
    
    if not os.path.exists(temp_dir):
        os.makedirs(temp_dir)

    # Find all videos
    video_files = [f for f in os.listdir(videos_dir) if f.startswith("sense_") and f.endswith(".mp4")]
    
    def extract_number(filename):
        try:
            name_part = filename.split(".")[0]
            num_part = name_part.split("_")[-1]
            return int(num_part)
        except:
            return 999

    video_files.sort(key=extract_number)
    merged_files = []

    for video_file in video_files:
        sense_id = extract_number(video_file)
        audio_file = f"sense_{sense_id}.wav"
        audio_path = os.path.join(audio_dir, audio_file)
        video_path = os.path.join(videos_dir, video_file)
        
        temp_output = os.path.join(temp_dir, f"ready_{sense_id}.mp4")
        
        if os.path.exists(audio_path):
            print(f"Merging sense {sense_id} video (bg) and VO (primary)...")
            
            # Check if video has an audio stream to mix with
            probe_cmd = ["ffprobe", "-v", "error", "-select_streams", "a", "-show_entries", "stream=index", "-of", "csv=p=0", video_path]
            has_audio = subprocess.run(probe_cmd, capture_output=True, text=True).stdout.strip() != ""
            
            if has_audio:
                # MIX: Video audio at 30% volume, VO at 100%
                cmd = [
                    "ffmpeg", "-y",
                    "-stream_loop", "-1",
                    "-i", video_path,
                    "-i", audio_path,
                    "-filter_complex", "[0:a]volume=0.3[bg];[1:a]volume=1.0[vo];[bg][vo]amix=inputs=2:duration=shortest[aout]",
                    "-map", "0:v",
                    "-map", "[aout]",
                    "-c:v", "libx264",
                    "-c:a", "aac",
                    "-shortest",
                    temp_output
                ]
            else:
                # No audio in video, just use VO
                cmd = [
                    "ffmpeg", "-y",
                    "-stream_loop", "-1",
                    "-i", video_path,
                    "-i", audio_path,
                    "-map", "0:v",
                    "-map", "1:a",
                    "-c:v", "libx264",
                    "-c:a", "aac",
                    "-shortest",
                    temp_output
                ]
            subprocess.run(cmd, capture_output=True, text=True)
        else:
            print(f"Warning: VO not found for sense {sense_id}. Using original video.")
            cmd = ["ffmpeg", "-y", "-i", video_path, "-c", "copy", temp_output]
            subprocess.run(cmd, capture_output=True, text=True)

        if os.path.exists(temp_output):
            merged_files.append(temp_output)

    if not merged_files:
        return {"success": False, "error": "No segments found to compile."}

    # Concatenate
    list_file_path = os.path.join(temp_dir, "concat_list.txt")
    with open(list_file_path, "w") as f:
        for m in merged_files:
            f.write(f"file '{os.path.basename(m)}'\n")

    print("Concatenating segments...")
    concat_cmd = [
        "ffmpeg", "-y",
        "-f", "concat",
        "-safe", "0",
        "-i", "concat_list.txt",
        "-c", "copy",
        "final_output.mp4"
    ]
    result = subprocess.run(concat_cmd, cwd=temp_dir, capture_output=True, text=True)
    
    if os.path.exists(os.path.join(temp_dir, "final_output.mp4")):
        if os.path.exists(output_final):
            os.remove(output_final)
        os.rename(os.path.join(temp_dir, "final_output.mp4"), output_final)
        return {"success": True, "message": "Successfully merged and compiled final video.", "output_file": os.path.abspath(output_final)}
    else:
        return {"success": False, "error": f"Concat failed: {result.stderr}"}

def get_all_durations(audio_dir="generated_audio"):
    """Scans the audio directory and returns a dictionary of sense_id: duration."""
    if not os.path.exists(audio_dir):
        return {"success": False, "error": f"Directory {audio_dir} not found."}
    
    files = [f for f in os.listdir(audio_dir) if f.startswith("sense_") and f.endswith(".wav")]
    durations = {}
    
    for f in files:
        try:
            # Extract sense_id from "sense_1.wav"
            sense_id = int(f.split("_")[1].split(".")[0])
            path = os.path.join(audio_dir, f)
            durations[sense_id] = get_wav_duration(path)
        except:
            continue
            
    return {"success": True, "durations": durations}

if __name__ == "__main__":
    try:
        # Default to full_process if no params or empty params
        params = json.loads(sys.argv[1]) if len(sys.argv) > 1 else {}
        action = params.get("action", "full_process")

        if action == "generate":
            sense_id = params.get("sense_id")
            text = params.get("text")
            voice_name = params.get("voice_name", "Kore")
            
            if sense_id is None or text is None:
                print(json.dumps({"error": "sense_id and text are required for generate action"}))
            else:
                result = generate_sense_audio(sense_id, text, voice_name)
                print(json.dumps(result))

        elif action == "generate_all":
            script_path = params.get("script_path", "script.json")
            voice_name = params.get("voice_name", "Kore")
            result = generate_all_audio(script_path, voice_name)
            print(json.dumps(result))

        elif action == "full_process":
            script_path = params.get("script_path", "script.json")
            voice_name = params.get("voice_name", "Kore")
            result = full_process(script_path, voice_name)
            print(json.dumps(result))

        elif action == "convert_dir":
            directory = params.get("directory", "generated_audio")
            result = convert_dir_to_wav(directory)
            print(json.dumps(result))

        elif action == "merge":
            result = merge_audio_and_video()
            print(json.dumps(result))

        elif action == "get_durations":
            audio_dir = params.get("audio_dir", "generated_audio")
            result = get_all_durations(audio_dir)
            print(json.dumps(result))

        else:
            print(json.dumps({"error": f"Unknown action: {action}"}))

    except Exception as e:
        print(json.dumps({"error": str(e)}))

