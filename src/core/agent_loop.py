import sys
import os
import json
import asyncio
import logging
from typing import Optional, List, Any

from src.core.agent import Agent
from src.core.storage import JsonStorage
from src.core.logger import logger, setup_logging
from src.core.agent_loader import create_agent_instance
from src.tools.web_search import WebSearchTool
from src.tools.python_eval import PythonEvalTool
from src.tools.personality_tool import UpdatePersonalityTool
# Tools that need adapting or stubbing for stdin/stdout:
# (For example, creator tools and scheduler depend on chat_room)

class StdoutChatBridge:
    """A mock chat room that just prints to stdout."""
    async def post_message(self, sender: str, message: str, room: str = None):
        # We output a structured JSON or just plain text.
        # Since the IRC bridge reads this, just text is fine, but maybe prefix with sender.
        # However, the IRC bridge knows this process belongs to one agent.
        print(message, flush=True)
        
    def register_agent(self, agent):
        pass
        
    def unregister_agent(self, name: str):
        pass

    async def agent_join(self, name: str):
        await self.post_message("System", f"* {name} has joined the chat")

    async def agent_leave(self, name: str):
        await self.post_message("System", f"* {name} has left the chat")
        
    async def notify_task_complete(self, agent_name: str, task_summary: str):
        await self.post_message(agent_name, f"[TASK COMPLETE] {task_summary}")
        
    def get_recent_history(self, limit: int = 30) -> List[Any]:
        # History is now maintained by the IRC bridge or just kept in memory here.
        # Let's keep a local history in this loop for context.
        return self.history[-limit:] if hasattr(self, 'history') else []

