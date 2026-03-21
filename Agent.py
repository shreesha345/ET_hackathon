"""
Agent.py — The Main Agent (Manager)
====================================
This is the brain of the system. It works like this:

    ┌─────────────────────────────────────────────┐
    │              MANAGER MODE                   │
    │  (Default — uses the MANAGER_PROMPT)        │
    │                                             │
    │  Has ONE universal tool:                    │
    │    • find_and_use_skill  → searches the     │
    │      skills/ folder, picks the right skill, │
    │      and loads it.                          │
    │                                             │
    │  When a skill is loaded:                    │
    │    1. System prompt switches to the skill's │
    │       prompt.                               │
    │    2. The skill's tools become available.   │
    │    3. The agent now acts as that specialist.│
    └──────────────────────┬──────────────────────┘
                           │  Skill finishes its job
                           ▼
    ┌─────────────────────────────────────────────┐
    │              KILL SWITCH                    │
    │  reset_to_manager() is called               │
    │    1. System prompt resets to MANAGER_PROMPT│
    │    2. Specialist tools are removed.         │
    │    3. Manager resumes control.              │
    └─────────────────────────────────────────────┘

Folder Structure:
    Agent.py        ← You are here (main agent)
    memory.py       ← Scratchpad (tracks steps & status)
    prompt.md       ← The manager's system prompt (edit this!)
    skills/         ← Each .md file is a skill/agent
    tools/          ← Python scripts that skills can call
"""

import os
import json
import subprocess
import sys
import time
import threading
from dotenv import load_dotenv
from memory import Memory
from google import genai
from google.genai import types

load_dotenv()


# ═══════════════════════════════════════════════════════════════════════════════
# TERMINAL STYLING (just colors for pretty output)
# ═══════════════════════════════════════════════════════════════════════════════

class Colors:
    """ANSI color codes for terminal output."""
    HEADER    = '\033[95m'   # Purple
    BLUE      = '\033[94m'
    CYAN      = '\033[96m'
    GREEN     = '\033[92m'
    YELLOW    = '\033[93m'
    RED       = '\033[91m'
    BOLD      = '\033[1m'
    UNDERLINE = '\033[4m'
    RESET     = '\033[0m'


class Spinner:
    """
    Shows a spinning animation in the terminal while the agent is thinking.
    Usage:
        with Spinner("Thinking..."):
            do_something_slow()
    """
    FRAMES = '⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏'

    def __init__(self, message: str = "Thinking..."):
        self.message = message
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._spin, daemon=True)

    def _spin(self):
        for i in range(10**9):
            if self._stop.is_set():
                break
            frame = self.FRAMES[i % len(self.FRAMES)]
            sys.stdout.write(f"\r{Colors.CYAN}{frame}{Colors.RESET} {self.message}")
            sys.stdout.flush()
            time.sleep(0.1)
        # Clear the spinner line when done
        sys.stdout.write("\r" + " " * (len(self.message) + 4) + "\r")
        sys.stdout.flush()

    def __enter__(self):
        self._thread.start()
        return self

    def __exit__(self, *_):
        self._stop.set()
        self._thread.join()


# ═══════════════════════════════════════════════════════════════════════════════
# SYSTEM PROMPTS
# ═══════════════════════════════════════════════════════════════════════════════

def _load_manager_prompt() -> str:
    """
    Load the manager's system prompt from prompt.md.
    If the file is empty or missing, use a sensible default.
    """
    prompt_file = os.path.join(os.path.dirname(__file__), "prompt.md")
    if os.path.exists(prompt_file):
        content = open(prompt_file, encoding="utf-8").read().strip()
        if content:
            return content

    # Fallback default prompt (used only if prompt.md is empty/missing)
    return """You are the Main Agent Manager.

Your job:
1. Understand the user's request.
2. Use 'find_and_use_skill' to search for and load the right specialist skill.
3. When a specialist finishes, it calls 'reset_to_manager' with a summary.
4. Check your memory for any pending next_steps and act on them.
5. When everything is done, present the final result to the user."""


