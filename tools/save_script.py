import json
import os
import sys

def save_script(script_data: dict) -> dict:
    """Saves the provided script JSON to script.json."""
    try:
        output_file = os.path.join(os.path.dirname(__file__), "..", "script.json")
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(script_data, f, indent=2, ensure_ascii=False)
        return {"success": True, "message": f"Successfully saved to {os.path.abspath(output_file)}"}
    except Exception as e:
        return {"success": False, "error": str(e)}

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(json.dumps({"success": False, "error": "No input provided."}))
        sys.exit(1)

    try:
        params = json.loads(sys.argv[1])
        # The tool receives a dictionary of parameters.
        # It's called with 'script_data' as the key.
        script_data = params.get("script_data", params)
        result = save_script(script_data)
        print(json.dumps(result))
    except json.JSONDecodeError as e:
        print(json.dumps({"success": False, "error": f"Invalid JSON input: {e}"}))
        sys.exit(1)