async def main():
    agent_name = os.environ.get("AGENT_NAME")
    if not agent_name:
        sys.stderr.write("ERROR: AGENT_NAME environment variable not set.\n")
        sys.exit(1)

    # Load metadata FIRST so we have the properly cased name for logs and instantiations
    agent_path = "/app/data/agent"
    meta_path = os.path.join(agent_path, "metadata.json")
    
    keywords = []
    role = "Agent"
    if os.path.exists(meta_path):
        with open(meta_path, "r", encoding="utf-8") as f:
            meta = json.load(f)
            # Override with properly cased name
            agent_name = meta.get("name", agent_name)
            keywords = meta.get("claim_keywords", [])
            role = meta.get("role", "Agent")

    # Setup file and stderr logging
    # Every agent container mounts its specific data/agents/<AgentName> dir to /app/data/agent
    log_dir = "/app/data/agent"
    os.makedirs(log_dir, exist_ok=True)
    log_file = os.path.join(log_dir, "agent.log")
    
    # Re-configure logger to write to stderr and file, NOT stdout
    handler = logging.StreamHandler(sys.stderr)
    file_handler = logging.FileHandler(log_file)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    file_handler.setFormatter(formatter)
    
    logger.handlers.clear()
    logger.addHandler(handler)
    logger.addHandler(file_handler)
    logger.setLevel(logging.INFO)
    
    logger.info(f"Starting agent loop for {agent_name}")

    chat_bridge = StdoutChatBridge()
    chat_bridge.history = []

    # Initialize Agent
    agent = create_agent_instance(agent_name, role, agent_path, keywords, chat_bridge)
    # The creator agent might need CreatorTools which takes a chat_room.
    # Our stdout chat bridge is a bit of a stub, but sufficient for outputting text.
    agent.chat_room = chat_bridge
    
    # We must also redefine the tools that need real container implementations:
    # 1. File system (read/write in container)
    # 2. Container command execution (we can run shell commands)
    # 3. Git repo cloning
    # Let's add standard container system tools
    from src.tools.base import Tool
    import subprocess
    
    class RunCommandTool(Tool):
        def __init__(self):
            super().__init__(
                "run_command",
                "Run a shell command inside the agent's container.",
                args_schema={"command": "The shell command to run."}
            )
        async def run(self, command: str) -> str:
            logger.info(f"Running command: {command}")
            try:
                result = subprocess.run(command, shell=True, capture_output=True, text=True, timeout=120)
                stdout = result.stdout.strip()
                stderr = result.stderr.strip()
                output = f"Exit code: {result.returncode}\n"
                if stdout: output += f"STDOUT:\n{stdout}\n"
                if stderr: output += f"STDERR:\n{stderr}\n"
                return output[:4000] # Limit output
            except Exception as e:
                return f"Error running command: {e}"

    class FileSystemTool(Tool):
        def __init__(self):
            super().__init__(
                "file_system_read",
                "Read the contents of a file.",
                args_schema={"path": "Absolute or relative path to the file."}
            )
        async def run(self, path: str) -> str:
            try:
                with open(path, "r", encoding="utf-8") as f:
                    return f.read()[:8000]
            except Exception as e:
                return f"Error reading file {path}: {e}"

    class FileSystemWriteTool(Tool):
        def __init__(self):
            super().__init__(
                "file_system_write",
                "Write content to a file.",
                args_schema={"path": "Path to the file.", "content": "Content to write."}
            )
        async def run(self, path: str, content: str) -> str:
            try:
                os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
                with open(path, "w", encoding="utf-8") as f:
                    f.write(content)
                return f"Successfully wrote to {path}"
            except Exception as e:
                return f"Error writing to {path}: {e}"

    class CustomPythonEvalTool(Tool):
        def __init__(self):
            super().__init__(
                "python_eval",
                "Evaluate a python script locally for complex problems.",
                args_schema={"code": "Python code to execute."}
            )
        async def run(self, code: str) -> str:
            # We can write to a temp file and run it
            script_path = "/tmp/eval_script.py"
            with open(script_path, "w") as f:
                f.write(code)
            try:
                res = subprocess.run([sys.executable, script_path], capture_output=True, text=True, timeout=60)
                return f"STDOUT:\n{res.stdout}\nSTDERR:\n{res.stderr}"
            except Exception as e:
                return f"Execution error: {e}"

    agent.add_tool(RunCommandTool())
    agent.add_tool(FileSystemTool())
    agent.add_tool(FileSystemWriteTool())
    agent.add_tool(CustomPythonEvalTool())

    def get_brief_description(personality: str, fallback_role: str) -> str:
        if not personality:
            return fallback_role
        import re
        match = re.search(r"You are \*\*[^*]+\*\*,?\s*(.*?)(?:\.|\n|$)", personality)
        if match:
            return match.group(1).strip()
        lines = personality.split("\n")
        for line in lines:
            line = line.strip()
            if line and not line.startswith("#"):
                return line.split(". ")[0].strip(" .")
        return fallback_role

    description = get_brief_description(agent.personality, role)
    print(f"Hello, i'm {agent_name}, I'm here to help you with {description}", flush=True)

    # Simplified stub for history
    class DummyMessage:
        def __init__(self, sender, content):
            self.sender = sender
            self.content = content

    # The Loop
    loop = asyncio.get_event_loop()
    # Auto-trigger Creator to sync agents on startup
    if agent_name.lower() == "creator":
        logger.info("Creator booting up. Waiting 10 seconds for environment to stabilize...")
        await asyncio.sleep(10)
        logger.info("Triggering sync_agents on startup for Creator...")

        startup_msg = "System: You have just booted up. Please run the sync_agents tool to check if any agents defined in the data directory are not currently running, and spawn them immediately if necessary."
        msg_obj = DummyMessage("System", startup_msg)
        chat_bridge.history.append(msg_obj)
        # Process message in background without blocking loop
        asyncio.create_task(agent.process_message(startup_msg))
        sys.stdout.write("--- WAIT_FOR_INPUT ---\n")
        sys.stdout.flush()

    while True:
        try:
            line = await loop.run_in_executor(None, sys.stdin.readline)
            if not line:
                # EOF
                break
                
            line = line.strip()
            if not line: continue
            
            logger.info(f"Received from stdin: {line}")
            
            # Check for passive history update
            is_history_only = False
            if line.startswith("[HISTORY] "):
                is_history_only = True
                line = line[len("[HISTORY] "):]

            # Format from IRC bridge is typically "Sender: Message"
            sender = "User"
            content = line
            if ":" in line:
                parts = line.split(":", 1)
                sender = parts[0].strip()
                content = parts[1].strip()
                
            msg = DummyMessage(sender, content)
            chat_bridge.history.append(msg)
            
            if is_history_only:
                logger.info(f"Stored passive history from {sender}")
                sys.stdout.write("--- WAIT_FOR_INPUT ---\n")
                sys.stdout.flush()
                continue
                
            # Process the active message
            await agent.process_message(content)
            
            # Signal ready for next input
            sys.stdout.write("--- WAIT_FOR_INPUT ---\n")
            sys.stdout.flush()
            
        except Exception as e:
            logger.error(f"Error in agent loop: {e}", exc_info=True)
            sys.stderr.write(f"Error: {e}\n")

    # Graceful exit
    if hasattr(agent, "scheduler_daemon"):
        logger.info(f"Shutting down scheduler for {agent_name}...")
        agent.scheduler_daemon.stop()

if __name__ == "__main__":
    asyncio.run(main())
