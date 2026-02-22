
import abc
import json
import os
from typing import Any, Dict, List, Optional

class StorageInterface(abc.ABC):
    @abc.abstractmethod
    def save(self, collection: str, key: str, data: Any):
        """Saves data to the storage."""
        pass

    @abc.abstractmethod
    def load(self, collection: str, key: str) -> Optional[Any]:
        """Loads data from the storage."""
        pass

    @abc.abstractmethod
    def list_keys(self, collection: str) -> List[str]:
        """Lists all keys in a collection."""
        pass

    @abc.abstractmethod
    def delete(self, collection: str, key: str):
        """Deletes data from the storage."""
        pass

class JsonStorage(StorageInterface):
    def __init__(self, base_dir: str = "data"):
        self.base_dir = base_dir
        os.makedirs(self.base_dir, exist_ok=True)

    def _get_path(self, collection: str, key: str) -> str:
        collection_dir = os.path.join(self.base_dir, collection)
        os.makedirs(collection_dir, exist_ok=True)
        return os.path.join(collection_dir, f"{key}.json")

    def save(self, collection: str, key: str, data: Any):
        path = self._get_path(collection, key)
        with open(path, "w") as f:
            json.dump(data, f, indent=2)

    def load(self, collection: str, key: str) -> Optional[Any]:
        path = self._get_path(collection, key)
        if not os.path.exists(path):
            return None
        with open(path, "r") as f:
            return json.load(f)

    def list_keys(self, collection: str) -> List[str]:
        collection_dir = os.path.join(self.base_dir, collection)
        if not os.path.exists(collection_dir):
            return []
        keys = []
        for filename in os.listdir(collection_dir):
            if filename.endswith(".json"):
                keys.append(filename[:-5])
        return keys

    def delete(self, collection: str, key: str):
        path = self._get_path(collection, key)
        if os.path.exists(path):
            os.remove(path)
