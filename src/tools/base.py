
import abc
from typing import Any, Dict, Optional

class Tool(abc.ABC):
    def __init__(self, name: str, description: str, args_schema: Optional[Dict[str, str]] = None):
        self.name = name
        self.description = description
        self.args_schema = args_schema or {}

    @abc.abstractmethod
    async def run(self, **kwargs) -> Any:
        """Executes the tool logic."""
        pass
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description
        }
