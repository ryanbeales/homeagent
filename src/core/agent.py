
import asyncio
import inspect
import json
import re
from typing import Any, Dict, List, Optional

from src.core.llm import LLMRouter
from src.core.memory import Memory
from src.core.storage import JsonStorage, StorageInterface
from src.core.knowledge import KnowledgeBank
from src.core.logger import logger


class Agent:
    """
    Unified agent class for the IRC-style chat system.
    
    All agents are instances of this class. Specialization comes from:
    - PERSONALITY.md (system prompt)
    - claim_keywords (which messages to respond to)
    - tools (which tools are available)
    """

    def __init__(
        self,
        name: str,
        role: str,
        personality_path: str = "",
        storage: StorageInterface = None,
        claim_keywords: List[str] = None,
    ):
        self.name = name
        self.role = role
        self.claim_keywords = claim_keywords or []
        self.storage = storage if storage else JsonStorage()
        self.chat_room = None  # Set by ChatRoom.register_agent()

        # Private memory (agent's own scratch notes)
        self.memory = Memory(name, self.storage, storage_collection="", storage_key="memory")

        # Knowledge bank (private to this agent)
        self.knowledge_bank = KnowledgeBank(self.storage, name)

        # LLM router
        self.llm_router = LLMRouter()

        # Load personality
        self.personality = ""
        self.personality_path = personality_path
        if personality_path:
            self._load_personality(personality_path)

        # Build base system prompt
        self._build_system_prompt()

        # Tools registry
        self.tools: Dict[str, Any] = {}
        self._setup_default_tools()

    def _load_personality(self, path: str):
        """Load personality from PERSONALITY.md file."""
        import os
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                self.personality = f.read()
        else:
            logger.warning(f"Personality file not found: {path}")

    def _build_system_prompt(self):
        """Build the system prompt from identity + personality."""
        self.system_prompt = f"You are {self.name}, {self.role}."
        self.system_prompt += "\n\nYou are in a shared IRC-style chat room with other agents and a human user."
        self.system_prompt += "\nAll messages you send will be visible to everyone in the chat."
        self.system_prompt += "\nTo mention another agent, use @AgentName."
        self.system_prompt += "\nTo mention the user, use @User."
        self.system_prompt += "\n\nYou have access to your own private Knowledge Bank and tools."
        
        if self.personality:
            self.system_prompt += f"\n\nYOUR PERSONALITY & INSTRUCTIONS:\n{self.personality}"

    def reload_personality(self):
        """Reload personality from disk and rebuild system prompt."""
        if self.personality_path:
            self._load_personality(self.personality_path)
            self._build_system_prompt()
            logger.info(f"Agent {self.name} personality reloaded.")

    def _setup_default_tools(self):
        """Set up tools available to all agents."""
        from src.tools.base import Tool

        # Search Knowledge
        class SearchKnowledgeTool(Tool):
            def __init__(self, kb: KnowledgeBank):
                super().__init__(
                    "search_knowledge",
                    "Search your PRIVATE knowledge bank for a specific topic.",
                    args_schema={"query": "The search query to find in your knowledge bank."}
                )
                self.kb = kb

            async def run(self, query: str) -> str:
                results = self.kb.search(query)
                if not results:
                    return "No relevant knowledge found."
                return "\n".join([f"- {r['topic']}: {r['content']}" for r in results[:5]])

        # Add Knowledge
        class AddKnowledgeTool(Tool):
            def __init__(self, kb: KnowledgeBank):
                super().__init__(
                    "add_knowledge",
                    "Add a new entry to your private knowledge bank for future reference.",
                    args_schema={
                        "topic": "The topic of this knowledge entry.",
                        "content": "The content/information to store.",
                        "tags": "Comma-separated tags for categorization."
                    }
                )
                self.kb = kb

            async def run(self, topic: str, content: str, tags: str = "") -> str:
                tag_list = [t.strip() for t in tags.split(",") if t.strip()] if tags else []
                self.kb.add_entry(topic, content, tag_list)
                return f"Added knowledge on '{topic}'."

        self.add_tool(SearchKnowledgeTool(self.knowledge_bank))
        self.add_tool(AddKnowledgeTool(self.knowledge_bank))

    def add_tool(self, tool):
        """Register a tool with this agent."""
        self.tools[tool.name] = tool

    def _build_native_tools(self) -> List[dict]:
        """Build tool schemas for LLM native tool calling."""
        native_tools = []
        for tool in self.tools.values():
            run_method = tool.run
            sig = inspect.signature(run_method)

            properties = {}
            required = []

            for param_name, param in sig.parameters.items():
                if param_name in ['self', 'kwargs', 'output_callback']:
                    continue

                # Infer type from annotation
                param_type = "string"
                if param.annotation == int:
                    param_type = "integer"
                elif param.annotation == float:
                    param_type = "number"
                elif param.annotation == bool:
                    param_type = "boolean"
                elif param.annotation == list:
                    param_type = "array"

                arg_desc = tool.args_schema.get(param_name, f"Argument: {param_name}")
                properties[param_name] = {
                    "type": param_type,
                    "description": arg_desc
                }

                if param.default == inspect.Parameter.empty:
                    required.append(param_name)

            tool_schema = {
                'type': 'function',
                'function': {
                    'name': tool.name,
                    'description': tool.description,
                    'parameters': {
                        'type': 'object',
                        'properties': properties,
                        'required': required
                    }
                }
            }
            native_tools.append(tool_schema)

        return native_tools

    def _build_context_messages(self) -> List[Dict[str, str]]:
        """Build LLM context from shared chat history."""
        messages = []
        if self.chat_room:
            recent = self.chat_room.get_recent_history(limit=30)
            for msg in recent:
                if msg.sender == "User":
                    messages.append({"role": "user", "content": msg.content})
                elif msg.sender == self.name:
                    messages.append({"role": "assistant", "content": msg.content})
                elif msg.sender == "System":
                    messages.append({"role": "system", "content": msg.content})
                else:
                    # Other agents' messages — show as user messages with sender prefix
                    messages.append({"role": "user", "content": f"<{msg.sender}> {msg.content}"})
        return messages

    async def process_message(self, user_message: str):
        """
        Process a message from the chat room and post response.
        This is the main entry point called by ChatRoom.
        """
        logger.info(f"Agent {self.name} processing: {user_message[:80]}...")

        # Reload personality in case it was updated
        self.reload_personality()

        # Build context from shared chat history
        context_history = self._build_context_messages()

        # Build system prompt with strategy hints
        current_system_prompt = self.system_prompt

        # Coordinator gets a delegation-first strategy
        if self.name == "Coordinator":
            current_system_prompt += "\n\nSTRATEGY:"
            current_system_prompt += "\n1. DELEGATE — Check the chat members. If a specialist agent could handle this, @mention them immediately."
            current_system_prompt += "\n2. CREATE — If no specialist exists, ask @Creator to make one."
            current_system_prompt += "\n3. ONLY answer directly if the question is about you, the system, or is a greeting."
            current_system_prompt += "\nYou are a ROUTER, not an expert. NEVER answer domain questions yourself."
        else:
            current_system_prompt += "\n\nSTRATEGY: When asked a question or task:"
            current_system_prompt += "\n1. FIRST, determine if the request falls within your specific area of expertise or persona."
            current_system_prompt += "\n2. If the request is OUTSIDE your expertise, DO NOT attempt to answer it or use web search. Instead, apologize and @mention an appropriate agent or the @Coordinator to handle it. You MUST pass along all the relevant context from the original request (e.g., location, specific constraints) when you tag them so they know exactly what to do."
            current_system_prompt += "\n3. If the request IS within your expertise, check if you have a TOOL that can accomplish the task."
            current_system_prompt += "\n4. Check your own knowledge bank."
            current_system_prompt += "\n5. If you need help, mention another agent in chat with @AgentName."
            current_system_prompt += "\n6. Use 'web_search' to find information online."
            current_system_prompt += "\n7. When done with a task, use 'signal_task_complete'."

        # Self-improvement instructions for ALL agents
        current_system_prompt += "\n\nSELF-IMPROVEMENT:"
        current_system_prompt += "\n- You are expected to continuously learn and improve your capabilities."
        current_system_prompt += "\n- When you complete a major task, proactively ask @Judge for feedback on your performance."
        current_system_prompt += "\n- When the Judge gives you feedback, use the 'update_personality' tool to permanently incorporate their lessons into your configuration."
        current_system_prompt += "\n- Pay attention to recurring feedback patterns and proactively become a better agent."

        if self.tools:
            current_system_prompt += "\n\nYou have access to external tools. Use them when necessary."

        native_tools = self._build_native_tools()
        logger.info(f"Agent {self.name} has tools available: {list(self.tools.keys())}")

        # ReAct loop — allow up to 5 iterations for tool use
        for iteration in range(5):
            # First iteration: use the original user message as the prompt
            # Subsequent iterations: use the tool result summary as the prompt
            if iteration == 0:
                prompt = user_message
            else:
                # The tool result was appended to context_history; use it as the prompt
                prompt = "Now respond to the user based on the tool results above. Do NOT call another tool unless absolutely necessary. Give a direct, helpful answer."

            try:
                response = await self.llm_router.get_response(
                    prompt=prompt,
                    history=context_history,
                    system_prompt=current_system_prompt,
                    complexity="low",
                    tools=native_tools
                )
            except Exception as e:
                logger.error(f"LLM Error in Agent {self.name}: {e}")
                if self.chat_room:
                    await self.chat_room.post_message(
                        self.name, f"I encountered an error while thinking: {e}"
                    )
                return

            if not response or not response.strip():
                logger.warning(f"Agent {self.name} received empty response from LLM.")
                if iteration < 4:
                    continue
                if self.chat_room:
                    await self.chat_room.post_message(self.name, "...")
                return

            # Check for tool calls in response
            tool_call = self._parse_tool_call(response)
            if tool_call:
                tool_name, tool_args = tool_call
                if tool_name in self.tools:
                    logger.info(f"Agent {self.name} executing tool: {tool_name}")

                    try:
                        # Inject output_callback if supported
                        run_method = self.tools[tool_name].run
                        result = await run_method(**tool_args)
                        logger.info(f"Tool {tool_name} result: {str(result)[:200]}")

                        # Add tool result to context for next iteration
                        context_history.append({"role": "assistant", "content": response})
                        context_history.append({"role": "system", "content": f"Tool '{tool_name}' result: {result}"})
                        continue

                    except Exception as e:
                        logger.error(f"Tool execution error: {e}")
                        context_history.append({"role": "assistant", "content": response})
                        context_history.append({"role": "system", "content": f"Error executing tool '{tool_name}': {e}"})
                        continue
                else:
                    logger.warning(f"Agent {self.name} tried to use unknown tool: {tool_name}")
                    context_history.append({"role": "assistant", "content": response})
                    context_history.append({"role": "system", "content": f"Tool '{tool_name}' not available. Reply directly instead."})
                    continue

            # No tool call — this is the final response, post to chat
            if self.chat_room:
                await self.chat_room.post_message(self.name, response)
            return

        # Exhausted iterations
        if self.chat_room:
            await self.chat_room.post_message(
                self.name, "I'm having trouble coming up with a response."
            )

    def _parse_tool_call(self, response: str) -> Optional[tuple]:
        """
        Parse a tool call from LLM response.
        Returns (tool_name, tool_args) or None.
        """
        json_str = None

        # Strategy 1: Direct JSON
        stripped = response.strip()
        if stripped.startswith("{") and stripped.endswith("}"):
            try:
                test_json = json.loads(stripped)
                if "tool" in test_json and "args" in test_json:
                    json_str = stripped
            except json.JSONDecodeError:
                pass

        # Strategy 2: Extract JSON from text
        if not json_str:
            start_index = response.find('{')
            if start_index != -1:
                brace_count = 0
                for i, char in enumerate(response[start_index:], start=start_index):
                    if char == '{':
                        brace_count += 1
                    elif char == '}':
                        brace_count -= 1
                        if brace_count == 0:
                            json_str = response[start_index:i + 1]
                            break

        if json_str and '"tool":' in json_str and '"args":' in json_str:
            try:
                parsed = json.loads(json_str)
                return parsed.get("tool"), parsed.get("args", {})
            except json.JSONDecodeError:
                pass

        return None
