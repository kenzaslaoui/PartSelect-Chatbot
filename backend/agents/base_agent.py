"""
Simplified Base Agent class - direct tool execution with LLM response generation.

This implements a simplified agentic pattern:
1. Agent receives query with context from orchestrator
2. Agent selects and executes the most relevant tool based on intent
3. Agent uses LLM to generate human-friendly response from tool results
4. Returns response immediately (no reasoning loops)

Uses centralized system prompts from prompts.py for domain boundaries and tone.
"""

import logging
import json
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass
from .deepseek_client import DeepseekClient
from .prompts import CLIENT_FACING_SYSTEM_PROMPT
from rag.chroma_db import ChromaDBManager

logger = logging.getLogger(__name__)


@dataclass
class Tool:
    """Definition of a tool an agent can use."""
    name: str
    description: str
    func: Callable
    required_params: List[str]
    optional_params: List[str] = None

    def __post_init__(self):
        if self.optional_params is None:
            self.optional_params = []


@dataclass
class AgentThought:
    """Represents a single reasoning step."""
    thought: str
    action: str
    action_input: Dict[str, Any]
    observation: Optional[str] = None
    reasoning: Optional[str] = None


class BaseAgent:
    """Base class for all agentic agents with tool use and reasoning."""

    def __init__(
        self,
        name: str,
        description: str,
        deepseek_client: Optional[DeepseekClient] = None,
        chroma_manager: Optional[ChromaDBManager] = None,
        model: str = "deepseek-chat"
    ):
        """
        Initialize agent.

        Args:
            name: Agent name
            description: Agent description/role
            deepseek_client: Deepseek LLM client
            chroma_manager: ChromaDB manager for retrievals
            model: LLM model to use (default: 'deepseek-chat' for fast responses)
        """
        self.name = name
        self.description = description
        self.model = model

        # Create client with specified model
        if deepseek_client:
            self.deepseek = deepseek_client
            self.deepseek.model = model  # Override model
        else:
            self.deepseek = DeepseekClient(model=model)

        self.chroma_manager = chroma_manager or ChromaDBManager()
        self.tools: Dict[str, Tool] = {}

        logger.info(f"Initialized agent: {name} with model: {model}")

    def register_tool(self, tool: Tool) -> None:
        """Register a tool the agent can use."""
        self.tools[tool.name] = tool
        logger.debug(f"Registered tool '{tool.name}' for agent '{self.name}'")

    def _generate_response(
        self,
        tool_result: Any,
        query: str,
        conversation_history: Optional[List[Dict[str, str]]] = None
    ) -> str:
        """
        Use Deepseek to generate a human-friendly response from tool results.

        Args:
            tool_result: Result from executing a tool
            query: Original user query
            conversation_history: Previous messages in conversation for context

        Returns:
            Human-friendly response text
        """
        # Format tool result for context
        if isinstance(tool_result, dict):
            result_str = json.dumps(tool_result, indent=2)
        else:
            result_str = str(tool_result)

        # Use CLIENT_FACING_SYSTEM_PROMPT to enforce domain boundaries and tone
        system_prompt = CLIENT_FACING_SYSTEM_PROMPT

        # Build messages with conversation history for context
        messages = []

        # Include recent conversation history for context (last 4 messages to stay within limits)
        if conversation_history:
            messages.extend(conversation_history[-4:])

        # Add current query and tool results
        messages.append({
            "role": "user",
            "content": f"User asked: {query}\n\nHere's the relevant information:\n{result_str}\n\nPlease provide a helpful, clear response to the user based on this information. Make sure to highlight any video URLs or resources available."
        })

        response = self.deepseek.generate_response(
            messages=messages,
            system_prompt=system_prompt,
            temperature=0.7,
            max_tokens=500
        )

        return response

    def _normalize_tool_inputs(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """
        Normalize tool input parameter names to match expected signatures.

        Handles common naming variations to make LLM-generated inputs more flexible.
        E.g., "appliance_brand" → "appliance_type", "brand" → "appliance_type"
        """
        # Parameter name mappings (from → to)
        mappings = {
            "appliance_brand": "appliance_type",
            "brand": "appliance_type",
            "appliance": "appliance_type",
            "issue": "symptom",
            "problem": "symptom",
            "part": "part_name",
            "part_type": "part_name",
        }

        normalized = inputs.copy()
        for old_key, new_key in mappings.items():
            if old_key in normalized and new_key not in normalized:
                normalized[new_key] = normalized.pop(old_key)
                logger.debug(f"Normalized parameter: {old_key} → {new_key}")

        return normalized

    def _execute_tool(self, tool_name: str, inputs: Dict[str, Any]) -> str:
        """
        Execute a tool with given inputs.

        Args:
            tool_name: Name of tool to execute
            inputs: Tool parameters

        Returns:
            Tool output as string
        """
        if tool_name not in self.tools:
            return f"ERROR: Tool '{tool_name}' not found"

        tool = self.tools[tool_name]

        try:
            # MVP: Normalize parameter names (handle common variations)
            # E.g., "appliance_brand" → "appliance_type"
            normalized_inputs = self._normalize_tool_inputs(inputs)

            # Validate required parameters
            for param in tool.required_params:
                if param not in normalized_inputs:
                    return f"ERROR: Missing required parameter '{param}'"

            # Execute tool
            result = tool.func(**normalized_inputs)

            # Format result as string
            if isinstance(result, dict):
                return json.dumps(result, indent=2)
            elif isinstance(result, list):
                return json.dumps(result, indent=2)
            else:
                return str(result)

        except Exception as e:
            logger.error(f"Error executing tool '{tool_name}': {e}")
            return f"ERROR executing tool: {str(e)}"

    def execute(
        self,
        tool_name: str,
        tool_inputs: Dict[str, Any],
        query: str,
        conversation_history: Optional[List[Dict[str, str]]] = None
    ) -> Dict[str, Any]:
        """
        Execute a tool and generate response.

        This is the simplified execution path - no reasoning loops, direct tool execution.

        Args:
            tool_name: Name of the tool to execute
            tool_inputs: Parameters for the tool
            query: Original user query (for response generation context)
            conversation_history: Previous conversation messages for context

        Returns:
            Dict with response and metadata
        """
        logger.info(f"Agent {self.name} executing tool: {tool_name}")

        try:
            # Execute the tool
            tool_result = self._execute_tool(tool_name, tool_inputs)

            # Generate human-friendly response from tool result (with conversation context)
            response = self._generate_response(tool_result, query, conversation_history)

            return {
                "response": response,
                "agent": self.name,
                "tool_used": tool_name,
                "tool_result": tool_result,
                "success": True
            }

        except Exception as e:
            logger.error(f"Error executing tool {tool_name}: {e}", exc_info=True)
            return {
                "response": f"I encountered an error while trying to help. Please try again or rephrase your question.",
                "agent": self.name,
                "tool_used": tool_name,
                "success": False,
                "error": str(e)
            }