# This instruction is appended to EVERY specialist's prompt so they know to hand back.
REPORTING_INSTRUCTION = """

IMPORTANT: When you finish your job, you MUST call 'reset_to_manager'.
Provide a clear 'work_summary' and list any 'next_steps' if more work is needed."""


# ═══════════════════════════════════════════════════════════════════════════════
# TOOL DECLARATIONS (what the LLM sees as available functions)
# ═══════════════════════════════════════════════════════════════════════════════

# --- Manager Tools ---
# These are ALWAYS available. The manager uses them to find & load skills.

MANAGER_TOOLS = [
    {
        # See what skills are available.
        "name": "list_skills",
        "description": "List all available specialist skills/agents with their descriptions.",
        "parameters": {"type": "object", "properties": {}},
    },
    {
        # Load a skill — switches the agent INTO specialist mode.
        "name": "find_and_use_skill",
        "description": (
            "Load a specialist skill/agent by name. This switches you into that "
            "specialist's mode (new prompt + tools). Use list_skills first to see what's available."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "skill_name": {
                    "type": "string",
                    "description": "Name of the skill to load (without .md extension).",
                },
            },
            "required": ["skill_name"],
        },
    },
    {
        # Run a skill in isolation — Manager stays in control.
        # Use this when you need to run MULTIPLE skills for one task.
        "name": "run_skill",
        "description": (
            "Run a specialist skill in the background and get its result back. "
            "Unlike find_and_use_skill, this does NOT switch modes — you stay as Manager. "
            "Use this to chain multiple skills for complex tasks."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "skill_name": {
                    "type": "string",
                    "description": "Name of the skill to run (without .md extension).",
                },
                "query": {
                    "type": "string",
                    "description": "The task/question to send to the skill.",
                },
            },
            "required": ["skill_name", "query"],
        },
    },
    {
        # Kill switch — specialist calls this when done.
        "name": "reset_to_manager",
        "description": (
            "Return control to the main manager. Call this when your job is done."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "work_summary": {
                    "type": "string",
                    "description": "Short description of what was accomplished.",
                },
                "next_steps": {
                    "type": "string",
                    "description": "What the manager should do next, if anything.",
                },
            },
            "required": ["work_summary"],
        },
    },
]


# ═══════════════════════════════════════════════════════════════════════════════
# THE AGENT
# ═══════════════════════════════════════════════════════════════════════════════

