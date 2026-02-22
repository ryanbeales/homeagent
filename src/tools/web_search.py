
import httpx
from typing import List, Dict, Any
from src.tools.base import Tool

from src.core.config import settings

class WebSearchTool(Tool):
    def __init__(self, base_url: str = None):
        super().__init__(
            name="web_search",
            description="Search the web using Searxng. Useful for finding current information."
        )
        self.base_url = base_url or settings.searxng_url

    async def run(self, query: str) -> str:
        async with httpx.AsyncClient(follow_redirects=True) as client:
            try:
                params = {
                    "q": query,
                    "format": "json"
                }
                response = await client.get(self.base_url, params=params)
                response.raise_for_status()
                data = response.json()
                
                results = data.get("results", [])
                if not results:
                    return "No results found."
                
                formatted_results = []
                for result in results[:5]: # Content limit to top 5
                    formatted_results.append(f"- **{result.get('title')}**: {result.get('content')} ({result.get('url')})")
                
                return "\n".join(formatted_results)
            except Exception as e:
                return f"Error performing search: {str(e)}"
