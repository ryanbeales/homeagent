
import pytest
import asyncio
from unittest.mock import MagicMock, AsyncMock
from src.core.agent import Agent
from src.core.storage import StorageInterface
from src.core.llm import LLMRouter

@pytest.fixture
def mock_storage():
    return MagicMock(spec=StorageInterface)

@pytest.fixture
def mock_llm_router():
    router = MagicMock(spec=LLMRouter)
    router.get_response = AsyncMock()
    return router

@pytest.fixture
def agent(mock_storage, mock_llm_router):
    # Configure storage to return None for initial load (empty history)
    mock_storage.load.return_value = None
    
    # Patch the Agent to use our mock router
    agent = Agent("TestBot", "Tester", storage=mock_storage)
    agent.llm_router = mock_llm_router
    return agent

@pytest.mark.asyncio
async def test_agent_process_message_simple(agent, mock_llm_router):
    mock_llm_router.get_response.return_value = "Hello there!"
    
    # Needs a mock chat_room
    agent.chat_room = MagicMock()
    agent.chat_room.post_message = AsyncMock()
    agent.chat_room.get_recent_history.return_value = []
    
    await agent.process_message("Hi")
    
    mock_llm_router.get_response.assert_called_once()
    # Check chat_bridge
    agent.chat_room.post_message.assert_called_with("TestBot", "Hello there!")

@pytest.mark.asyncio
async def test_agent_tool_use(agent, mock_llm_router):
    agent.chat_room = MagicMock()
    agent.chat_room.post_message = AsyncMock()
    
    # LLM returns tool call first, then final answer
    # Using legacy JSON format which LLMRouter gives back
    mock_llm_router.get_response.side_effect = [
        '{"tool": "dummy_tool", "args": {"dummy": "test"}}',
        "Here is what I found."
    ]
    
    # Add dummy tool
    from src.tools.base import Tool
    mock_tool = MagicMock(spec=Tool)
    mock_tool.name = "dummy_tool"
    mock_tool.description = "A dummy tool"
    mock_tool.args_schema = {"dummy": "test"}
    mock_tool.run = AsyncMock(return_value="Dummy Result")
    agent.add_tool(mock_tool)
    
    await agent.process_message("Find info")
    
    assert mock_llm_router.get_response.call_count == 2
    mock_tool.run.assert_called_once_with(dummy="test")
    
    # Final response posted
    agent.chat_room.post_message.assert_called_with("TestBot", "Here is what I found.")

# Removed `test_ask_agent_tool` as `set_registry()` has been replaced by the IRC chat_room bridge.
