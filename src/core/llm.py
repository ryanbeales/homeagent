
import os
import abc
from typing import List, Dict, Any
from enum import Enum
import ollama
import json
from src.core.logger import logger

class LLMProviderType(Enum):
    OLLAMA = "ollama"

class LLMProvider(abc.ABC):
    @abc.abstractmethod
    async def generate_response(self, prompt: str, history: List[Dict[str, str]], system_prompt: str = "") -> str:
        """Generates a response from the LLM."""
        pass

from src.core.config import settings

class OllamaProvider(LLMProvider):
    def __init__(self, model: str = None, base_url: str = None):
        self.model = model or settings.ollama_model
        self.client = ollama.AsyncClient(host=base_url or settings.ollama_host)

    async def generate_response(self, prompt: str, history: List[Dict[str, str]], system_prompt: str = "", tools: List[Dict[str, Any]] = None) -> str:
        messages = []
        
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
            
        messages.extend(history)
        messages.append({"role": "user", "content": prompt})

        logger.info(f"Sending request to Ollama ({self.model}). Message count: {len(messages)}")
        logger.debug(f"Messages: {json.dumps(messages, default=str)}")
        
        # Log tool usage
        if tools:
            logger.info(f"Sending {len(tools)} tools to Ollama.")

        try:
            # Request larger context window to prevent truncation/empty responses
            import time
            start_time = time.time()
            logger.debug(f"Sending to Ollama (Context: 8192)...")
            
            response = await self.client.chat(
                model=self.model, 
                messages=messages,
                tools=tools, # Pass native tools
                options={'num_ctx': 8192} 
            )
            # logger.debug(f"Full Ollama response: {response}")
            
            message = response.get('message', {})
            content = message.get('content', '')
            tool_calls = message.get('tool_calls', [])
            
            # If tool calls exist, convert to legacy JSON format for Agent.py compatibility
            if tool_calls:
                logger.info(f"Ollama returned {len(tool_calls)} native tool calls.")
                # We only handle one tool call at a time for now due to Agent loop structure
                first_call = tool_calls[0]
                tool_name = first_call.get('function', {}).get('name')
                tool_args = first_call.get('function', {}).get('arguments', {})
                
                # Construct legacy JSON string
                legacy_json = json.dumps({
                    "tool": tool_name,
                    "args": tool_args
                })
                return legacy_json
            
            # Normal text response
            logger.info(f"Ollama response received (Length: {len(content)}): {content[:50]}...")
            
            if not content:
                import time
                logger.warning(f"Ollama returned empty response! (Duration: {time.time() - start_time:.2f}s)")
                logger.debug(f"RAW OLLAMA RESPONSE: {json.dumps(response, default=str)}")
                logger.debug(f"SENT MESSAGES: {json.dumps(messages, default=str)}")
                # Don't raise error, just return empty string to avoid crashing loop
                return "" 
                
            return content
        except Exception as e:
            logger.error(f"Ollama Error ({self.model}): {e}")
            raise e # Re-raise to allow router to fallback

class LLMRouter:
    def __init__(self):
        # Local Ollama
        self.local_ollama = OllamaProvider()
        
        # Remote Ollama removed as per user request (too slow)
        self.remote_ollama = None

    async def get_response(self, prompt: str, history: List[Dict[str, str]], system_prompt: str = "", complexity: str = "low", tools: List[Dict[str, Any]] = None) -> str:
        """
        Routes the request to the appropriate LLM.
        Currently defaults strictly to local Ollama (using settings model).
        """
        # Default to local model
        logger.info("Routing to Local Ollama")
        try:
            return await self.local_ollama.generate_response(prompt, history, system_prompt, tools)
        except Exception as e:
            logger.error(f"Local Ollama failed: {e}")
            raise e
