"""
Conversation orchestrator for PartSelect chat agent.

This module handles:
- Conversation context management
- Multi-turn dialogue tracking
- Agent selection and routing
- State persistence
"""

import logging
import uuid
from typing import Dict, List, Any, Optional, Set
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

from .intent_classifier import IntentClassifier, EntityExtractor, ExtractedEntities

logger = logging.getLogger(__name__)


class Intent(str, Enum):
    """User intent types."""
    PRODUCT_SEARCH = "product_search"
    TROUBLESHOOTING = "troubleshooting"
    INSTALLATION = "installation"
    COMPATIBILITY_CHECK = "compatibility_check"
    REVIEW_COMPARISON = "review_comparison"
    GENERAL_HELP = "general_help"


@dataclass
class Message:
    """Single message in conversation."""
    role: str  # "user" or "assistant"
    content: str
    timestamp: datetime = field(default_factory=datetime.now)
    intent: Optional[Intent] = None
    entities: Optional[ExtractedEntities] = None
    sources: List[str] = field(default_factory=list)  # Which collections/agents used
    results_count: int = 0


@dataclass
class ConversationContext:
    """Context for current conversation."""
    conversation_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    user_id: Optional[str] = None
    history: List[Message] = field(default_factory=list)
    current_intent: Optional[Intent] = None
    entities: ExtractedEntities = field(default_factory=ExtractedEntities)
    previous_results: List[Dict[str, Any]] = field(default_factory=list)
    conversation_topic: Optional[str] = None  # "refrigerator", "dishwasher", or None
    context_window: int = 10  # Number of recent messages to consider

    def add_message(
        self,
        role: str,
        content: str,
        intent: Optional[Intent] = None,
        entities: Optional[ExtractedEntities] = None,
        sources: List[str] = None,
        results_count: int = 0
    ) -> None:
        """Add message to conversation history."""
        msg = Message(
            role=role,
            content=content,
            intent=intent,
            entities=entities,
            sources=sources or [],
            results_count=results_count
        )
        self.history.append(msg)

        # Update current intent if this is a user message
        if role == "user" and intent:
            self.current_intent = intent

        # Limit history to context window
        if len(self.history) > self.context_window * 2:
            self.history = self.history[-self.context_window * 2:]

    def get_recent_history(self, n: int = 5) -> List[Message]:
        """Get last n messages from history."""
        return self.history[-n:]

    def get_conversation_summary(self) -> Dict[str, Any]:
        """Get summary of conversation so far."""
        return {
            "conversation_id": self.conversation_id,
            "user_id": self.user_id,
            "message_count": len(self.history),
            "current_intent": self.current_intent.value if self.current_intent else None,
            "conversation_topic": self.conversation_topic,
            "extracted_entities": {
                "appliance_type": self.entities.appliance_type,
                "brand": self.entities.brand,
                "part_type": self.entities.part_type,
                "model_number": self.entities.model_number
            },
            "recent_messages": [
                {
                    "role": msg.role,
                    "content": msg.content[:100] + "..." if len(msg.content) > 100 else msg.content,
                    "intent": msg.intent.value if msg.intent else None
                }
                for msg in self.get_recent_history(3)
            ]
        }