class Agent:
    """
    The main agent. It starts in "Manager" mode and can switch to
    "Specialist" mode by loading a skill from the skills/ folder.

    Key idea:
        - Manager mode  → has find_and_use_skill + run_skill tools
        - find_and_use_skill → switches INTO the skill (full handover)
        - run_skill          → runs a skill in isolation (Manager stays in control)
        - Specialist mode → has whatever tools the skill defines
        - When specialist is done → kill switch resets back to Manager
    """

    MODEL_ID   = "gemini-3-flash-preview"    # The LLM model to use
    SKILLS_DIR = "skills"               # Where skill .md files live
    TOOLS_DIR  = "tools"                # Where tool .py scripts live

    def __init__(self):
        # Load the manager prompt (from prompt.md or default)
        self._manager_prompt = _load_manager_prompt()

        # Current state
        self.system_prompt  = self._manager_prompt   # Active system prompt
        self.current_tools  = []                      # Extra tools from loaded skill
        self.chat           = None                    # Chat session (reset on skill switch)
        self.memory         = Memory()                # The scratchpad

        # Initialize the Google GenAI client
        self.client = genai.Client(
            api_key=os.getenv("VITE_VERTEX_API_KEY"),
        )
        self._log("System", f"Agent initialized with {self.MODEL_ID}.", Colors.GREEN)

    # ── Helper Properties ─────────────────────────────────────────────────────

    @property
    def is_manager(self) -> bool:
        """True if the agent is currently in Manager mode."""
        return self.system_prompt == self._manager_prompt

    @property
    def _role_label(self) -> str:
        """Display label for the current mode."""
        return "MANAGER" if self.is_manager else "SPECIALIST"

    @property
    def _role_color(self) -> str:
        """Color for the current mode."""
        return Colors.CYAN if self.is_manager else Colors.HEADER

    # ── Logging ───────────────────────────────────────────────────────────────

    def _log(self, tag: str, message: str, color: str = Colors.BLUE):
        """Print a formatted log message."""
        print(f"{color}[{tag}]{Colors.RESET} {message}")

    # ═══════════════════════════════════════════════════════════════════════════
    # TOOL HANDLERS (what actually happens when the LLM calls a tool)
    # ═══════════════════════════════════════════════════════════════════════════

    def find_and_use_skill(self, skill_name: str = "") -> str:
        """
        The ONE universal tool.

        - If skill_name is empty → list all available skills with their descriptions.
        - If skill_name is given → load that skill (switch system prompt + tools).

        This is the only tool the manager needs. It can discover what's available
        and then load the right specialist.
        """

        # ── Case 1: No skill_name → just list available skills ────────────────
        if not skill_name:
            return self._list_skills()

        # ── Case 2: skill_name given → load the skill ─────────────────────────
        return self._load_skill(skill_name)

    def _list_skills(self) -> str:
        """
        Scan the skills/ folder and return a summary of all available skills.
        Each skill's first line (after the # heading) is used as its description.
        """
        if not os.path.exists(self.SKILLS_DIR):
            return "No skills directory found."

        # Find all .md files in the skills folder
        skill_files = [f for f in os.listdir(self.SKILLS_DIR) if f.endswith(".md")]

        if not skill_files:
            return "No skills found in the skills/ folder."

        # Build a summary with name + first-line description
        summaries = []
        for filename in skill_files:
            name = filename.removesuffix(".md")
            path = os.path.join(self.SKILLS_DIR, filename)

            # Read the first non-empty, non-heading line as the description
            description = "(no description)"
            with open(path, encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#"):
                        description = line[:100]  # Truncate long descriptions
                        break

            summaries.append(f"  • {name}: {description}")

        return "Available skills:\n" + "\n".join(summaries)

    def _load_skill(self, skill_name: str) -> str:
        """
        Load a skill from skills/<skill_name>.md.

        The .md file format:
            # Skill Title
            You are a specialist...  (this becomes the system prompt)

            ---TOOLS---              (optional separator)
            [ ...JSON array... ]     (tool declarations for this skill)
        """
        step_id = self.memory.add_step(f"Loading skill: {skill_name}", status="in_progress")
        skill_file = os.path.join(self.SKILLS_DIR, f"{skill_name}.md")

        # Check the skill file exists
        if not os.path.exists(skill_file):
            self.memory.update_step(step_id, "error")
            return f"Skill '{skill_name}' not found in skills/ folder."

        try:
            content = open(skill_file, encoding="utf-8").read().strip()

            # Split into prompt and tools (if ---TOOLS--- separator exists)
            if "---TOOLS---" in content:
                prompt_part, tools_part = content.split("---TOOLS---", 1)
                self.system_prompt = prompt_part.strip() + REPORTING_INSTRUCTION
                self.current_tools = json.loads(tools_part.strip())
            else:
                # No tools — just a prompt-only skill
                self.system_prompt = content + REPORTING_INSTRUCTION
                self.current_tools = []

            # Reset the chat session so the new prompt takes effect
            self.chat = None

            self.memory.update_step(step_id, "success")
            self._log("System", f"Skill '{skill_name}' loaded. Switching to SPECIALIST mode.", Colors.GREEN)
            return f"Skill '{skill_name}' loaded successfully."

        except Exception as e:
            self.memory.update_step(step_id, "error")
            return f"Error loading skill '{skill_name}': {e}"

    def reset_to_manager(self, work_summary: str, next_steps: str = "") -> str:
        """
        ╔═══════════════════════════════════════════╗
        ║            THE KILL SWITCH                ║
        ║  Resets everything back to Manager mode.  ║
        ╚═══════════════════════════════════════════╝

        Called by the specialist when it's done with its job.
        - Restores the manager's system prompt.
        - Clears specialist tools.
        - Logs what was accomplished in memory.
        """
        # Reset to manager state
        self.system_prompt = self._manager_prompt
        self.current_tools = []
        self.chat = None  # Fresh chat session for the manager

        # Log the handover in memory
        summary_text = f"Specialist done → {work_summary}"
        if next_steps:
            summary_text += f" | Next: {next_steps}"
        self.memory.add_step(summary_text, status="done")

        self._log("Kill Switch", "Specialist finished. Manager resumed.", Colors.YELLOW)
        return f"Manager restored. Work done: {work_summary}"

    # ═══════════════════════════════════════════════════════════════════════════
    # TOOL SCRIPT RUNNER (runs Python scripts from tools/ folder)
    # ═══════════════════════════════════════════════════════════════════════════

    def _run_tool_script(self, tool_name: str, params: dict) -> dict:
        """
        Execute a Python script from the tools/ folder.

        The script is expected to:
          - Accept a JSON string as its first argument (sys.argv[1])
          - Print a JSON result to stdout

        Example: tools/add.py '{"a": 1, "b": 2}' → {"result": 3}
        """
        step_id = self.memory.add_step(f"Running tool: {tool_name}", status="in_progress")
        script_path = os.path.join(self.TOOLS_DIR, f"{tool_name}.py")

        if not os.path.exists(script_path):
            self.memory.update_step(step_id, "error")
            return {"error": f"Tool script '{tool_name}.py' not found in tools/ folder."}

        with Spinner(f"Running '{tool_name}'..."):
            try:
                result = subprocess.run(
                    [sys.executable, script_path, json.dumps(params)],
                    capture_output=True,
                    text=True,
                    check=True,
                )
                output = json.loads(result.stdout)
                self.memory.update_step(step_id, "success")
                return output
            except Exception as e:
                self.memory.update_step(step_id, "error")
                return {"error": str(e)}

    # ═══════════════════════════════════════════════════════════════════════════
    # CORE RUN LOOP — where the magic happens
    # ═══════════════════════════════════════════════════════════════════════════

    def _build_tool_declarations(self) -> list:
        """
        Build the complete list of tools available to the LLM.
        Always includes MANAGER_TOOLS + any tools from the loaded skill.
        """
        all_tools = MANAGER_TOOLS + self.current_tools
        return [
            types.Tool(function_declarations=[types.FunctionDeclaration(**t)])
            for t in all_tools
        ]

    def _ensure_chat(self):
        """Create a chat session if one doesn't exist (or was reset)."""
        if not self.chat:
            # Inject memory context into the system prompt so the LLM knows what happened
            memory_context = self.memory.get_summary()
            full_prompt = self.system_prompt
            if memory_context != "No activity recorded yet.":
                full_prompt += f"\n\n--- MEMORY (what you've done so far) ---\n{memory_context}"

            self.chat = self.client.chats.create(
                model=self.MODEL_ID,
                config=types.GenerateContentConfig(
                    system_instruction=full_prompt,
                    tools=self._build_tool_declarations(),
                ),
            )

    def run(self, user_message: str) -> str:
        """
        Process a user message. This is the main entry point.

        Flow:
            1. Send message to the LLM.
            2. If the LLM wants to call a tool → execute it and send the result back.
            3. Repeat step 2 until the LLM gives a text response.
            4. Return the text response.

        Special cases:
            - find_and_use_skill → may switch to specialist mode.
            - reset_to_manager  → switches back to manager mode (kill switch).
        """
        self._log(self._role_label, "Processing...", self._role_color)
        self._ensure_chat()

        # Send the message to the LLM
        with Spinner(f"{self._role_label} thinking..."):
            response = self.chat.send_message(user_message)

        # ── Tool Call Loop ────────────────────────────────────────────────────
        while response.candidates[0].content.parts and any(p.function_call for p in response.candidates[0].content.parts):
            function_responses = []
            immediate_return = None

            for part in response.candidates[0].content.parts:
                if not part.function_call:
                    continue

                fn_name = part.function_call.name
                fn_args = dict(part.function_call.args)
                self._log("Tool Call", f"{fn_name}({fn_args})")

                # ── Handle: list_skills ────────────────────────────────────────
                if fn_name == "list_skills":
                    result = self._list_skills()
                    function_responses.append(
                        types.Part.from_function_response(name=fn_name, response={"skills": result})
                    )

                # ── Handle: find_and_use_skill (load & switch to specialist) ──
                elif fn_name == "find_and_use_skill":
                    skill_name = fn_args.get("skill_name", "")
                    self.find_and_use_skill(skill_name)
                    # This switches modes — we must restart the 'run' with the original query
                    immediate_return = self.run(
                        f"User's original request: '{user_message}'. "
                        f"Please complete this and call reset_to_manager when done."
                    )
                    break

                # ── Handle: run_skill (run a skill without switching modes) ──
                elif fn_name == "run_skill":
                    skill_result = self._run_tool_script("run_skill", fn_args)
                    self._log("Skill Result", f"{fn_args.get('skill_name', '?')} → done", Colors.GREEN)
                    function_responses.append(
                        types.Part.from_function_response(name=fn_name, response=skill_result)
                    )

                # ── Handle: reset_to_manager (KILL SWITCH) ────────────────────
                elif fn_name == "reset_to_manager":
                    result = self.reset_to_manager(
                        fn_args.get("work_summary", ""),
                        fn_args.get("next_steps", ""),
                    )
                    # This switches back to manager — restart with context
                    immediate_return = self.run(
                        f"Specialist finished. {result}. "
                        f"Check memory for any next steps."
                    )
                    break

                # ── Handle: Any other tool (from a loaded skill) ──────────────
                else:
                    tool_result = self._run_tool_script(fn_name, fn_args)
                    function_responses.append(
                        types.Part.from_function_response(name=fn_name, response=tool_result)
                    )

            if immediate_return:
                return immediate_return

            if function_responses:
                with Spinner("Processing results..."):
                    response = self.chat.send_message(function_responses)
            else:
                break

        # ── Done — return the LLM's text response ────────────────────────────
        return response.text or "[No response]"

    # ═══════════════════════════════════════════════════════════════════════════
    # DIAGNOSTICS — show what the agent has been doing
    # ═══════════════════════════════════════════════════════════════════════════

    def show_history(self):
        """Print the full activity log from memory."""
        divider = "─" * 50
        print(f"\n{Colors.BOLD}{divider}{Colors.RESET}")
        print(f"{Colors.BOLD}  📋 Agent Activity Log{Colors.RESET}")
        print(f"{Colors.BOLD}{divider}{Colors.RESET}")
        print(self.memory.get_summary())
        print(f"{Colors.BOLD}{divider}{Colors.RESET}\n")


# ═══════════════════════════════════════════════════════════════════════════════
# ENTRY POINT — run this file directly to test
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    agent = Agent()

    print(f"\n{Colors.BOLD}{'═' * 50}{Colors.RESET}")
    print(f"{Colors.BOLD}  🤖 Agent System — Interactive Mode{Colors.RESET}")
    print(f"{Colors.BOLD}{'═' * 50}{Colors.RESET}")
    print(f"{Colors.CYAN}Type 'quit' to exit, 'history' to see activity log.{Colors.RESET}\n")

    while True:
        try:
            query = input(f"{Colors.BOLD}You: {Colors.RESET}").strip()

            if not query:
                continue
            if query.lower() in ("quit", "exit", "q"):
                print(f"\n{Colors.GREEN}Goodbye! 👋{Colors.RESET}\n")
                break
            if query.lower() == "history":
                agent.show_history()
                continue
            if query.lower() == "clear":
                agent.memory.clear()
                print(f"{Colors.GREEN}Memory cleared.{Colors.RESET}")
                continue

            answer = agent.run(query)
            print(f"\n{Colors.GREEN}{Colors.BOLD}Agent:{Colors.RESET} {answer}\n")

        except KeyboardInterrupt:
            print(f"\n\n{Colors.GREEN}Goodbye! 👋{Colors.RESET}\n")
            break