"""
Intent classification and entity extraction for user queries.

This module handles:
- Intent detection (product_search, troubleshooting, installation, etc.)
- Entity extraction (appliance type, brand, part type, model number, etc.)
- Query parsing
"""

import logging
import re
from typing import Dict, List, Any, Optional, Set
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class ExtractedEntities:
    """Extracted entities from user query."""
    appliance_type: Optional[str] = None  # "refrigerator" or "dishwasher"
    brand: Optional[str] = None  # "LG", "Samsung", "GE", etc.
    part_type: Optional[str] = None  # "water dispenser", "spray arm", etc.
    model_number: Optional[str] = None  # "RS25J500DSG", etc.
    issue_keywords: List[str] = None  # ["noise", "leaking", "not cooling"]
    installation_related: bool = False
    comparison_requested: bool = False

    def __post_init__(self):
        if self.issue_keywords is None:
            self.issue_keywords = []


class IntentClassifier:
    """Classify user intent from query."""

    # Intent types
    INTENTS = {
        "product_search": "User looking for specific parts",
        "troubleshooting": "User has appliance issue/problem",
        "installation": "User needs installation guidance",
        "compatibility_check": "User checking if part fits their model",
        "review_comparison": "User comparing parts/reviews",
        "general_help": "General inquiry about parts/products"
    }

    # Keywords for each intent
    INTENT_KEYWORDS = {
        "product_search": [
            "find", "search", "looking for", "need", "want",
            "where can i", "show me", "do you have", "price",
            "cost", "available", "in stock", "buy"
        ],
        "troubleshooting": [
            "problem", "issue", "broken", "not working", "doesn't work",
            "error", "making noise", "leaking", "noisy", "sound",
            "won't", "can't", "help", "fix", "trouble",
            "symptom", "damage", "repair", "fail"
        ],
        "installation": [
            "install", "installation", "how to install", "replace",
            "replacement", "remove", "setup", "fit", "attach",
            "mount", "connection", "tool", "step"
        ],
        "compatibility_check": [
            "compatible", "fit", "work with", "match", "model",
            "will it work", "is it compatible", "does it fit",
            "model number"
        ],
        "review_comparison": [
            "review", "rating", "compare", "better", "best",
            "vs", "versus", "difference", "similar", "recommend",
            "opinion", "experience", "feedback"
        ]
    }

    # Appliance types
    APPLIANCE_KEYWORDS = {
        "refrigerator": ["fridge", "refrigerator", "frig", "ice maker", "freezer"],
        "dishwasher": ["dishwasher", "dish washer", "washing dishes"]
    }

    # Common brands
    BRANDS = {
        "lg": ["lg", "lgé"],
        "samsung": ["samsung"],
        "ge": ["ge", "general electric"],
        "whirlpool": ["whirlpool"],
        "electrolux": ["electrolux"],
        "bosch": ["bosch"],
        "thermador": ["thermador"],
        "kitchenaid": ["kitchenaid"],
        "maytag": ["maytag"],
        "frigidaire": ["frigidaire"]
    }

    # Common part types
    PART_TYPES = {
        "water_dispenser": ["water dispenser", "ice dispenser", "water filter"],
        "spray_arm": ["spray arm", "spray ball", "wash arm"],
        "compressor": ["compressor"],
        "condenser": ["condenser", "condenser fan"],
        "evaporator": ["evaporator", "evaporator fan"],
        "door_handle": ["door handle", "handle"],
        "thermostat": ["thermostat"],
        "motor": ["motor", "fan motor"],
        "seal": ["seal", "gasket"],
        "shelf": ["shelf", "shelf assembly"]
    }

    def classify(self, query: str) -> tuple[Set[str], float]:
        """
        Classify user intent.

        Args:
            query: User query text

        Returns:
            Tuple of (intent_set, confidence_score)
        """
        query_lower = query.lower()
        detected_intents = set()
        intent_scores = {}

        # Score each intent
        for intent, keywords in self.INTENT_KEYWORDS.items():
            matches = sum(1 for kw in keywords if kw in query_lower)
            if matches > 0:
                intent_scores[intent] = matches / len(keywords)
                detected_intents.add(intent)

        # If no specific intent detected, classify as general_help
        if not detected_intents:
            detected_intents.add("general_help")
            confidence = 0.0
        else:
            # Calculate average confidence
            confidence = sum(intent_scores.values()) / len(intent_scores)

        return detected_intents, confidence

    def extract_appliance_type(self, query: str) -> Optional[str]:
        """Extract appliance type from query."""
        query_lower = query.lower()
        for appliance, keywords in self.APPLIANCE_KEYWORDS.items():
            for keyword in keywords:
                if keyword in query_lower:
                    return appliance
        return None

    def extract_brand(self, query: str) -> Optional[str]:
        """Extract brand from query."""
        query_lower = query.lower()
        for brand, keywords in self.BRANDS.items():
            for keyword in keywords:
                if keyword in query_lower:
                    return brand.upper()
        return None

    def extract_part_type(self, query: str) -> Optional[str]:
        """Extract part type from query."""
        query_lower = query.lower()
        for part_type, keywords in self.PART_TYPES.items():
            for keyword in keywords:
                if keyword in query_lower:
                    return part_type
        return None

    def extract_model_number(self, query: str) -> Optional[str]:
        """
        Extract model number from query.
        Model numbers are typically alphanumeric patterns like RS25J500DSG.
        """
        # Pattern: Usually starts with letters, followed by numbers and sometimes letters
        # Examples: RS25J500DSG, WDT780SAEM1, FFBF3054US
        pattern = r'\b[A-Z]{1,2}\d{2,3}[A-Z0-9]{4,8}\b'
        matches = re.findall(pattern, query)
        return matches[0] if matches else None

    def extract_issue_keywords(self, query: str) -> List[str]:
        """Extract problem-related keywords from query."""
        troubleshooting_keywords = [
            "noise", "leaking", "not cooling", "not freezing",
            "ice maker", "water dispenser", "door won't close",
            "grinding", "squealing", "broken", "cracked", "stopped",
            "error", "beeping", "won't drain"
        ]
        query_lower = query.lower()
        found = [kw for kw in troubleshooting_keywords if kw in query_lower]
        return found


