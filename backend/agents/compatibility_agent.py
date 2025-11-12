"""
Compatibility Agent - Specialized agent for checking part compatibility.

Uses tools:
- lookup_model_info: Get information about appliance model
- search_compatible_parts: Find parts compatible with model
- verify_fit: Verify a part is compatible with a model
- check_alternatives: Find alternative compatible parts
"""

import logging
from typing import Dict, List, Any, Optional
from .base_agent import BaseAgent, Tool
from rag.retrieval import CompatibilityRetriever
from rag.chroma_db import ChromaDBManager
from .deepseek_client import DeepseekClient

logger = logging.getLogger(__name__)


class CompatibilityAgent(BaseAgent):
    """Agent for checking part-to-model compatibility."""

    def __init__(
        self,
        deepseek_client: Optional[DeepseekClient] = None,
        chroma_manager: Optional[ChromaDBManager] = None
    ):
        """Initialize Compatibility Agent."""
        super().__init__(
            name="Compatibility Agent",
            description="I verify that parts are compatible with your specific appliance model. I can lookup model information and find parts that fit your exact model.",
            deepseek_client=deepseek_client,
            chroma_manager=chroma_manager,
            model="deepseek-chat"
        )
        logger.info("CompatibilityAgent initialized")

        self.retriever = CompatibilityRetriever(self.chroma_manager)
        self.compatible_parts: List[Dict[str, Any]] = []
        self._register_tools()

    def _register_tools(self) -> None:
        """Register tools available to this agent."""

        def lookup_model_info(model_number: str):
            """Look up information about an appliance model."""
            # This would query a model database - for now return structure
            return {
                "model": model_number,
                "found": True,
                "message": f"Model {model_number} found in our database"
            }

        def search_compatible_parts(model_number: str, part_type: Optional[str] = None):
            """Search for parts compatible with a specific model."""
            results = self.retriever.retrieve_compatible_parts(
                model_number=model_number,
                part_type=part_type,
                top_k=5
            )
            self.compatible_parts = results.get("results", [])
            return {
                "model": model_number,
                "compatible_count": len(self.compatible_parts),
                "parts": [
                    {
                        "id": p["id"],
                        "title": p["title"],
                        "part_type": p.get("part_type"),
                        "price": p.get("price"),
                        "stock": p.get("stock_status")
                    }
                    for p in self.compatible_parts[:5]
                ]
            }

        def verify_fit(part_id: str, model_number: str):
            """Verify if a specific part fits a specific model."""
            for part in self.compatible_parts:
                if part["id"] == part_id:
                    return {
                        "compatible": True,
                        "part": part.get("title"),
                        "model": model_number,
                        "confirmation": f"✓ This part is confirmed compatible with {model_number}",
                        "stock": part.get("stock_status")
                    }

            return {
                "compatible": False,
                "error": "Part not found in compatibility database",
                "suggestion": "Please double-check the part number"
            }

        def check_alternatives(model_number: str, part_type: str):
            """Find alternative compatible parts of same type."""
            results = self.retriever.retrieve_compatible_parts(
                model_number=model_number,
                part_type=part_type,
                top_k=8
            )
            parts = results.get("results", [])
            return {
                "model": model_number,
                "alternatives": len(parts),
                "parts": [
                    {
                        "title": p.get("title"),
                        "price": p.get("price"),
                        "stock": p.get("stock_status")
                    }
                    for p in parts[:5]
                ]
            }

        def final_answer(answer: str):
            """Provide final compatibility response."""
            return {"response": answer}

        # Register tools
        self.register_tool(Tool(
            name="lookup_model_info",
            description="Look up information about an appliance model.",
            func=lookup_model_info,
            required_params=["model_number"]
        ))

        self.register_tool(Tool(
            name="search_compatible_parts",
            description="Find parts that are compatible with a specific model.",
            func=search_compatible_parts,
            required_params=["model_number"],
            optional_params=["part_type"]
        ))

        self.register_tool(Tool(
            name="verify_fit",
            description="Verify that a specific part is compatible with a model.",
            func=verify_fit,
            required_params=["part_id", "model_number"]
        ))

        self.register_tool(Tool(
            name="check_alternatives",
            description="Find alternative compatible parts of the same type.",
            func=check_alternatives,
            required_params=["model_number", "part_type"]
        ))

        self.register_tool(Tool(
            name="FINAL_ANSWER",
            description="Provide final compatibility confirmation.",
            func=final_answer,
            required_params=["answer"]
        ))

    def execute(self, part_id: str, model_number: str, conversation_history: Optional[List[Dict[str, str]]] = None) -> Dict[str, Any]:
        """
        Execute compatibility check.

        Uses simplified direct tool execution - no reasoning loops.

        Args:
            part_id: ID of part to check
            model_number: Appliance model number
            conversation_history: Previous conversation messages for context

        Returns:
            Compatibility check result
        """
        logger.info(f"CompatibilityAgent checking part {part_id} with model {model_number}")

        query = f"Is part {part_id} compatible with model {model_number}?"

        # Execute the search_compatible_parts tool directly
        tool_inputs = {
            "model_number": model_number,
            "part_type": part_id
        }

        result = super().execute(
            tool_name="search_compatible_parts",
            tool_inputs=tool_inputs,
            query=query,
            conversation_history=conversation_history
        )

        return {
            **result,
            "agent_type": "compatibility",
            "part_id": part_id,
            "model_number": model_number
        }
