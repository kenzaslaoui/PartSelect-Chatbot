"""
Agent executor for PartSelect chat.

Orchestrates the complete flow:
Orchestrator → EntityExtraction → AgentRouting → Retrieval → Deepseek → Response
"""

import logging
from typing import Dict, List, Any, Optional
from .orchestrator import ConversationOrchestrator, Intent
from .response_generator import ResponseGenerator
from .deepseek_client import DeepseekClient
from rag.chroma_db import ChromaDBManager
from .part_search_agent import PartSearchAgent
from .troubleshooting_agent import TroubleshootingAgent
from .installation_agent import InstallationAgent
from .compatibility_agent import CompatibilityAgent
from .review_compare_agent import ReviewCompareAgent

logger = logging.getLogger(__name__)


class AgentExecutor:
    """Executes agents and generates responses for user queries."""

    def __init__(
        self,
        user_id: Optional[str] = None,
        chroma_manager: Optional[ChromaDBManager] = None,
        deepseek_client: Optional[DeepseekClient] = None
    ):
        """
        Initialize agent executor.

        Args:
            user_id: Optional user ID for conversation tracking
            chroma_manager: ChromaDB manager instance
            deepseek_client: Deepseek LLM client instance
        """
        self.orchestrator = ConversationOrchestrator(user_id=user_id)
        self.response_generator = ResponseGenerator(deepseek_client or DeepseekClient())

        # Initialize ChromaDB if not provided
        self.chroma_manager = chroma_manager or ChromaDBManager()

        # Load collections
        self._load_collections()

        # Initialize agentic agents
        self.part_search_agent = PartSearchAgent(
            deepseek_client=self.response_generator.deepseek,
            chroma_manager=self.chroma_manager
        )
        self.troubleshooting_agent = TroubleshootingAgent(
            deepseek_client=self.response_generator.deepseek,
            chroma_manager=self.chroma_manager
        )
        self.installation_agent = InstallationAgent(
            deepseek_client=self.response_generator.deepseek,
            chroma_manager=self.chroma_manager
        )
        self.compatibility_agent = CompatibilityAgent(
            deepseek_client=self.response_generator.deepseek,
            chroma_manager=self.chroma_manager
        )
        self.review_compare_agent = ReviewCompareAgent(
            deepseek_client=self.response_generator.deepseek,
            chroma_manager=self.chroma_manager
        )

        logger.info(f"AgentExecutor initialized for user: {user_id or 'anonymous'}")

    def _load_collections(self) -> None:
        """Load all ChromaDB collections."""
        collections = ["parts_refrigerator", "parts_dishwasher", "blogs_articles", "repair_symptoms"]
        for collection_name in collections:
            try:
                self.chroma_manager.create_collection(collection_name)
            except Exception as e:
                logger.debug(f"Collection {collection_name} already loaded: {e}")

    def process_user_input(self, user_query: str) -> Dict[str, Any]:
        """
        Process user input and generate response.

        Args:
            user_query: User's input query

        Returns:
            Dict with response and metadata
        """
        logger.info(f"Processing user input: {user_query}")

        # Step 1: Process query through orchestrator
        routing_info = self.orchestrator.process_query(user_query)

        # If out of scope, return direct response
        if not routing_info.get("in_scope"):
            response = self.response_generator.generate_out_of_scope_response(user_query)
            self.orchestrator.add_assistant_response(response, sources=[])

            return {
                "response": response,
                "conversation_id": self.orchestrator.context.conversation_id,
                "in_scope": False,
                "sources": []
            }

        # Step 2: Route to agents and retrieve information
        retrieval_results = self._execute_agents(routing_info)

        # Step 3: Generate response using Deepseek
        primary_intent = Intent(routing_info["primary_intent"])
        response = self._generate_response(primary_intent, user_query, retrieval_results)

        # Step 4: Update conversation history
        self.orchestrator.add_assistant_response(
            response,
            sources=retrieval_results.get("sources", []),
            results_count=retrieval_results.get("results_count", 0)
        )

        # Store results for follow-up queries
        if retrieval_results.get("parts_list"):
            self.orchestrator.set_previous_results(retrieval_results["parts_list"])

        return {
            "response": response,
            "conversation_id": self.orchestrator.context.conversation_id,
            "intent": routing_info["primary_intent"],
            "entities": routing_info["entities"],
            "sources": retrieval_results.get("sources", []),
            "in_scope": True
        }

    def _execute_agents(self, routing_info: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute appropriate agentic agents based on routing info.

        Uses true agents with reasoning loops and tool execution.

        Args:
            routing_info: Routing information from orchestrator

        Returns:
            Dict with agent results
        """
        intent = Intent(routing_info["primary_intent"])
        entities = routing_info["entities"]
        agents = routing_info["selected_agents"]

        results = {
            "sources": agents,
            "agent_responses": [],
            "thinking_history": []
        }

        # Get conversation history for context
        conversation_history = [
            {"role": "user" if msg.role == "user" else "assistant", "content": msg.content}
            for msg in self.orchestrator.context.get_recent_history(5)
        ]

        try:
            # Execute appropriate agent based on routing
            if "PartSearchRetriever" in agents:
                logger.info("Executing PartSearchAgent...")
                agent_result = self.part_search_agent.execute(
                    query=routing_info["query"],
                    appliance_type=entities["appliance_type"],
                    conversation_history=conversation_history
                )
                results["agent_responses"].append(agent_result)
                results["thinking_history"].extend(agent_result.get("thinking_history", []))
                results["part_search"] = agent_result

            elif "TroubleshootingRetriever" in agents:
                logger.info("Executing TroubleshootingAgent...")
                agent_result = self.troubleshooting_agent.execute(
                    query=routing_info["query"],
                    appliance_type=entities["appliance_type"],
                    conversation_history=conversation_history
                )
                results["agent_responses"].append(agent_result)
                results["thinking_history"].extend(agent_result.get("thinking_history", []))
                results["troubleshooting"] = agent_result

            elif "InstallationRetriever" in agents:
                logger.info("Executing InstallationAgent...")
                part_name = entities["part_type"] or routing_info["query"]
                agent_result = self.installation_agent.execute(
                    part_name=part_name,
                    appliance_type=entities["appliance_type"],
                    conversation_history=conversation_history
                )
                results["agent_responses"].append(agent_result)
                results["thinking_history"].extend(agent_result.get("thinking_history", []))
                results["installation"] = agent_result

            elif "CompatibilityRetriever" in agents:
                logger.info("Executing CompatibilityAgent...")
                agent_result = self.compatibility_agent.execute(
                    part_id=entities.get("part_type", ""),
                    model_number=entities.get("model_number", ""),
                    conversation_history=conversation_history
                )
                results["agent_responses"].append(agent_result)
                results["thinking_history"].extend(agent_result.get("thinking_history", []))
                results["compatibility"] = agent_result

            elif "ReviewAnalyzer" in agents:
                logger.info("Executing ReviewCompareAgent...")
                agent_result = self.review_compare_agent.execute(
                    query=routing_info["query"],
                    appliance_type=entities["appliance_type"],
                    conversation_history=conversation_history
                )
                results["agent_responses"].append(agent_result)
                results["thinking_history"].extend(agent_result.get("thinking_history", []))
                results["review_compare"] = agent_result

            # For multi-intent queries, could execute multiple agents
            # This is a simplified version - full implementation would handle all agents

        except Exception as e:
            logger.error(f"Error executing agents: {e}", exc_info=True)
            results["error"] = str(e)

        return results

    def _generate_response(
        self,
        intent: Intent,
        query: str,
        retrieval_results: Dict[str, Any]
    ) -> str:
        """
        Generate response based on agent outputs.

        The agentic agents already generate their own responses via Deepseek,
        so we mostly extract and format them.

        Args:
            intent: Primary user intent
            query: Original user query
            retrieval_results: Results from agentic agent execution

        Returns:
            Generated response text
        """
        try:
            # Extract agent response(s)
            agent_responses = retrieval_results.get("agent_responses", [])

            if agent_responses:
                # If agents already generated responses, use them
                primary_response = agent_responses[0].get("response", "")

                if primary_response:
                    return primary_response

            # Fallback: generate response using ResponseGenerator
            if intent == Intent.PRODUCT_SEARCH:
                return self.response_generator.generate_product_search_response(
                    query,
                    retrieval_results.get("part_search", {})
                )

            elif intent == Intent.COMPATIBILITY_CHECK:
                model_number = self.orchestrator.context.entities.model_number
                return self.response_generator.generate_compatibility_response(
                    model_number or query,
                    retrieval_results.get("compatibility", {})
                )

            elif intent == Intent.TROUBLESHOOTING:
                conversation_history = [
                    {"role": "user" if msg.role == "user" else "assistant", "content": msg.content}
                    for msg in self.orchestrator.context.get_recent_history(5)
                ]
                return self.response_generator.generate_troubleshooting_response(
                    query,
                    retrieval_results.get("troubleshooting", {}),
                    conversation_history
                )

            elif intent == Intent.INSTALLATION:
                part_name = self.orchestrator.context.entities.part_type or query
                return self.response_generator.generate_installation_response(
                    part_name,
                    retrieval_results.get("installation", {})
                )

            elif intent == Intent.REVIEW_COMPARISON:
                # Use ReviewCompareAgent response if available
                return self.response_generator.generate_product_search_response(
                    query,
                    retrieval_results.get("review_compare", {})
                )

            else:  # GENERAL_HELP
                conversation_history = [
                    {"role": "user" if msg.role == "user" else "assistant", "content": msg.content}
                    for msg in self.orchestrator.context.get_recent_history(5)
                ]
                return self.response_generator.generate_general_help_response(
                    query,
                    conversation_history
                )

        except Exception as e:
            logger.error(f"Error generating response: {e}", exc_info=True)
            return "I encountered an error processing your request. Please try again."

    def get_conversation_context(self) -> Dict[str, Any]:
        """Get current conversation context."""
        return self.orchestrator.get_context_summary()

    def new_conversation(self, user_id: Optional[str] = None) -> str:
        """Start a new conversation."""
        return self.orchestrator.create_new_conversation(user_id)

    def check_health(self) -> Dict[str, bool]:
        """Check health of all components."""
        return {
            "chroma_db": self._check_chroma_health(),
            "deepseek": self.response_generator.deepseek.check_api_health(),
            "orchestrator": True,
            "overall": self._check_chroma_health() and self.response_generator.deepseek.check_api_health()
        }

    def _check_chroma_health(self) -> bool:
        """Check ChromaDB health."""
        try:
            stats = self.chroma_manager.get_collection_stats()
            return len(stats) > 0
        except Exception as e:
            logger.error(f"ChromaDB health check failed: {e}")
            return False