class EntityExtractor:
    """Extract entities from user queries."""

    def __init__(self):
        """Initialize entity extractor."""
        self.intent_classifier = IntentClassifier()

    def extract(self, query: str) -> ExtractedEntities:
        """
        Extract all entities from query.

        Args:
            query: User query text

        Returns:
            ExtractedEntities object
        """
        entities = ExtractedEntities()

        # Extract appliance type
        entities.appliance_type = self.intent_classifier.extract_appliance_type(query)

        # Extract brand
        entities.brand = self.intent_classifier.extract_brand(query)

        # Extract part type
        entities.part_type = self.intent_classifier.extract_part_type(query)

        # Extract model number
        entities.model_number = self.intent_classifier.extract_model_number(query)

        # Extract issue keywords
        entities.issue_keywords = self.intent_classifier.extract_issue_keywords(query)

        # Detect if installation-related
        installation_keywords = ["install", "replace", "how to", "setup", "remove"]
        entities.installation_related = any(kw in query.lower() for kw in installation_keywords)

        # Detect if comparison-related
        comparison_keywords = ["compare", "vs", "versus", "better", "best", "difference", "recommend"]
        entities.comparison_requested = any(kw in query.lower() for kw in comparison_keywords)

        return entities

    def extract_followup_context(self, query: str, previous_results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Extract context for follow-up queries.

        Args:
            query: Current query
            previous_results: Results from previous query

        Returns:
            Context dict with relevant information
        """
        context = {
            "referencing_previous": False,
            "reference_type": None,
            "relevant_result_ids": []
        }

        query_lower = query.lower()

        # Check for references to previous results
        reference_keywords = [
            "that one", "this one", "the first", "the second",
            "it", "them", "those", "these", "this part", "that part",
            "compare to", "compared to", "like the", "similar to"
        ]

        if any(kw in query_lower for kw in reference_keywords) and previous_results:
            context["referencing_previous"] = True

            # Determine what type of reference
            if "first" in query_lower:
                context["reference_type"] = "first_result"
                if previous_results:
                    context["relevant_result_ids"] = [previous_results[0].get("id")]
            elif "compare" in query_lower or "vs" in query_lower:
                context["reference_type"] = "comparison"
                context["relevant_result_ids"] = [r.get("id") for r in previous_results[:3]]
            elif "better" in query_lower or "best" in query_lower:
                context["reference_type"] = "ranking"
                context["relevant_result_ids"] = [r.get("id") for r in previous_results]

        return context
