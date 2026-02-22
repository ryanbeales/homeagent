
import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from src.core.llm import LLMRouter, OllamaProvider

@pytest.mark.asyncio
async def test_router_low_complexity():
    router = LLMRouter()
    
    # Mock providers
    router.local_ollama = MagicMock(spec=OllamaProvider)
    router.local_ollama.generate_response = AsyncMock(return_value="Local response")
    
    router.remote_ollama = MagicMock(spec=OllamaProvider)
    
    response = await router.get_response("hi", [], complexity="low")
    
    assert response == "Local response"
    router.local_ollama.generate_response.assert_called_once()
    router.remote_ollama.generate_response.assert_not_called()

@pytest.mark.asyncio
async def test_router_high_complexity_no_remote():
    # Only tests missing remote fallback (local should just throw error)
    router = LLMRouter()
    
    router.local_ollama = MagicMock(spec=OllamaProvider)
    router.local_ollama.generate_response = AsyncMock(side_effect=Exception("Connection failed"))
    
    with pytest.raises(Exception, match="Connection failed"):
        await router.get_response("complex task", [], complexity="high")
    
    router.local_ollama.generate_response.assert_called_once()
