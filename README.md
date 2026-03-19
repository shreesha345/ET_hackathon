# ET Agent - Multi-Agent Coordination Framework 🚀

A simple, powerful, and highly extensible framework for building AI agent systems. This project implements a **Manager-Specialist** coordination pattern, allowing a central manager to discover, load, and delegate tasks to specialized agents with their own set of tools.

---

## 🌟 Key Features

- **Manager-Specialist Architecture**: A central Manager handles high-level intent and delegates execution to specialized sub-agents (Skills).
- **Markdown-Based Skill System**: Define agent personas, system prompts, and tool schemas directly in `.md` files in the `skills/` directory.
- **Standalone Script Tools**: Tools are independent Python scripts located in the `tools/` folder, executed dynamically by the agent via `subprocess`.
- **Advanced Scratchpad (Memory)**: A persistent `memory.json` system that tracks every step, status, and handover summary between agents.
- **Robust Handover Logic**: Specialists report their work using `reset_to_manager`, providing a summary and suggested `next_steps` for the Manager to follow.
- **Premium Terminal UX**: Features ANSI-colorized logs and a real-time loading spinner for a smooth developer experience.
- **Google GenAI & Vertex AI**: Fully integrated with the `google-genai` SDK, supporting both Vertex AI and standard Gemini API keys.

---

## 🛠️ How it Works

### 1. 🔍 Discovery
The Manager uses the `list_available_skills` tool to see which specialized agents are available in the `skills/` folder.

### 2. 📦 Loading
When a task is identified, the Manager calls `get_skill(skill_name)`. This swaps the system prompt and registers the new tools defined in that skill's `.md` file.

### 3. ✨ Execution
The specialized agent uses its tools (e.g., `add.py`, `subtract.py`) to perform the work. These are executed as external Python scripts to keep the logic modular.

### 4. 📝 Reporting
Once finished, the Specialist calls `reset_to_manager(work_summary, next_steps)`. The Manager then reads the scratchpad to decide whether to continue with further steps or conclude the task.

---

## 📁 Project Structure

- `Agent.py`: The core agent implementation (Manager + Specialist logic).
- `memory.py`: Logic for the persistent scratchpad system.
- `skills/`: Markdown files defining specialized agents (e.g., `math_agent.md`).
- `tools/`: Python scripts that function as agent tools (e.g., `add.py`).
- `memory.json`: (Auto-generated) Persistent record of steps and handovers.

---

## 🚀 Getting Started

### 🏗️ Prerequisites
- Python 3.12+
- `google-genai` SDK
- A valid **Vertex AI** project or **Gemini API Key**.

### ⚙️ Configuration
Create a `.env` file with your credentials:
```env
VITE_VERTEX_API_KEY="your_api_key_or_token"
VITE_GOOGLE_CLOUD_PROJECT="your_project_id"
VITE_GOOGLE_CLOUD_LOCATION="us-central1"
```

### ▶️ Running the Agent
```bash
uv run Agent.py
```

---

## 🎯 Example Flow
**User**: *"Add 123 and 456"*
1. **Manager**: Detects math task → loads `math_agent`.
2. **Specialist (`math_agent`)**: Calls `add.py` tool.
3. **Tool (`add.py`)**: Returns `579.0`.
4. **Specialist**: Reports result to Manager → calls `reset_to_manager`.
5. **Manager**: Sees task complete → Informs user.
