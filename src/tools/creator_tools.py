
import json
import os
import shutil
import time
from src.tools.base import Tool
from src.core.logger import logger


class CreateAgentTool(Tool):
    """Creates a new agent with a personality and registers it in the chat."""

    def __init__(self, chat_room):
        super().__init__(
            "create_agent",
            "Create a new agent. You must provide a name, role, personality, and claim_keywords.",
            args_schema={
                "name": "The name of the agent (e.g., 'PythonExpert', 'WriterBot'). No spaces.",
                "role": "The role or job title of the agent.",
                "personality": "A DETAILED personality document in markdown. Describe behavior, tone, expertise, and how the agent should interact.",
                "claim_keywords": "Comma-separated keywords this agent should respond to (e.g., 'python,coding,script,programming')"
            }
        )
        self.chat_room = chat_room

    async def run(self, name: str, role: str, personality: str, claim_keywords: str = "", **kwargs) -> str:
        try:
            # Fallbacks for common LLM attribute hallucinations
            if not claim_keywords and 'tags' in kwargs:
                claim_keywords = kwargs['tags']
            if not claim_keywords and 'keywords' in kwargs:
                claim_keywords = kwargs['keywords']
            # Validate
            if not name or not role:
                return "Error: name and role are required."

            # Parse keywords
            keywords = [kw.strip() for kw in claim_keywords.split(",") if kw.strip()] if claim_keywords else []

            # Ensure personality is not empty
            if not personality or len(personality.strip()) < 10:
                personality = self._generate_default_personality(name, role)

            # Create directory structure & files
            from src.core.agent_loader import create_agent_files
            create_agent_files(name, role, personality, claim_keywords=keywords)
            
            logger.info(f"CreateAgentTool: Agent '{name}' files created. Spawning container...")
            
            # Spawn Docker Container
            import subprocess
            
            # First, try to remove the container if it already exists
            subprocess.run(["docker", "rm", "-f", f"agent-{name.lower()}"], capture_output=True)
            
            cmd = [
                "docker", "run", "-d", "--restart", "unless-stopped",
                "--name", f"agent-{name.lower()}",
                "--network", "homeagent_default", # Assuming docker compose default network name
                "-e", f"AGENT_NAME={name}",
                "-e", f"IRC_SERVER={os.environ.get('IRC_SERVER', 'ircserver')}",
                "-e", "IRC_PORT=6667",
                "-e", f"OLLAMA_HOST={os.environ.get('OLLAMA_HOST', 'http://host.docker.internal:11434')}",
                "-v", "/var/run/docker.sock:/var/run/docker.sock",
                "-v", f"{os.path.join(os.environ.get('HOST_PROJECT_ROOT', os.getcwd()), 'data', 'agents', name)}:/app/data/agent",
                "-v", f"{os.path.join(os.environ.get('HOST_PROJECT_ROOT', os.getcwd()), 'data', 'agents')}:/app/data/agents:ro",
                "-v", f"{os.path.join(os.environ.get('HOST_PROJECT_ROOT', os.getcwd()), 'data', 'shared')}:/app/data/shared",
                "homeagent-agent-coordinator" # Re-use the built image
            ]
            try:
                res = subprocess.run(cmd, capture_output=True, text=True)
                if res.returncode == 0:
                    return f"Successfully created and started container for agent {name}."
                else:
                    # Try fallback image name
                    cmd[-1] = "homeagent-agent-creator"
                    res2 = subprocess.run(cmd, capture_output=True, text=True)
                    if res2.returncode == 0:
                        return f"Successfully created and started container for agent {name}."
                    return f"Failed to start container. Error: {res.stderr} or {res2.stderr}"
            except Exception as e:
                return f"Docker execution error: {e}"

        except Exception as e:
            logger.error(f"CreateAgentTool error: {e}", exc_info=True)
            return f"Error creating agent: {e}"

    def _generate_default_personality(self, name: str, role: str) -> str:
        return f"""# {name}

You are **{name}**, a highly skilled **{role}**.

## Expertise
You are an expert in your field. Provide detailed, accurate, and helpful information related to {role}.

## Behavior
- Be professional and concise
- If you see a problem, suggest a solution
- Collaborate with other agents via the chat
- Use your tools when needed (web search, knowledge bank, etc.)
- Update your personality document as you learn and improve

## Interaction Guidelines
1. When asked a question, provide a direct answer
2. If you don't know, admit it and suggest who might help
3. Use @AgentName to mention other agents when delegating
4. Signal task completion when you've finished your work
"""


