
import json
import os
from typing import List

from src.core.agent import Agent
from src.core.storage import JsonStorage
from src.core.logger import logger
from src.tools.web_search import WebSearchTool
from src.tools.python_eval import PythonEvalTool
from src.tools.personality_tool import UpdatePersonalityTool
from src.tools.scheduler import AgentScheduler, ScheduleTaskTool, ListScheduledTasksTool, RemoveScheduledTaskTool
from src.tools.creator_tools import CreateAgentTool, DeleteAgentTool, SyncAgentsTool
from src.tools.http_request import HttpRequestTool


def create_agent_instance(name: str, role: str, agent_dir: str, claim_keywords: List[str], chat_room) -> Agent:
    """Create a single Agent instance with all appropriate tools."""
    agent_storage = JsonStorage(base_dir=agent_dir)
    personality_path = os.path.join(agent_dir, "PERSONALITY.md")

    agent = Agent(
        name=name,
        role=role,
        personality_path=personality_path,
        storage=agent_storage,
        claim_keywords=claim_keywords,
    )

    # Attach the persistent scheduler daemon
    agent_scheduler = AgentScheduler(name, agent_dir, chat_room)
    try:
        agent_scheduler.start()
    except RuntimeError as e:
        logger.warning(f"Could not start scheduler for {name} automatically (no event loop?): {e}")
        
    # Store it on the agent so we can cleanly shut it down if needed later
    agent.scheduler_daemon = agent_scheduler

    # Tools available to ALL agents
    agent.add_tool(WebSearchTool())
    agent.add_tool(PythonEvalTool())
    agent.add_tool(UpdatePersonalityTool(name, agent_dir))
    agent.add_tool(ScheduleTaskTool(agent_scheduler))
    agent.add_tool(ListScheduledTasksTool(agent_scheduler))
    agent.add_tool(RemoveScheduledTaskTool(agent_scheduler))
    agent.add_tool(HttpRequestTool())

    # Creator-specific tools
    if name == "Creator":
        agent.add_tool(CreateAgentTool(chat_room))
        agent.add_tool(DeleteAgentTool(chat_room))
        agent.add_tool(SyncAgentsTool(chat_room))

    return agent


def create_agent_files(name: str, role: str, personality: str, claim_keywords: List[str] = None):
    """Create agent directory and files on disk."""
    agent_dir = os.path.join("data", "agents", name)
    os.makedirs(agent_dir, exist_ok=True)

    # Metadata
    meta_path = os.path.join(agent_dir, "metadata.json")
    if not os.path.exists(meta_path):
        metadata = {
            "name": name,
            "role": role,
            "claim_keywords": claim_keywords or [],
            "enabled": True
        }
        with open(meta_path, "w", encoding="utf-8") as f:
            json.dump(metadata, f, indent=2)

    # Personality
    personality_path = os.path.join(agent_dir, "PERSONALITY.md")
    if not os.path.exists(personality_path):
        with open(personality_path, "w", encoding="utf-8") as f:
            f.write(personality.strip() + "\n")

    return agent_dir


def load_all_agents(chat_room) -> dict:
    """
    Load all agents from data/agents/ directory.
    Returns dict of name -> Agent.
    """
    agents = {}
    base_dir = "data/agents"
    if not os.path.exists(base_dir):
        os.makedirs(base_dir, exist_ok=True)
        return agents

    for agent_name in os.listdir(base_dir):
        agent_path = os.path.join(base_dir, agent_name)
        if not os.path.isdir(agent_path):
            continue

        meta_path = os.path.join(agent_path, "metadata.json")
        if not os.path.exists(meta_path):
            logger.warning(f"Skipping agent dir without metadata: {agent_name}")
            continue

        try:
            with open(meta_path, "r", encoding="utf-8") as f:
                meta = json.load(f)

            name = meta.get("name", agent_name)
            role = meta.get("role", "Agent")
            keywords = meta.get("claim_keywords", [])
            is_enabled = meta.get("enabled", True)

            if not is_enabled:
                logger.debug(f"Skipping disabled agent: {name}")
                continue

            agent = create_agent_instance(name, role, agent_path, keywords, chat_room)
            chat_room.register_agent(agent)
            agents[name] = agent
            logger.info(f"Loaded agent: {name} (keywords: {keywords})")

        except Exception as e:
            logger.error(f"Failed to load agent {agent_name}: {e}", exc_info=True)

    return agents
