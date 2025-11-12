"""
Part Search Agent - Specialized agent for finding and recommending parts.

Uses tools:
- vector_search_parts: Search parts by query
- filter_by_price: Filter results by price range
- check_stock: Check stock availability
- get_reviews: Retrieve customer reviews
- compare_parts: Compare multiple parts
"""

import logging
from typing import Dict, List, Any, Optional
from .base_agent import BaseAgent, Tool
from .model_selector import get_recommended_model
from rag.retrieval import PartSearchRetriever
from rag.chroma_db import ChromaDBManager
from .deepseek_client import DeepseekClient

logger = logging.getLogger(__name__)


class PartSearchAgent(BaseAgent):
    """Agent for searching and recommending appliance parts."""

    def __init__(
        self,
        deepseek_client: Optional[DeepseekClient] = None,
        chroma_manager: Optional[ChromaDBManager] = None
    ):
        """Initialize Part Search Agent."""
        super().__init__(
            name="Part Search Agent",
            description="I help you find and recommend the best parts for your appliances. I can search by specifications, filter by price/brand, check stock status, and compare options.",
            deepseek_client=deepseek_client,
            chroma_manager=chroma_manager,
            model="deepseek-chat"
        )
        logger.info("PartSearchAgent initialized")

        # Initialize retriever
        self.retriever = PartSearchRetriever(self.chroma_manager)
        self.search_results: List[Dict[str, Any]] = []

        # Register tools
        self._register_tools()

    def _register_tools(self) -> None:
        """Register tools available to this agent."""

        def vector_search_parts(query: str, appliance_type: Optional[str] = None, top_k: int = 5):
            """Search parts by natural language query."""
            results = self.retriever.retrieve_parts(
                query=query,
                appliance_type=appliance_type,
                top_k=top_k
            )
            self.search_results = results.get("results", [])
            return {
                "found": len(self.search_results),
                "parts": [
                    {
                        "id": p["id"],
                        "title": p["title"],
                        "price": p["price"],
                        "rating": p["rating"],
                        "stock": p["stock_status"],
                        "relevance": p["relevance_score"]
                    }
                    for p in self.search_results[:5]
                ]
            }

        def filter_by_price(min_price: Optional[float] = None, max_price: Optional[float] = None):
            """Filter current results by price range."""
            filtered = self.search_results
            if min_price:
                filtered = [p for p in filtered if float(p.get("price", 0) or 0) >= min_price]
            if max_price:
                filtered = [p for p in filtered if float(p.get("price", float("inf")) or 0) <= max_price]

            return {
                "filtered_count": len(filtered),
                "parts": [
                    {
                        "title": p["title"],
                        "price": p["price"],
                        "rating": p["rating"]
                    }
                    for p in filtered[:5]
                ]
            }

        def check_stock(part_id: str):
            """Check stock status for a specific part."""
            for part in self.search_results:
                if part["id"] == part_id:
                    return {
                        "part": part["title"],
                        "stock_status": part["stock_status"],
                        "availability": "Available" if part["stock_status"] == "In Stock" else "Out of Stock"
                    }
            return {"error": "Part not found in current results"}

        def get_reviews(part_id: str):
            """Get customer reviews for a part."""
            for part in self.search_results:
                if part["id"] == part_id:
                    return {
                        "part": part["title"],
                        "rating": part["rating"],
                        "review_count": part["review_count"],
                        "quality": "Excellent" if float(part.get("rating") or 0) >= 4.5 else "Good" if float(part.get("rating") or 0) >= 4.0 else "Average"
                    }
            return {"error": "Part not found"}

        def compare_parts(part_ids: List[str]):
            """Compare multiple parts side-by-side."""
            parts_to_compare = [p for p in self.search_results if p["id"] in part_ids]
            return {
                "comparison": [
                    {
                        "title": p["title"],
                        "price": p["price"],
                        "rating": p["rating"],
                        "reviews": p["review_count"],
                        "stock": p["stock_status"]
                    }
                    for p in parts_to_compare
                ]
            }

        def final_answer(answer: str):
            """Provide final answer to user."""
            return {"response": answer}

        # Register all tools
        self.register_tool(Tool(
            name="vector_search_parts",
            description="Search for parts using natural language. Use this first to find relevant parts.",
            func=vector_search_parts,
            required_params=["query"],
            optional_params=["appliance_type", "top_k"]
        ))

        self.register_tool(Tool(
            name="filter_by_price",
            description="Filter current search results by price range.",
            func=filter_by_price,
            required_params=[],
            optional_params=["min_price", "max_price"]
        ))

        self.register_tool(Tool(
            name="check_stock",
            description="Check if a specific part is in stock.",
            func=check_stock,
            required_params=["part_id"]
        ))

        self.register_tool(Tool(
            name="get_reviews",
            description="Get customer reviews and ratings for a part.",
            func=get_reviews,
            required_params=["part_id"]
        ))

        self.register_tool(Tool(
            name="compare_parts",
            description="Compare multiple parts side-by-side.",
            func=compare_parts,
            required_params=["part_ids"]
        ))

        self.register_tool(Tool(
            name="FINAL_ANSWER",
            description="Provide the final answer to the user based on search and analysis.",
            func=final_answer,
            required_params=["answer"]
        ))

    def execute(self, query: str, appliance_type: Optional[str] = None, conversation_history: Optional[List[Dict[str, str]]] = None) -> Dict[str, Any]:
        """
        Execute agent on a part search query.

        Uses simplified direct tool execution - no reasoning loops.

        Args:
            query: User's search query
            appliance_type: "refrigerator" or "dishwasher" (optional)
            conversation_history: Previous conversation messages for context

        Returns:
            Dict with response and tool results
        """
        logger.info(f"PartSearchAgent executing query: {query}")

        # Determine tool inputs based on query
        tool_inputs = {
            "query": query,
            "appliance_type": appliance_type,
            "top_k": 5
        }

        # Execute the vector_search_parts tool directly
        result = super().execute(
            tool_name="vector_search_parts",
            tool_inputs=tool_inputs,
            query=query,
            conversation_history=conversation_history
        )

        return {
            **result,
            "agent_type": "part_search",
            "search_results": self.search_results[:5]  # Include top results
        }
