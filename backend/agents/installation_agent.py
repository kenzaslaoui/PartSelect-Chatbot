"""
Installation Agent - Specialized agent for providing installation guidance.

Uses tools:
- search_installation_guides: Find installation guides for a part
- get_difficulty_level: Get difficulty assessment
- get_tools_needed: List required tools
- get_time_estimate: Get estimated installation time
- get_video_guide: Find video installation guides
"""

import logging
from typing import Dict, List, Any, Optional
from .base_agent import BaseAgent, Tool
from rag.retrieval import InstallationRetriever
from rag.chroma_db import ChromaDBManager
from .deepseek_client import DeepseekClient

logger = logging.getLogger(__name__)


class InstallationAgent(BaseAgent):
    """Agent for providing step-by-step installation guidance."""

    def __init__(
        self,
        deepseek_client: Optional[DeepseekClient] = None,
        chroma_manager: Optional[ChromaDBManager] = None
    ):
        """Initialize Installation Agent."""
        super().__init__(
            name="Installation Agent",
            description="I provide step-by-step installation guidance for appliance parts. I can estimate time, list required tools, and provide difficulty levels.",
            deepseek_client=deepseek_client,
            chroma_manager=chroma_manager,
            model="deepseek-chat"
        )
        logger.info("InstallationAgent initialized")

        self.retriever = InstallationRetriever(self.chroma_manager)
        self.guides: List[Dict[str, Any]] = []
        self._register_tools()

    def _register_tools(self) -> None:
        """Register tools available to this agent."""

        def search_installation_guides(part_name: str, appliance_type: Optional[str] = None):
            """Search for installation guides for a part."""
            results = self.retriever.retrieve_installation_guides(
                part_name=part_name,
                appliance_type=appliance_type,
                top_k=5
            )
            self.guides = results.get("results", [])
            return {
                "found": len(self.guides),
                "guides": [
                    {
                        "id": g["id"],
                        "title": g.get("guide_title") or g.get("title"),
                        "difficulty": g.get("difficulty"),
                        "has_video": g.get("has_video")
                    }
                    for g in self.guides[:3]
                ]
            }

        def get_difficulty_level(part_name: str):
            """Get difficulty level for installing this part."""
            if not self.guides:
                return {"difficulty": "Unknown"}

            difficulties = [g.get("difficulty", "MEDIUM") for g in self.guides]

            easy_count = sum(1 for d in difficulties if d.upper() == "EASY")
            if easy_count >= len(difficulties) / 2:
                level = "EASY"
                description = "Straightforward installation, no special skills required."
            elif any(d.upper() == "HARD" for d in difficulties):
                level = "HARD"
                description = "Complex installation, professional recommended."
            else:
                level = "MEDIUM"
                description = "Moderate difficulty, some technical skill needed."

            return {
                "difficulty": level,
                "description": description,
                "recommendation": "Professional" if level == "HARD" else "DIY" if level == "EASY" else "DIY with guidance"
            }

        def get_tools_needed(part_name: str):
            """Get list of tools needed for installation."""
            # In a real system, this would extract from guides
            common_tools = ["Screwdriver (Phillips)", "Screwdriver (Flathead)", "Wrench", "Pliers"]
            return {
                "tools": common_tools,
                "note": "Check the installation guide for any specialized tools needed"
            }

        def get_time_estimate(part_name: str):
            """Get estimated installation time."""
            if not self.guides:
                return {"estimate": "Unknown"}

            times = [g.get("installation_time") for g in self.guides if g.get("installation_time")]

            if times:
                return {
                    "time_estimates": list(set(times)),
                    "average": "30-60 minutes for most installations"
                }
            return {"estimate": "30-60 minutes"}

        def get_video_guide(part_name: str):
            """Find video installation guides."""
            videos = [g for g in self.guides if g.get("has_video")]
            return {
                "videos_found": len(videos),
                "videos": [
                    {
                        "title": g.get("guide_title") or g.get("title"),
                        "url": g.get("video_url"),
                        "part": g.get("part_name")
                    }
                    for g in videos[:2]
                ]
            }

        def final_answer(answer: str):
            """Provide final installation guidance."""
            return {"response": answer}

        # Register tools
        self.register_tool(Tool(
            name="search_installation_guides",
            description="Search for installation guides for a part.",
            func=search_installation_guides,
            required_params=["part_name"],
            optional_params=["appliance_type"]
        ))

        self.register_tool(Tool(
            name="get_difficulty_level",
            description="Get difficulty assessment for installation.",
            func=get_difficulty_level,
            required_params=["part_name"]
        ))

        self.register_tool(Tool(
            name="get_tools_needed",
            description="Get list of tools required for installation.",
            func=get_tools_needed,
            required_params=["part_name"]
        ))

        self.register_tool(Tool(
            name="get_time_estimate",
            description="Get estimated installation time.",
            func=get_time_estimate,
            required_params=["part_name"]
        ))

        self.register_tool(Tool(
            name="get_video_guide",
            description="Find video installation tutorials.",
            func=get_video_guide,
            required_params=["part_name"]
        ))

        self.register_tool(Tool(
            name="FINAL_ANSWER",
            description="Provide final installation guidance.",
            func=final_answer,
            required_params=["answer"]
        ))

    def execute(self, part_name: str, appliance_type: Optional[str] = None, conversation_history: Optional[List[Dict[str, str]]] = None) -> Dict[str, Any]:
        """
        Execute installation guidance.

        Uses simplified direct tool execution - no reasoning loops.

        Args:
            part_name: Name of part to install
            appliance_type: Type of appliance
            conversation_history: Previous conversation messages for context

        Returns:
            Installation guidance
        """
        logger.info(f"InstallationAgent executing for part: {part_name}")

        query = f"How do I install a {part_name}" + (f" for my {appliance_type}" if appliance_type else "") + "?"

        # Execute the search_installation_guides tool directly
        tool_inputs = {
            "part_name": part_name,
            "appliance_type": appliance_type
        }

        result = super().execute(
            tool_name="search_installation_guides",
            tool_inputs=tool_inputs,
            query=query,
            conversation_history=conversation_history
        )

        return {
            **result,
            "agent_type": "installation",
            "part_name": part_name
        }
