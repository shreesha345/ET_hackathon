import json
import os
import sys

def load_script() -> dict:
    """Loads the script JSON from script.json."""
    try:
        input_file = os.path.join(os.path.dirname(__file__), "..", "script.json")
        if not os.path.exists(input_file):
            return {"success": False, "error": f"File {os.path.abspath(input_file)} not found."}
        with open(input_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        return {"success": True, "script_data": data}
    except Exception as e:
        return {"success": False, "error": str(e)}

if __name__ == "__main__":
    # No input parameters needed, but the agent system passes a JSON {}
    result = load_script()
    print(json.dumps(result))
