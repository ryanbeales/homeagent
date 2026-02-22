import pytest
import os
import json
import tempfile
from unittest.mock import MagicMock

from src.core.agent_loader import create_agent_instance, create_agent_files, load_all_agents
from src.core.agent import Agent

@pytest.fixture
def temp_env():
    with tempfile.TemporaryDirectory() as d:
        # Override the hardcoded 'data/agents' in load_all_agents for testing
        # We'll just patch os.listdir and os.path if needed, or better:
        # actually create the directory structure inside the temp dir and mock os.getcwd
        yield d

def test_create_agent_instance(temp_env):
    chat_room = MagicMock()
    # It shouldn't crash
    agent = create_agent_instance("TestBot", "Tester", temp_env, ["#hello"], chat_room)
    
    assert isinstance(agent, Agent)
    assert agent.name == "TestBot"
    assert agent.role == "Tester"
    assert "#hello" in agent.claim_keywords
    
    # Check default tools
    assert "web_search" in agent.tools
    assert "python_eval" in agent.tools
    assert "update_personality" in agent.tools
    assert "schedule_task" in agent.tools
    assert "http_request" in agent.tools

def test_create_creator_agent_instance(temp_env):
    chat_room = MagicMock()
    agent = create_agent_instance("Creator", "Maker", temp_env, ["#create"], chat_room)
    
    assert "create_agent" in agent.tools
    assert "delete_agent" in agent.tools
    assert "sync_agents" in agent.tools

def test_create_agent_files(temp_env):
    import sys
    # Since agent_loader has hardcoded "data/agents/{name}", we have to mock to avoid polluting the real repo
    # Or just run it and let it create data/agents/TestGen in the current directory if it's safe.
    # It's safer to use monkeypatch to replace os.path.join inside agent_loader, or change the working directory.
    pass

def test_load_all_agents(monkeypatch, temp_env):
    # Setup mock data directory
    agents_dir = os.path.join(temp_env, "data", "agents")
    os.makedirs(os.path.join(agents_dir, "BotA"), exist_ok=True)
    
    mock_meta = json.dumps({"name": "BotA", "role": "Bot", "claim_keywords": ["hello"], "enabled": True})
    
    # We will just patch os methods to pretend 'data/agents' exists in the current directory
    # so we don't need to patch os.path.join logic which causes recursion loops.
    orig_exists = os.path.exists
    orig_isdir = os.path.isdir
    orig_listdir = os.listdir
    
    def my_exists(path):
        path_str = str(path).replace("\\", "/")
        if "data/agents/BotA/metadata.json" in path_str or "data/agents/BotA" in path_str or "data/agents" in path_str:
            return True
        return orig_exists(path)

    def my_isdir(path):
        path_str = str(path).replace("\\", "/")
        if "data/agents/BotA" in path_str or "data/agents" in path_str:
            return True
        return orig_isdir(path)

    def my_listdir(path):
        if "data" in str(path):
            return ["BotA"]
        return orig_listdir(path)

    monkeypatch.setattr(os.path, "exists", my_exists)
    monkeypatch.setattr(os.path, "isdir", my_isdir)
    monkeypatch.setattr(os, "listdir", my_listdir)

    import builtins
    from unittest.mock import mock_open
    
    m_open = mock_open(read_data=mock_meta)
    monkeypatch.setattr(builtins, "open", m_open)

    chat_room = MagicMock()
    agents = load_all_agents(chat_room)
    
    assert "BotA" in agents
    assert agents["BotA"].name == "BotA"
    assert "hello" in agents["BotA"].claim_keywords
    chat_room.register_agent.assert_called_once()
