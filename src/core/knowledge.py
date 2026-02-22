
from typing import List, Dict, Any
from src.core.storage import StorageInterface
import time

class KnowledgeBank:
    def __init__(self, storage: StorageInterface, agent_name: str):
        self.storage = storage
        self.agent_name = agent_name
        self.collection = f"knowledge_{agent_name}"

    def add_entry(self, topic: str, content: str, tags: List[str] = []):
        """Adds a new knowledge entry."""
        entry_id = f"{topic.lower().replace(' ', '_')}_{int(time.time())}"
        entry = {
            "topic": topic,
            "content": content,
            "tags": tags,
            "timestamp": time.time()
        }
        self.storage.save(self.collection, entry_id, entry)
        return entry_id

    def search(self, query: str) -> List[Dict[str, Any]]:
        """
        Simple keyword search.
        In a real app, this would use vector embeddings.
        """
        keys = self.storage.list_keys(self.collection)
        results = []
        query_lower = query.lower()
        
        for key in keys:
            entry = self.storage.load(self.collection, key)
            if entry:
                # Check topic, content, and tags
                if (query_lower in entry["topic"].lower() or 
                    query_lower in entry["content"].lower() or 
                    any(query_lower in tag.lower() for tag in entry["tags"])):
                    results.append(entry)
        
        return results

    def get_all_topics(self) -> List[str]:
        keys = self.storage.list_keys(self.collection)
        topics = set()
        for key in keys:
            entry = self.storage.load(self.collection, key)
            if entry:
                topics.add(entry["topic"])
        return list(topics)
