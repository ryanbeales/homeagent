
import pytest
from unittest.mock import MagicMock
from src.core.knowledge import KnowledgeBank
from src.core.storage import StorageInterface

@pytest.fixture
def mock_storage():
    return MagicMock(spec=StorageInterface)

@pytest.fixture
def kb(mock_storage):
    return KnowledgeBank(mock_storage, agent_name="test_agent")

def test_add_entry(kb, mock_storage):
    topic = "Python"
    content = "A programming language."
    tags = ["code", "scripting"]
    
    entry_id = kb.add_entry(topic, content, tags)
    
    assert entry_id is not None
    mock_storage.save.assert_called_once()
    args, _ = mock_storage.save.call_args
    # args: collection, key, data
    assert args[0] == "knowledge_test_agent"
    assert args[2]["topic"] == topic
    assert args[2]["content"] == content

def test_search(kb, mock_storage):
    # Setup mock data
    mock_storage.list_keys.return_value = ["entry1", "entry2"]
    
    def load_side_effect(collection, key):
        if key == "entry1":
            return {"topic": "Python", "content": "Great language", "tags": ["code"]}
        if key == "entry2":
            return {"topic": "Java", "content": "Compiled language", "tags": ["enterprise"]}
        return None
    
    mock_storage.load.side_effect = load_side_effect
    
    # Test match
    results = kb.search("python")
    assert len(results) == 1
    assert results[0]["topic"] == "Python"
    
    # Test match via content
    results = kb.search("compiled")
    assert len(results) == 1
    assert results[0]["topic"] == "Java"
    
    # Test no match
    results = kb.search("ruby")
    assert len(results) == 0

def test_get_all_topics(kb, mock_storage):
    mock_storage.list_keys.return_value = ["k1", "k2"]
    mock_storage.load.side_effect = [
        {"topic": "T1"},
        {"topic": "T2"}
    ]
    
    topics = kb.get_all_topics()
    assert "T1" in topics
    assert "T2" in topics
