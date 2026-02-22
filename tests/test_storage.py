
import os
import json
import pytest
from src.core.storage import JsonStorage

@pytest.fixture
def storage(tmp_path):
    # Use a temporary directory for tests
    return JsonStorage(base_dir=str(tmp_path))

def test_save_and_load(storage):
    collection = "test_col"
    key = "test_key"
    data = {"foo": "bar"}
    
    storage.save(collection, key, data)
    loaded = storage.load(collection, key)
    
    assert loaded == data

def test_load_nonexistent(storage):
    loaded = storage.load("nonexistent", "key")
    assert loaded is None

def test_list_keys(storage):
    collection = "test_list"
    storage.save(collection, "k1", {"a": 1})
    storage.save(collection, "k2", {"b": 2})
    
    keys = storage.list_keys(collection)
    assert "k1" in keys
    assert "k2" in keys
    assert len(keys) == 2

def test_delete(storage):
    collection = "test_del"
    key = "del_key"
    storage.save(collection, key, {})
    
    assert storage.load(collection, key) is not None
    storage.delete(collection, key)
    assert storage.load(collection, key) is None
