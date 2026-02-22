
from typing import List, Dict, Any
import json
import os
from src.core.storage import StorageInterface

class Memory:
    def __init__(self, agent_name: str, storage: StorageInterface, storage_collection: str = "memory", storage_key: str = None):
        self.agent_name = agent_name
        self.storage = storage
        self.storage_collection = storage_collection
        # Default key is agent_name if not provided
        self.storage_key = storage_key if storage_key else agent_name
        
        self.history: List[Dict[str, str]] = []
        self._load_history()

    def _load_history(self):
        data = self.storage.load(self.storage_collection, self.storage_key)
        if data:
            self.history = data.get("history", [])

    def _save_history(self):
        self.storage.save(self.storage_collection, self.storage_key, {"history": self.history})

    def add_message(self, role: str, content: str):
        self.history.append({"role": role, "content": content})
        self._save_history()

    def get_history(self) -> List[Dict[str, str]]:
        return self.history

    def clear(self):
        self.history = []
        self._save_history()

    def load_soul(self, soul_path: str) -> str:
        if os.path.exists(soul_path):
            with open(soul_path, "r") as f:
                return f.read()
        return ""
