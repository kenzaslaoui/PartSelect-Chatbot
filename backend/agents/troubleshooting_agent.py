"""
Troubleshooting Agent - Specialized agent for diagnosing appliance issues.

Uses tools:
- search_repair_guides: Search repair guides by symptom
- search_blogs: Search troubleshooting blogs
- get_video_tutorials: Find video tutorials
- extract_parts: Identify which parts might need replacement
- assess_difficulty: Evaluate repair difficulty level
"""

import logging
from typing import Dict, List, Any, Optional
from .base_agent import BaseAgent, Tool
from .model_selector import get_recommended_model
from rag.retrieval import TroubleshootingRetriever
from rag.chroma_db import ChromaDBManager
from .deepseek_client import DeepseekClient

logger = logging.getLogger(__name__)


class TroubleshootingAgent(BaseAgent):
    """Agent for diagnosing and troubleshooting appliance issues."""

    def __init__(
        self,
        deepseek_client: Optional[DeepseekClient] = None,
        chroma_manager: Optional[ChromaDBManager] = None
    ):
        """Initialize Troubleshooting Agent."""
        super().__init__(
            name="Troubleshooting Agent",
            description="I help you diagnose and fix appliance problems. I can identify symptoms, provide repair guidance, and recommend parts that might need replacement.",
            deepseek_client=deepseek_client,
            chroma_manager=chroma_manager,
            model="deepseek-chat"
        )
        logger.info("TroubleshootingAgent initialized")

        # Initialize retriever
        self.retriever = TroubleshootingRetriever(self.chroma_manager)
        self.guides: List[Dict[str, Any]] = []

        # Register tools
        self._register_tools()

    def _register_tools(self) -> None:
        """Register tools available to this agent."""

        def search_repair_guides(symptom: str, appliance_type: Optional[str] = None, difficulty: Optional[str] = None):
            """Search repair guides by symptom. Parameters: symptom (required), appliance_type (optional), difficulty (optional)."""
            results = self.retriever.retrieve_troubleshooting_guides(
                issue_description=symptom,
                appliance_type=appliance_type,
                difficulty=difficulty,
                include_videos=True,
                top_k=5
            )
            self.guides = results.get("results", [])
            return {
                "found": len(self.guides),
                "guides": [
                    {
                        "id": g["id"],
                        "symptom": g.get("symptom") or g.get("title"),
                        "difficulty": g.get("difficulty", "Unknown"),
                        "has_video": g.get("has_video", False),
                        "source": g.get("source")
                    }
                    for g in self.guides[:5]
                ]
            }

        def search_blogs(symptom: str, appliance_type: Optional[str] = None):
            """Search troubleshooting blog articles."""
            results = self.retriever.retrieve_troubleshooting_guides(
                issue_description=symptom,
                appliance_type=appliance_type,
                top_k=3
            )
            # Filter for blog articles
            blog_guides = [g for g in results.get("results", []) if g.get("source") == "blog_article"]
            return {
                "found": len(blog_guides),
                "articles": [
                    {
                        "title": g.get("title"),
                        "url": g.get("url"),
                        "appliance": g.get("appliance_type")
                    }
                    for g in blog_guides[:3]
                ]
            }

        def get_video_tutorials(symptom: str):
            """Find video tutorials for the issue."""
            videos = [g for g in self.guides if g.get("has_video")]
            return {
                "video_count": len(videos),
                "videos": [
                    {
                        "title": g.get("guide_title") or g.get("symptom"),
                        "url": g.get("video_url"),
                        "part": g.get("part_name")
                    }
                    for g in videos[:3]
                ]
            }

        def extract_parts(symptom: str):
            """Identify which parts might need replacement for this symptom."""
            parts = list(set([g.get("part_name") for g in self.guides if g.get("part_name")]))
            return {
                "potential_parts": parts[:5],
                "description": "These parts are commonly involved in this type of issue. You may need to replace one or more of them."
            }

        def assess_difficulty(symptom: str):
            """Assess difficulty level of repair."""
            if not self.guides:
                return {"difficulty": "Unknown"}

            difficulties = [g.get("difficulty", "MEDIUM").upper() for g in self.guides]
            easy_count = difficulties.count("EASY")
            hard_count = difficulties.count("HARD")

            if easy_count >= len(difficulties) / 2:
                level = "EASY"
                description = "This is a straightforward repair that most people can do themselves."
            elif hard_count >= len(difficulties) / 2:
                level = "HARD"
                description = "This is a complex repair. You may want to contact a professional."
            else:
                level = "MEDIUM"
                description = "This is a moderate difficulty repair. Some technical skills helpful."

            return {
                "difficulty_level": level,
                "description": description,
                "professional_recommended": level == "HARD"
            }

        def final_answer(answer: str):
            """Provide final troubleshooting guidance."""
            return {"response": answer}

        # Register tools
        self.register_tool(Tool(
            name="search_repair_guides",
            description="Search for repair guides matching the symptom/issue.",
            func=search_repair_guides,
            required_params=["symptom"],
            optional_params=["appliance_type", "difficulty"]
        ))

        self.register_tool(Tool(
            name="search_blogs",
            description="Search troubleshooting blog articles with detailed explanations.",
            func=search_blogs,
            required_params=["symptom"],
            optional_params=["appliance_type"]
        ))

        self.register_tool(Tool(
            name="get_video_tutorials",
            description="Find video tutorials showing how to fix this issue.",
            func=get_video_tutorials,
            required_params=["symptom"]
        ))

        self.register_tool(Tool(
            name="extract_parts",
            description="Identify which parts are commonly replaced for this symptom.",
            func=extract_parts,
            required_params=["symptom"]
        ))

        self.register_tool(Tool(
            name="assess_difficulty",
            description="Assess the difficulty level of this repair (EASY/MEDIUM/HARD).",
            func=assess_difficulty,
            required_params=["symptom"]
        ))

        self.register_tool(Tool(
            name="FINAL_ANSWER",
            description="Provide final troubleshooting guidance and recommendations.",
            func=final_answer,
            required_params=["answer"]
        ))

    def execute(self, query: str, appliance_type: Optional[str] = None, conversation_history: Optional[List[Dict[str, str]]] = None) -> Dict[str, Any]:
        """
        Execute agent on a troubleshooting query.

        Uses simplified direct tool execution - no reasoning loops.

        Args:
            query: User's issue/symptom description
            appliance_type: Type of appliance ("refrigerator" or "dishwasher")
            conversation_history: Previous conversation messages for context

        Returns:
            Dict with diagnostic response and tool results
        """
        logger.info(f"TroubleshootingAgent executing query: {query}")

        # Determine tool inputs based on query
        tool_inputs = {
            "symptom": query,
            "appliance_type": appliance_type
        }

        # Execute the search_repair_guides tool directly
        result = super().execute(
            tool_name="search_repair_guides",
            tool_inputs=tool_inputs,
            query=query,
            conversation_history=conversation_history
        )

        return {
            **result,
            "agent_type": "troubleshooting",
            "guides": self.guides[:3]
        }