class DeleteAgentTool(Tool):
    """Archives an agent and removes it from the chat."""

    def __init__(self, chat_room):
        super().__init__(
            "delete_agent",
            "Delete (archive) an agent. System agents (Coordinator, Creator, Judge) cannot be deleted.",
            args_schema={
                "name": "The name of the agent to delete."
            }
        )
        self.chat_room = chat_room

    async def run(self, name: str) -> str:
        if name in ["Coordinator", "Creator", "Judge"]:
            return f"Cannot delete system agent '{name}'."

        if name not in self.chat_room.agents:
            return f"Agent '{name}' not found."

        base_path = os.path.join("data", "agents", name)
        if not os.path.exists(base_path):
            return f"Agent '{name}' directory not found."

        # Disable in metadata.json
        meta_path = os.path.join(base_path, "metadata.json")
        if os.path.exists(meta_path):
            try:
                with open(meta_path, "r", encoding="utf-8") as f:
                    meta = json.load(f)
                meta["enabled"] = False
                with open(meta_path, "w", encoding="utf-8") as f:
                    json.dump(meta, f, indent=2)
            except Exception as e:
                logger.error(f"Failed to update metadata.json for {name}: {e}")
                return f"Failed to disable agent in metadata: {e}"

        # Stop and remove Docker container
        import subprocess
        subprocess.run(["docker", "rm", "-f", f"agent-{name.lower()}"], capture_output=True)

        # Remove from chat
        await self.chat_room.agent_leave(name)
        self.chat_room.unregister_agent(name)

        return f"Agent '{name}' has been disabled and its container stopped. It still exists in the data/agents/{name} directory. To bring them back, enable them in metadata.json and Sync Agents or restart."


class SyncAgentsTool(Tool):
    """Checks for active agents tracking against the filesystem and spawns missing containers."""

    def __init__(self, chat_room):
        super().__init__(
            "sync_agents",
            "Check if all agents defined in the data directory are currently running as containers. If not, spawn them. Returns a list of what was started.",
            args_schema={}
        )
        self.chat_room = chat_room

    async def run(self, **kwargs) -> str:
        try:
            # 1. Get list of agents from data/agents/
            base_dir = "data/agents"
            if not os.path.exists(base_dir):
                return "No agents directory found."
                
            defined_agents = []
            for name in os.listdir(base_dir):
                agent_path = os.path.join(base_dir, name)
                meta_path = os.path.join(agent_path, "metadata.json")
                if os.path.isdir(agent_path) and os.path.exists(meta_path):
                    try:
                        with open(meta_path, "r", encoding="utf-8") as f:
                            meta = json.load(f)
                        if meta.get("enabled", True):
                            defined_agents.append(name)
                    except Exception as e:
                        logger.error(f"Error reading metadata for {name}: {e}")
                    
            # 2. Get list of running docker containers
            import subprocess
            res = subprocess.run(["docker", "ps", "--format", "{{.Names}}"], capture_output=True, text=True)
            if res.returncode != 0:
                return f"Error checking docker: {res.stderr}"
                
            running_containers = [line.strip() for line in res.stdout.split('\n') if line.strip()]
            
            if not defined_agents:
                return "No agents defined in the data directory."
                
            # 4. Recreate all dynamic agents (excluding system agents)
            system_agents = {"Coordinator", "Creator", "Judge"}
            results = []
            for agent in defined_agents:
                if agent in system_agents:
                    continue  # We don't spawn system agents this way, docker-compose handles it
                
                # Proactively remove existing container
                subprocess.run(["docker", "stop", f"agent-{agent.lower()}"], capture_output=True)
                rm_res = subprocess.run(["docker", "rm", "-f", f"agent-{agent.lower()}"], capture_output=True, text=True)
                if rm_res.returncode != 0 and "No such container" not in rm_res.stderr:
                    logger.warning(f"Failed to remove existing container for {agent}: {rm_res.stderr}")
                
                cmd = [
                    "docker", "run", "-d", "--restart", "unless-stopped",
                    "--name", f"agent-{agent.lower()}",
                    "--network", "homeagent_default",
                    "-e", f"AGENT_NAME={agent}",
                    "-e", f"IRC_SERVER={os.environ.get('IRC_SERVER', 'ircserver')}",
                    "-e", "IRC_PORT=6667",
                    "-e", f"OLLAMA_HOST={os.environ.get('OLLAMA_HOST', 'http://host.docker.internal:11434')}",
                    "-v", "/var/run/docker.sock:/var/run/docker.sock",
                    "-v", f"{os.path.join(os.environ.get('HOST_PROJECT_ROOT', os.getcwd()), 'data', 'agents', agent)}:/app/data/agent",
                    "-v", f"{os.path.join(os.environ.get('HOST_PROJECT_ROOT', os.getcwd()), 'data', 'agents')}:/app/data/agents:ro",
                    "-v", f"{os.path.join(os.environ.get('HOST_PROJECT_ROOT', os.getcwd()), 'data', 'shared')}:/app/data/shared",
                    "homeagent-agent-coordinator"
                ]
                try:
                    logger.info(f"SyncAgentsTool: Spawning missing local agent {agent}...")
                    res = subprocess.run(cmd, capture_output=True, text=True)
                    if res.returncode == 0:
                        results.append(f"Successfully started container for {agent}.")
                    else:
                        cmd[-1] = "homeagent-agent-creator"
                        res2 = subprocess.run(cmd, capture_output=True, text=True)
                        if res2.returncode == 0:
                            results.append(f"Successfully started container for {agent}.")
                        else:
                            results.append(f"Failed to start {agent}: {res.stderr} or {res2.stderr}")
                except Exception as e:
                    results.append(f"Error starting {agent}: {e}")
                    
            return "\n".join(results)
            
        except Exception as e:
            logger.error(f"SyncAgentsTool error: {e}", exc_info=True)
            return f"Error syncing agents: {e}"
