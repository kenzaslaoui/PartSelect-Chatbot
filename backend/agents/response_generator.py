"""
Response generator for PartSelect chat agent.

Combines orchestrator routing + retrieval results + Deepseek LLM
to generate natural language responses.

Uses centralized system prompts from prompts.py to ensure consistency
and align with brand voice and domain boundaries.
"""

import logging
from typing import Dict, List, Any, Optional
from .deepseek_client import DeepseekClient
from .orchestrator import ConversationOrchestrator, Intent
from .prompts import (
    CLIENT_FACING_SYSTEM_PROMPT,
    get_product_search_system_prompt,
    get_troubleshooting_system_prompt,
    get_installation_system_prompt,
    get_compatibility_system_prompt,
    OUT_OF_SCOPE_RESPONSE,
    NO_RESULTS_RESPONSE_TEMPLATE,
    ERROR_RESPONSE
)

logger = logging.getLogger(__name__)


class ResponseGenerator:
    """Generates responses using Deepseek LLM based on retrieval results."""

    def __init__(self, deepseek_client: Optional[DeepseekClient] = None):
        """
        Initialize response generator.

        Args:
            deepseek_client: Optional DeepseekClient instance
        """
        self.deepseek = deepseek_client or DeepseekClient()
        logger.info("ResponseGenerator initialized")

    def generate_product_search_response(
        self,
        query: str,
        results: Dict[str, Any],
        user_context: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Generate response for product search results.

        Args:
            query: Original user query
            results: Results from PartSearchRetriever
            user_context: Additional user context (brand preference, budget, etc.)

        Returns:
            Natural language response
        """
        parts = results.get("results", [])

        if not parts:
            return (
                f"I couldn't find any {results.get('filters', {}).get('appliance_type', 'appliance')} "
                f"parts matching your search for '{query}'. "
                "Could you provide more details about what you're looking for?"
            )

        # Build parts summary for LLM
        parts_info = "\n".join(
            [
                f"{i+1}. {p.get('title', 'Unknown')} "
                f"(${p.get('price', 'N/A')}, "
                f"Rating: {p.get('rating', 'N/A')}/5 from {p.get('review_count', 0)} reviews, "
                f"Stock: {p.get('stock_status', 'unknown')})"
                for i, p in enumerate(parts[:3])
            ]
        )

        context = f"""User is searching for: {query}
Filters applied: {results.get('filters')}
Found {results.get('total_results')} total results.

Top results:
{parts_info}"""

        recommendation = self.deepseek.extract_recommendations(parts, context)

        return f"Based on your search for '{query}':\n\n{recommendation}"

    def generate_troubleshooting_response(
        self,
        issue: str,
        results: Dict[str, Any],
        conversation_history: Optional[List[Dict[str, str]]] = None
    ) -> str:
        """
        Generate response for troubleshooting queries.

        Args:
            issue: User's issue description
            results: Results from TroubleshootingRetriever
            conversation_history: Previous conversation messages

        Returns:
            Natural language response with troubleshooting steps
        """
        guides = results.get("results", [])

        if not guides:
            return (
                f"I don't have specific guides for '{issue}'. "
                "Could you describe your problem in more detail? "
                "For example, what sounds, leaks, or performance issues are you experiencing?"
            )

        response = self.deepseek.generate_troubleshooting_response(
            issue,
            guides,
            conversation_history
        )

        # Add video links if available
        video_guides = [g for g in guides if g.get("has_video")]
        if video_guides:
            response += "\n\nVideo Tutorials Available:"
            for guide in video_guides[:3]:
                if guide.get("video_url"):
                    response += f"\n- {guide.get('guide_title', 'Video Guide')}: {guide.get('video_url')}"

        return response

    def generate_installation_response(
        self,
        part_name: str,
        results: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Generate response for installation queries.

        Args:
            part_name: Name of part to install
            results: Results from InstallationRetriever
            context: Additional context (time, difficulty, etc.)

        Returns:
            Natural language installation guidance
        """
        guides = results.get("results", [])

        if not guides:
            return (
                f"I don't have specific installation guides for '{part_name}'. "
                "For installation help, please contact PartSelect support or consult your appliance manual."
            )

        response = self.deepseek.generate_installation_response(
            part_name,
            guides,
            context
        )

        # Add resource links
        resource_links = [g for g in guides if g.get("url")]
        if resource_links:
            response += "\n\nAdditional Resources:"
            for guide in resource_links[:3]:
                response += f"\n- {guide.get('guide_title', guide.get('title', 'Guide'))}: {guide.get('url')}"

        return response

    def generate_compatibility_response(
        self,
        model_number: str,
        results: Dict[str, Any]
    ) -> str:
        """
        Generate response for compatibility queries.

        Args:
            model_number: Model number being checked
            results: Results from CompatibilityRetriever

        Returns:
            Compatibility information response
        """
        parts = results.get("results", [])

        if not parts:
            return (
                f"I couldn't find compatible parts for model {model_number}. "
                "Please verify the model number and try again, or contact PartSelect support."
            )

        parts_list = "\n".join(
            [f"- {p.get('title', 'Unknown')} (${p.get('price', 'N/A')})" for p in parts[:5]]
        )

        return (
            f"I found {results.get('total_results')} parts compatible with model {model_number}:\n\n"
            f"{parts_list}\n\n"
            f"All these parts are confirmed compatible with your {model_number} appliance. "
            f"Stock status and detailed specifications are available in the product pages."
        )

    def generate_general_help_response(
        self,
        query: str,
        conversation_history: Optional[List[Dict[str, str]]] = None
    ) -> str:
        """
        Generate response for general help queries.

        Args:
            query: User's general question
            conversation_history: Previous conversation messages

        Returns:
            Helpful response with client-facing system prompt
        """
        messages = conversation_history or []
        messages.append({"role": "user", "content": query})

        try:
            response = self.deepseek.generate_response(
                messages,
                system_prompt=CLIENT_FACING_SYSTEM_PROMPT,
                temperature=0.7,
                max_tokens=400
            )
            return response
        except Exception as e:
            logger.error(f"Error generating general help response: {e}")
            return ERROR_RESPONSE

    def generate_out_of_scope_response(
        self,
        query: str
    ) -> str:
        """
        Generate response for out-of-scope queries.

        Args:
            query: User's out-of-scope query

        Returns:
            Polite out-of-scope response from centralized prompts
        """
        return OUT_OF_SCOPE_RESPONSE

    def format_with_context(
        self,
        response: str,
        source_info: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Format response with metadata and source information.

        Args:
            response: Generated response text
            source_info: Information about sources used

        Returns:
            Formatted response dict
        """
        return {
            "response": response,
            "sources": source_info.get("sources", []) if source_info else [],
            "results_count": source_info.get("results_count", 0) if source_info else 0,
            "confidence": source_info.get("confidence", 1.0) if source_info else 1.0
        }
