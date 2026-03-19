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


# ─── Terminal Styling ─────────────────────────────────────────────────────────

class Colors:
    HEADER  = '\033[95m'
    BLUE    = '\033[94m'
    CYAN    = '\033[96m'
    GREEN   = '\033[92m'
    YELLOW  = '\033[93m'
    RED     = '\033[91m'
    BOLD    = '\033[1m'
    UNDERLINE = '\033[4m'
    RESET   = '\033[0m'


class Spinner:
    """A clean terminal spinner for long-running operations."""

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
        sys.stdout.write("\r" + " " * (len(self.message) + 4) + "\r")
        sys.stdout.flush()

    def __enter__(self):
        self._thread.start()
        return self

    def __exit__(self, *_):
        self._stop.set()
        self._thread.join()


# ─── Prompts ──────────────────────────────────────────────────────────────────

MANAGER_PROMPT = """
You are the Main Agent Manager. Your workflow is:
1. Identify if a specialized Agent/skill is needed.
2. Use 'list_available_skills' to discover agents and 'get_skill' to load one.
3. When a specialist agent finishes, it calls 'reset_to_manager' with a summary and optional 'next_steps'.
4. CRITICAL: Always check the latest activity in your memory. If 'next_steps' are mentioned, you MUST act on them.
5. If all steps are complete, present the final result to the user.
"""

REPORTING_INSTRUCTION = """

IMPORTANT: When you finish your job, you MUST call 'reset_to_manager'.
Provide a clear 'work_summary' and list any 'next_steps' if more work is needed.
"""

# ─── Tool Declarations ────────────────────────────────────────────────────────

MANAGER_TOOLS = [
    {
        "name": "list_available_skills",
        "description": "List all specialized skills/agents available.",
        "parameters": {"type": "object", "properties": {}},
    },
    {
        "name": "get_skill",
        "description": "Load a specialized skill/agent from the skills folder.",
        "parameters": {
            "type": "object",
            "properties": {"skill_name": {"type": "string"}},
            "required": ["skill_name"],
        },
    },
    {
        "name": "reset_to_manager",
        "description": "Return control to the main manager. Summarize your work and list next steps.",
        "parameters": {
            "type": "object",
            "properties": {
                "work_summary": {"type": "string", "description": "Short description of what was done."},
                "next_steps":   {"type": "string", "description": "What the manager should do next, if anything."},
            },
            "required": ["work_summary"],
        },
    },
]


# ─── Agent ────────────────────────────────────────────────────────────────────

