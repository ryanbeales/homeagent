import pytest
import os
import asyncio
from unittest.mock import MagicMock, AsyncMock, patch

from src.core.agent_loop import StdoutChatBridge, main

@pytest.mark.asyncio
async def test_stdout_chat_bridge():
    bridge = StdoutChatBridge()
    # It just prints, so we can mock builtins.print to check
    with patch("builtins.print") as mock_print:
        await bridge.post_message("TestBot", "Hello")
        mock_print.assert_called_with("Hello", flush=True)

        await bridge.agent_join("TestBot")
        mock_print.assert_called_with("* TestBot has joined the chat", flush=True)

        await bridge.agent_leave("TestBot")
        mock_print.assert_called_with("* TestBot has left the chat", flush=True)

@pytest.mark.asyncio
async def test_agent_loop_main(monkeypatch):
    """Test the main setup logic of the agent loop without running the infinite loop."""
    monkeypatch.setenv("AGENT_NAME", "TestBot")
    
    # We want to mock asyncio.get_event_loop().run_in_executor to raise EOFError or return empty string 
    # to immediately break the infinite stdin reading loop.
    async def mock_run_in_executor(*args, **kwargs):
        return "" # Empty string simulates EOF and breaks loop

    mock_loop = MagicMock()
    mock_loop.run_in_executor = mock_run_in_executor
    monkeypatch.setattr(asyncio, "get_event_loop", lambda: mock_loop)
    
    # Mock create_agent_instance
    mock_agent = MagicMock()
    mock_agent.personality = "You are a test."
    mock_agent.process_message = AsyncMock()
    
    monkeypatch.setattr("src.core.agent_loop.create_agent_instance", lambda *args, **kwargs: mock_agent)
    monkeypatch.setattr("os.makedirs", lambda *args, **kwargs: None)
    
    # Mock builtins open for log file
    from unittest.mock import mock_open
    m_open = mock_open(read_data='{}')
    monkeypatch.setattr("builtins.open", m_open)
    monkeypatch.setattr("os.path.exists", lambda p: False) # no metadata.json
    
    # Suppress print and sys.stdout writes during test
    monkeypatch.setattr("builtins.print", lambda *args, **kwargs: None)
    monkeypatch.setattr("sys.stdout.write", lambda *args, **kwargs: None)
    monkeypatch.setattr("sys.stderr.write", lambda *args, **kwargs: None)
    
    # Run main - it should initialize, set up tools, and break immediately on first stdin read
    await main()
    
    # Verify Tools were added
    assert mock_agent.add_tool.call_count >= 4 # run, file_read, file_write, eval etc.
