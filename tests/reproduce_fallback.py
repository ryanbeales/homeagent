
import asyncio
from src.core.llm import LLMRouter, LLMProvider
from unittest.mock import MagicMock, AsyncMock

async def test_fallback():
    print("Testing LLM Router Fallback...")
    
    router = LLMRouter()
    
    # Mock local ollama to fail
    router.local_ollama.generate_response = AsyncMock(side_effect=ValueError("Simulated Empty Response"))
    
    # Mock remote ollama to succeed
    router.remote_ollama.generate_response = AsyncMock(return_value="Remote Success")
    
    response = await router.get_response("Test prompt", [])
    
    print(f"Response: {response}")
    if response == "Remote Success":
        print("PASS: Fallback to remote successful.")
    else:
        print(f"FAIL: Fallback failed. Got: {response}")

if __name__ == "__main__":
    asyncio.run(test_fallback())
