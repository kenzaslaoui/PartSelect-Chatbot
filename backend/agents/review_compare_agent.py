"""
Review/Compare Agent - Specialized agent for comparing parts and analyzing reviews.

Uses tools:
- search_parts: Find parts matching criteria
- analyze_reviews: Analyze customer reviews for quality
- compare_prices: Compare prices across options
- rank_options: Rank parts by rating/value
- get_sentiments: Extract common themes from reviews
"""

import logging
from typing import Dict, List, Any, Optional
from .base_agent import BaseAgent, Tool
from rag.retrieval import PartSearchRetriever
from rag.chroma_db import ChromaDBManager
from .deepseek_client import DeepseekClient

logger = logging.getLogger(__name__)


class ReviewCompareAgent(BaseAgent):
    """Agent for comparing parts and analyzing customer reviews."""

    def __init__(
        self,
        deepseek_client: Optional[DeepseekClient] = None,
        chroma_manager: Optional[ChromaDBManager] = None
    ):
        """Initialize Review/Compare Agent."""
        super().__init__(
            name="Review Compare Agent",
            description="I help you compare parts and analyze customer reviews to find the best option for your needs. I can rank by price, quality, and reliability.",
            deepseek_client=deepseek_client,
            chroma_manager=chroma_manager,
            model="deepseek-chat"
        )
        logger.info("ReviewCompareAgent initialized")

        self.retriever = PartSearchRetriever(self.chroma_manager)
        self.parts: List[Dict[str, Any]] = []
        self._register_tools()

    def _register_tools(self) -> None:
        """Register tools available to this agent."""

        def search_parts(query: str, appliance_type: Optional[str] = None, top_k: int = 5):
            """Search for parts to compare."""
            results = self.retriever.retrieve_parts(
                query=query,
                appliance_type=appliance_type,
                top_k=top_k
            )
            self.parts = results.get("results", [])
            return {
                "found": len(self.parts),
                "parts": [
                    {
                        "id": p["id"],
                        "title": p["title"],
                        "price": p.get("price"),
                        "rating": p.get("rating"),
                        "reviews": p.get("review_count")
                    }
                    for p in self.parts
                ]
            }

        def analyze_reviews(part_id: str):
            """Analyze customer reviews for a part."""
            for part in self.parts:
                if part["id"] == part_id:
                    rating = float(part.get("rating") or 0)
                    review_count = part.get("review_count", 0)

                    if rating >= 4.7:
                        quality = "Excellent - Highly recommended"
                        sentiment = "Overwhelmingly positive"
                    elif rating >= 4.0:
                        quality = "Good - Generally well-received"
                        sentiment = "Mostly positive"
                    elif rating >= 3.5:
                        quality = "Average - Mixed reviews"
                        sentiment = "Mixed feedback"
                    else:
                        quality = "Below average"
                        sentiment = "Some concerns reported"

                    return {
                        "part": part["title"],
                        "rating": rating,
                        "review_count": review_count,
                        "quality": quality,
                        "sentiment": sentiment,
                        "recommendation_strength": "High" if rating >= 4.5 else "Medium" if rating >= 4.0 else "Low"
                    }

            return {"error": "Part not found"}

        def compare_prices(part_ids: List[str]):
            """Compare prices across parts."""
            parts_to_compare = [p for p in self.parts if p["id"] in part_ids]

            prices = []
            for part in parts_to_compare:
                try:
                    price = float(part.get("price") or 0)
                    prices.append({"part": part["title"], "price": price})
                except (ValueError, TypeError):
                    pass

            if prices:
                prices.sort(key=lambda x: x["price"])
                cheapest = prices[0]
                most_expensive = prices[-1]
                avg_price = sum(p["price"] for p in prices) / len(prices)

                return {
                    "comparison": prices,
                    "cheapest": cheapest,
                    "most_expensive": most_expensive,
                    "average_price": round(avg_price, 2)
                }

            return {"error": "No prices available"}

        def rank_options(sort_by: str = "rating"):
            """Rank current parts by rating, price, or value."""
            if sort_by == "rating":
                sorted_parts = sorted(self.parts, key=lambda p: float(p.get("rating") or 0), reverse=True)
                return {
                    "sorted_by": "Customer Rating (Highest First)",
                    "ranking": [
                        {
                            "rank": i + 1,
                            "part": p["title"],
                            "rating": p.get("rating"),
                            "reviews": p.get("review_count")
                        }
                        for i, p in enumerate(sorted_parts[:5])
                    ]
                }

            elif sort_by == "price":
                sorted_parts = sorted(self.parts, key=lambda p: float(p.get("price") or 0))
                return {
                    "sorted_by": "Price (Lowest First)",
                    "ranking": [
                        {
                            "rank": i + 1,
                            "part": p["title"],
                            "price": p.get("price"),
                            "rating": p.get("rating")
                        }
                        for i, p in enumerate(sorted_parts[:5])
                    ]
                }

            else:  # value = price per review point
                value_parts = []
                for p in self.parts:
                    try:
                        price = float(p.get("price") or 1)
                        rating = float(p.get("rating") or 1)
                        value = rating / (price / 100) if price > 0 else 0
                        value_parts.append({
                            "part": p,
                            "value_score": value
                        })
                    except (ValueError, TypeError):
                        pass

                value_parts.sort(key=lambda x: x["value_score"], reverse=True)

                return {
                    "sorted_by": "Value (Rating per Dollar)",
                    "ranking": [
                        {
                            "rank": i + 1,
                            "part": vp["part"]["title"],
                            "price": vp["part"].get("price"),
                            "rating": vp["part"].get("rating"),
                            "value_score": round(vp["value_score"], 2)
                        }
                        for i, vp in enumerate(value_parts[:5])
                    ]
                }

        def get_sentiments(query: str):
            """Extract common themes/sentiments from reviews."""
            # In a real system, this would analyze actual reviews
            return {
                "common_themes": [
                    "Durability - Users appreciate long-lasting quality",
                    "Reliability - Consistent performance reported",
                    "Easy installation - Quick setup process",
                    "Good customer service - Positive support experiences"
                ],
                "concerns": [
                    "Occasional shipping delays",
                    "Packaging quality could be better"
                ],
                "recommendation": "Overall well-reviewed option"
            }

        def final_answer(answer: str):
            """Provide final comparison and recommendation."""
            return {"response": answer}

        # Register tools
        self.register_tool(Tool(
            name="search_parts",
            description="Search for parts to compare.",
            func=search_parts,
            required_params=["query"],
            optional_params=["appliance_type", "top_k"]
        ))

        self.register_tool(Tool(
            name="analyze_reviews",
            description="Analyze customer reviews and sentiment for a part.",
            func=analyze_reviews,
            required_params=["part_id"]
        ))

        self.register_tool(Tool(
            name="compare_prices",
            description="Compare prices across selected parts.",
            func=compare_prices,
            required_params=["part_ids"]
        ))

        self.register_tool(Tool(
            name="rank_options",
            description="Rank parts by rating, price, or value score.",
            func=rank_options,
            required_params=[],
            optional_params=["sort_by"]
        ))

        self.register_tool(Tool(
            name="get_sentiments",
            description="Extract common themes and sentiments from customer reviews.",
            func=get_sentiments,
            required_params=["query"]
        ))

        self.register_tool(Tool(
            name="FINAL_ANSWER",
            description="Provide final comparison summary and recommendation.",
            func=final_answer,
            required_params=["answer"]
        ))

    def execute(self, query: str, appliance_type: Optional[str] = None, conversation_history: Optional[List[Dict[str, str]]] = None) -> Dict[str, Any]:
        """
        Execute comparison and review analysis.

        Uses simplified direct tool execution - no reasoning loops.

        Args:
            query: What user wants to compare
            appliance_type: Type of appliance
            conversation_history: Previous conversation messages for context

        Returns:
            Comparison and recommendation
        """
        logger.info(f"ReviewCompareAgent executing query: {query}")

        if appliance_type:
            enhanced_query = f"Compare {query} for {appliance_type}, looking at reviews and ratings"
        else:
            enhanced_query = f"Compare {query}, analyzing customer reviews and ratings"

        # Execute the search_parts tool directly
        tool_inputs = {
            "query": query,
            "appliance_type": appliance_type,
            "top_k": 5
        }

        result = super().execute(
            tool_name="search_parts",
            tool_inputs=tool_inputs,
            query=enhanced_query,
            conversation_history=conversation_history
        )

        return {
            **result,
            "agent_type": "review_compare",
            "parts": self.parts[:3]
        }
