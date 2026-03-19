import sys
import json

def add(a, b):
    return a + b

if __name__ == "__main__":
    try:
        # Expect parameters as JSON string
        params = json.loads(sys.argv[1])
        a = float(params.get("a", 0))
        b = float(params.get("b", 0))
        result = add(a, b)
        print(json.dumps({"result": result}))
    except Exception as e:
        print(json.dumps({"error": str(e)}))