class Agent:
    """Main Agent with specialist skill delegation and memory-aware handover."""

    MODEL_ID    = "gemini-2.5-flash"
    SKILLS_DIR  = "skills"
    TOOLS_DIR   = "tools"

    def __init__(self, system_prompt: str = MANAGER_PROMPT):
        self.system_prompt      = system_prompt
        self._manager_prompt    = MANAGER_PROMPT
        self.current_tools      = []
        self.memory             = Memory()
        self.chat               = None

        api_key     = os.getenv("VITE_VERTEX_API_KEY")
        self.client = genai.Client(vertexai=True, api_key=api_key)

        print(f"{Colors.GREEN}[System] Initialized with Vertex AI ({self.MODEL_ID}).{Colors.RESET}")

    # ── Properties ────────────────────────────────────────────────────────────

    @property
    def _is_manager(self) -> bool:
        return self.system_prompt == self._manager_prompt

    @property
    def _role_label(self) -> str:
        return "MANAGER" if self._is_manager else "SPECIALIST"

    @property
    def _role_color(self) -> str:
        return Colors.CYAN if self._is_manager else Colors.HEADER

    # ── Built-in Tool Handlers ────────────────────────────────────────────────

    def list_available_skills(self) -> str:
        """Return a comma-separated list of skill names found in the skills folder."""
        if not os.path.exists(self.SKILLS_DIR):
            return "Skills directory not found."
        skills = [f.removesuffix(".md") for f in os.listdir(self.SKILLS_DIR) if f.endswith(".md")]
        return f"Available skills: {', '.join(skills)}" if skills else "No skills found."

    def get_skill(self, skill_name: str) -> str:
        """Load a specialist skill, overriding the current system prompt and tools."""
        step_id    = self.memory.add_step(f"Loading skill: {skill_name}", status="in_progress")
        skill_file = os.path.join(self.SKILLS_DIR, f"{skill_name}.md")

        if not os.path.exists(skill_file):
            self.memory.update_step_status(step_id, "error")
            return f"Skill '{skill_name}' not found."

        try:
            content = open(skill_file).read().strip()

            if "---TOOLS---" in content:
                prompt_part, tools_part = content.split("---TOOLS---", 1)
                self.system_prompt  = prompt_part.strip() + REPORTING_INSTRUCTION
                self.current_tools  = json.loads(tools_part.strip())
            else:
                self.system_prompt  = content + REPORTING_INSTRUCTION
                self.current_tools  = []

            self.chat = None  # Fresh session for the specialist
            self.memory.update_step_status(step_id, "success")
            return f"Skill '{skill_name}' loaded."

        except Exception as exc:
            self.memory.update_step_status(step_id, "error")
            return f"Error loading skill: {exc}"

    def reset_to_manager(self, work_summary: str, next_steps: str = "None") -> str:
        """Hand control back to the manager and record what the specialist accomplished."""
        self.system_prompt = self._manager_prompt
        self.current_tools = []
        self.chat          = None

        description = f"Specialist done. Summary: {work_summary} | Next steps: {next_steps}"
        self.memory.add_step(description, status="done")

        self._notify(f"Specialist handover complete. Manager resuming.")
        return f"Manager restored. Outcome: {work_summary}"

    def _notify(self, message: str):
        """Hook for notifying the frontend of completed steps."""
        print(f"{Colors.BOLD}{Colors.YELLOW}>> NOTIFICATION:{Colors.RESET} {message}")

    # ── Script Tool Runner ────────────────────────────────────────────────────

    def execute_tool_script(self, tool_name: str, params: dict) -> dict:
        """Run a Python script from the tools/ folder and return its JSON output."""
        step_id     = self.memory.add_step(f"Running tool: {tool_name}", status="running")
        script_path = os.path.join(self.TOOLS_DIR, f"{tool_name}.py")

        if not os.path.exists(script_path):
            self.memory.update_step_status(step_id, "failed")
            return {"error": f"Tool script '{tool_name}.py' not found."}

        with Spinner(f"Running '{tool_name}'..."):
            try:
                result = subprocess.run(
                    [sys.executable, script_path, json.dumps(params)],
                    capture_output=True,
                    text=True,
                    check=True,
                )
                output = json.loads(result.stdout)
                self.memory.update_step_status(step_id, "success")
                return output
            except Exception as exc:
                self.memory.update_step_status(step_id, "error")
                return {"error": str(exc)}

    # ── Core Run Loop ─────────────────────────────────────────────────────────

    def _build_tools(self) -> list:
        all_declarations = MANAGER_TOOLS + self.current_tools
        return [
            types.Tool(function_declarations=[types.FunctionDeclaration(**t)])
            for t in all_declarations
        ]

    def _ensure_chat(self):
        if not self.chat:
            self.chat = self.client.chats.create(
                model=self.MODEL_ID,
                config=types.GenerateContentConfig(
                    system_instruction=self.system_prompt,
                    tools=self._build_tools(),
                ),
            )

    def run(self, user_message: str) -> str:
        """Process a user message, delegating to specialists as needed."""
        print(f"\n{self._role_color}[{self._role_label}] Active.{Colors.RESET}")

        self._ensure_chat()

        with Spinner(f"{self._role_label} processing..."):
            response = self.chat.send_message(user_message)

        # Tool-call dispatch loop
        while (
            response.candidates[0].content.parts
            and response.candidates[0].content.parts[0].function_call
        ):
            for part in response.candidates[0].content.parts:
                if not part.function_call:
                    continue

                name = part.function_call.name
                args = dict(part.function_call.args)
                print(f"{Colors.BLUE}[Action]{Colors.RESET} {name}({args})")

                if name == "list_available_skills":
                    result   = self.list_available_skills()
                    response = self.chat.send_message(
                        [types.Part.from_function_response(name=name, response={"available_skills": result})]
                    )

                elif name == "get_skill":
                    self.get_skill(args["skill_name"])
                    print(f"{Colors.GREEN}[System]{Colors.RESET} Handing off to specialist: {args['skill_name']}")
                    return self.run(f"User request: '{user_message}'. Please solve it and report back.")

                elif name == "reset_to_manager":
                    result = self.reset_to_manager(
                        args.get("work_summary", ""),
                        args.get("next_steps", "None"),
                    )
                    return self.run(f"System: Specialist finished. {result}. Check memory for next steps.")

                else:
                    res      = self.execute_tool_script(name, args)
                    with Spinner("Continuing..."):
                        response = self.chat.send_message(
                            [types.Part.from_function_response(name=name, response=res)]
                        )

                break  # Re-evaluate outer while condition after each dispatch

        return response.text or "[End of interaction]"

    # ── Diagnostics ───────────────────────────────────────────────────────────

    def show_history(self):
        """Print the full step history from memory."""
        steps = self.memory.get_all_steps()
        divider = "─" * 40
        print(f"\n{Colors.BOLD}{Colors.UNDERLINE}{divider}{Colors.RESET}")
        print(f"{Colors.BOLD}  Agent Activity History{Colors.RESET}")
        print(f"{Colors.BOLD}{Colors.UNDERLINE}{divider}{Colors.RESET}")
        for step in steps:
            ok     = step['status'] in ('success', 'done')
            color  = Colors.GREEN if ok else Colors.RED
            status = f"{color}{step['status']}{Colors.RESET}"
            print(f"  [{step['id']}] {step['description']}  →  {status}")
        print(f"{Colors.BOLD}{divider}{Colors.RESET}\n")


# ─── Entry Point ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    agent = Agent()

    query  = "how are you doing? if your great then what's 10 + 1 - 100"
    print(f"\n{Colors.BOLD}User:{Colors.RESET} {query}")

    answer = agent.run(query)
    print(f"\n{Colors.GREEN}{Colors.BOLD}Answer:{Colors.RESET} {answer}\n")

    agent.show_history()