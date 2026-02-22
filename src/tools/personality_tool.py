
import os
from src.tools.base import Tool
from src.core.logger import logger


class UpdatePersonalityTool(Tool):
    """Allows an agent to update its own PERSONALITY.md file."""

    def __init__(self, agent_name: str, agent_dir: str):
        super().__init__(
            "update_personality",
            f"Update YOUR OWN personality document (PERSONALITY.md for {agent_name}). "
            f"This writes to YOUR file only — you CANNOT update other agents' personalities. "
            f"Use this to evolve and improve over time based on feedback. Write the FULL new content.",
            args_schema={
                "new_content": "The complete new content for your PERSONALITY.md file. Write in markdown format."
            }
        )
        self.agent_name = agent_name
        self.agent_dir = agent_dir

    async def run(self, new_content: str) -> str:
        try:
            personality_path = os.path.join(self.agent_dir, "PERSONALITY.md")
            os.makedirs(self.agent_dir, exist_ok=True)

            with open(personality_path, "w", encoding="utf-8") as f:
                f.write(new_content)

            logger.info(f"Agent {self.agent_name} updated their personality at: {personality_path}")
            return f"Your PERSONALITY.md has been updated. Changes will take effect on your next message."
        except Exception as e:
            logger.error(f"Error updating personality for {self.agent_name}: {e}")
            return f"Error updating personality: {e}"
