
import pytest
from unittest.mock import MagicMock
from src.core.memory import Memory
from src.core.storage import StorageInterface

@pytest.fixture
def mock_storage():
    return MagicMock(spec=StorageInterface)

@pytest.fixture
def memory(mock_storage):
    # Retrieve what was stored in constructor
    mock_storage.load.return_value = {"history": [{"role": "system", "content": "init"}]}
    return Memory("test_agent", mock_storage)

def test_initial_load(memory, mock_storage):
    assert len(memory.history) == 1
    assert memory.history[0]["content"] == "init"
    mock_storage.load.assert_called_with("memory", "test_agent")

def test_add_message(memory, mock_storage):
    memory.add_message("user", "hello")
    
    assert len(memory.history) == 2
    assert memory.history[-1]["content"] == "hello"
    
    mock_storage.save.assert_called()
    args, _ = mock_storage.save.call_args
    assert args[0] == "memory"
    assert args[1] == "test_agent"
    assert "history" in args[2]

def test_clear(memory, mock_storage):
    memory.clear()
    assert len(memory.history) == 0
    mock_storage.save.assert_called()

def test_load_soul(tmp_path, memory):
    soul_file = tmp_path / "SOUL.md"
    soul_file.write_text("Be helpful.")
    
    content = memory.load_soul(str(soul_file))
    assert content == "Be helpful."
    
    start_missing = memory.load_soul("nonexistent")
    assert start_missing == ""