class ConversationOrchestrator:
    """Orchestrates conversation flow and agent selection."""

    # Mapping of intents to required agents
    INTENT_TO_AGENTS = {
        Intent.PRODUCT_SEARCH: ["PartSearchRetriever"],
        Intent.TROUBLESHOOTING: ["TroubleshootingRetriever"],
        Intent.INSTALLATION: ["InstallationRetriever"],
        Intent.COMPATIBILITY_CHECK: ["CompatibilityRetriever"],
        Intent.REVIEW_COMPARISON: ["PartSearchRetriever", "ReviewAnalyzer"],
        Intent.GENERAL_HELP: ["PartSearchRetriever", "TroubleshootingRetriever"]
    }

    # Scope validation (matches scraper keywords in scrapers/config.py)
    VALID_APPLIANCES = {"refrigerator", "dishwasher"}
    VALID_APPLIANCE_KEYWORDS = {
        "refrigerator": [
            "fridge", "refrigerator", "frig",
            "freezer", "icemaker", "ice maker",
            "defrost", "ice dispenser", "water dispenser", "cooling"
        ],
        "dishwasher": [
            "dishwasher", "dish washer",
            "rinse aid", "detergent dispenser", "spray arm", "dish rack"
        ]
    }

    def __init__(self, user_id: Optional[str] = None):
        """Initialize orchestrator."""
        self.intent_classifier = IntentClassifier()
        self.entity_extractor = EntityExtractor()
        self.context = ConversationContext(user_id=user_id)
        self.conversation_history: Dict[str, ConversationContext] = {}

        logger.info(f"Orchestrator initialized for user: {user_id or 'anonymous'}")

    def process_query(self, user_query: str) -> Dict[str, Any]:
        """
        Process user query and determine agent routing.

        Args:
            user_query: User's input query

        Returns:
            Dict with routing info and agent selection
        """
        logger.info(f"Processing query: {user_query[:100]}")

        # Check scope - only refrigerator/dishwasher
        # IMPORTANT: If we've already established a conversation topic (fridge/dishwasher),
        # maintain that scope even if current query doesn't have explicit keywords
        # (e.g., "is there a video..." in context of fridge issue)
        is_explicitly_in_scope = self._is_in_scope(user_query)
        is_conversation_in_scope = self.context.conversation_topic is not None

        if not is_explicitly_in_scope and not is_conversation_in_scope:
            return {
                "in_scope": False,
                "response": "I can only help with questions about refrigerators and dishwashers. Is there anything else I can help you with regarding those appliances?",
                "requires_response": True
            }

        # Classify intent
        intents, confidence = self.intent_classifier.classify(user_query)
        primary_intent = self._select_primary_intent(intents, confidence)

        # Extract entities
        entities = self.entity_extractor.extract(user_query)

        # Update conversation context
        self.context.current_intent = primary_intent
        self.context.entities = entities

        # Infer appliance type if not explicitly stated
        if not self.context.conversation_topic and entities.appliance_type:
            self.context.conversation_topic = entities.appliance_type

        # Extract follow-up context if applicable
        followup_context = self.entity_extractor.extract_followup_context(
            user_query,
            self.context.previous_results
        )

        # Select agents based on intent
        agents = self._select_agents(primary_intent, entities, followup_context)

        # Add to history
        self.context.add_message(
            role="user",
            content=user_query,
            intent=primary_intent,
            entities=entities
        )

        return {
            "in_scope": True,
            "query": user_query,
            "primary_intent": primary_intent.value,
            "confidence": confidence,
            "entities": {
                "appliance_type": entities.appliance_type,
                "brand": entities.brand,
                "part_type": entities.part_type,
                "model_number": entities.model_number,
                "issue_keywords": entities.issue_keywords
            },
            "selected_agents": agents,
            "followup_context": followup_context,
            "is_followup": followup_context.get("referencing_previous", False),
            "conversation_id": self.context.conversation_id,
            "previous_results": self.context.previous_results
        }

    def add_assistant_response(
        self,
        response_text: str,
        sources: List[str],
        results_count: int = 0
    ) -> None:
        """
        Add assistant response to conversation history.

        Args:
            response_text: Assistant's response
            sources: List of sources used (collection names, agents)
            results_count: Number of results returned
        """
        self.context.add_message(
            role="assistant",
            content=response_text,
            sources=sources,
            results_count=results_count
        )

    def set_previous_results(self, results: List[Dict[str, Any]]) -> None:
        """Store results for follow-up queries."""
        self.context.previous_results = results

    def get_context_summary(self) -> Dict[str, Any]:
        """Get conversation context summary."""
        return self.context.get_conversation_summary()

    def _is_in_scope(self, query: str) -> bool:
        """Check if query is about refrigerators or dishwashers."""
        query_lower = query.lower()

        # Check for in-scope appliances FIRST (before out_of_scope check)
        fridge_related = ["fridge", "refrigerator", "ice", "freezer"]
        dishwasher_related = ["dishwasher"]  # Check this before generic "washer"
        fridge_parts = ["ice maker", "water dispenser", "compressor", "condenser", "evaporator"]
        dishwasher_parts = ["spray arm", "wash arm"]

        # If mentions refrigerator/dishwasher or their parts, it's in scope
        if any(kw in query_lower for kw in fridge_related + dishwasher_related + fridge_parts + dishwasher_parts):
            return True

        # Out of scope patterns (only check these if no in-scope terms found)
        out_of_scope = [
            "washing machine", "washer", "dryer", "oven", "stove",
            "microwave", "toaster", "blender", "air conditioner",
            "furnace", "hvac"
        ]

        if any(keyword in query_lower for keyword in out_of_scope):
            return False

        # Default: out of scope if no appliance or known part mentioned
        return False

    def _select_primary_intent(self, intents: Set[str], confidence: float) -> Intent:
        """
        Select single primary intent from detected intents.

        Args:
            intents: Set of detected intents
            confidence: Overall confidence score

        Returns:
            Primary intent
        """
        if not intents:
            return Intent.GENERAL_HELP

        # Priority order for intents
        priority = [
            Intent.TROUBLESHOOTING,
            Intent.PRODUCT_SEARCH,
            Intent.COMPATIBILITY_CHECK,
            Intent.INSTALLATION,
            Intent.REVIEW_COMPARISON,
            Intent.GENERAL_HELP
        ]

        for intent in priority:
            if intent.value in intents:
                return intent

        return Intent.GENERAL_HELP

    def _select_agents(
        self,
        intent: Intent,
        entities: ExtractedEntities,
        followup_context: Dict[str, Any]
    ) -> List[str]:
        """
        Select which agents to use based on intent and entities.

        Args:
            intent: Primary user intent
            entities: Extracted entities
            followup_context: Follow-up context if applicable

        Returns:
            List of agent names to invoke
        """
        agents = set(self.INTENT_TO_AGENTS.get(intent, ["PartSearchRetriever"]))

        # Add specialty agents based on entities
        if entities.comparison_requested:
            agents.add("ReviewAnalyzer")

        if entities.model_number:
            agents.add("CompatibilityRetriever")

        if entities.installation_related:
            agents.add("InstallationRetriever")

        # For follow-up queries, may need multiple agents
        if followup_context.get("referencing_previous"):
            if followup_context.get("reference_type") == "comparison":
                agents.add("ReviewAnalyzer")

        return sorted(list(agents))

    def create_new_conversation(self, user_id: Optional[str] = None) -> str:
        """
        Create new conversation thread.

        Args:
            user_id: User ID for this conversation

        Returns:
            Conversation ID
        """
        conv_id = str(uuid.uuid4())
        self.context = ConversationContext(
            conversation_id=conv_id,
            user_id=user_id
        )
        logger.info(f"Created new conversation: {conv_id}")
        return conv_id

    def load_conversation(self, conversation_id: str) -> bool:
        """
        Load existing conversation (would need persistence layer).

        Args:
            conversation_id: ID of conversation to load

        Returns:
            True if loaded successfully, False otherwise
        """
        if conversation_id in self.conversation_history:
            self.context = self.conversation_history[conversation_id]
            return True
        return False

    def is_valid_appliance_query(self, query: str) -> tuple[bool, Optional[str]]:
        """
        Check if query is valid for supported appliances.

        Args:
            query: User query

        Returns:
            Tuple of (is_valid, detected_appliance_type)
        """
        query_lower = query.lower()

        for appliance, keywords in self.VALID_APPLIANCE_KEYWORDS.items():
            for keyword in keywords:
                if keyword in query_lower:
                    return True, appliance

        return False, None
