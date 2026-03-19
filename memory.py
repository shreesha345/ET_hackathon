import json
import os

class Memory:
    """
    A simple memory/scratchpad for the agent to track its steps and status.
    """
    def __init__(self, storage_file="memory.json"):
        self.storage_file = storage_file
        self.steps = []
        self.load_memory()

    def add_step(self, step_description, status="pending"):
        """Adds a new step to the memory."""
        step = {
            "id": len(self.steps) + 1,
            "description": step_description,
            "status": status
        }
        self.steps.append(step)
        self.save_memory()
        return step["id"]

    def update_step_status(self, step_id, status):
        """Updates the status of an existing step."""
        for step in self.steps:
            if step["id"] == step_id:
                step["status"] = status
                self.save_memory()
                return True
        return False

    def get_all_steps(self):
        """Returns all steps recorded so far."""
        return self.steps

    def clear_memory(self):
        """Clears all steps from memory."""
        self.steps = []
        self.save_memory()

    def save_memory(self):
        """Saves memory to a JSON file."""
        with open(self.storage_file, "w") as f:
            json.dump(self.steps, f, indent=4)

    def load_memory(self):
        """Loads memory from a JSON file if it exists."""
        if os.path.exists(self.storage_file):
            try:
                with open(self.storage_file, "r") as f:
                    self.steps = json.load(f)
            except json.JSONDecodeError:
                self.steps = []
