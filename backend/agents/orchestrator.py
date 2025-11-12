from agents.classifier import IntentClassifier
from agents.product_agent import ProductAgent
from agents.compatibility_agent import CompatibilityAgent
from agents.troubleshooting_agent import TroubleshootingAgent
from agents.installation_agent import InstallationAgent
from utils.deepseek import deepseek_chat
import uuid

class Orchestrator:
    """Main coordinator that routes messages to appropriate agents."""

    def __init__(self):
        self.classifier = IntentClassifier()
        self.product_agent = ProductAgent()
        self.compatibility_agent = CompatibilityAgent()
        self.troubleshooting_agent = TroubleshootingAgent()
        self.installation_agent = InstallationAgent()

        # Store conversation history
        self.conversations = {}

    async def process_message(self, message: str, conversation_id: str | None = None) -> dict:
        """Process user message and route to appropriate agent."""

        # Create or retrieve conversation
        if not conversation_id:
            conversation_id = str(uuid.uuid4())
            self.conversations[conversation_id] = []

        conversation_history = self.conversations.get(conversation_id, [])

        # Classify intent
        intent = await self.classifier.classify(message)

        # Route to appropriate agent
        result = await self._route_to_agent(intent, message, conversation_history)

        # Update conversation history
        conversation_history.append({"role": "user", "content": message})
        conversation_history.append({"role": "assistant", "content": result["response"]})
        self.conversations[conversation_id] = conversation_history

        # Add conversation_id and intent to result
        result["conversation_id"] = conversation_id
        result["intent"] = intent

        return result

    async def _route_to_agent(self, intent: str, message: str, history: list) -> dict:
        """Route message to the appropriate specialized agent."""

        if intent == "product_search":
            return await self.product_agent.search_products(message)

        elif intent == "compatibility_check":
            # Extract part/model numbers from message (simplified)
            # In production, use NER or more sophisticated extraction
            return await self.compatibility_agent.find_compatible_parts(message)

        elif intent == "troubleshooting":
            if history:
                return await self.troubleshooting_agent.guided_troubleshooting(
                    history + [{"role": "user", "content": message}]
                )
            else:
                return await self.troubleshooting_agent.diagnose_issue(message)

        elif intent == "installation_guide":
            # Extract part number (simplified)
            return await self.installation_agent.get_installation_guide(message)

        else:  # general_question
            return await self._handle_general_question(message, history)

    async def _handle_general_question(self, message: str, history: list) -> dict:
        """Handle general questions using base LLM."""

        system_prompt = """You are a helpful appliance parts and repair assistant.
        Answer general questions about appliances, parts, and repairs.
        Be friendly and informative."""

        messages = [{"role": "system", "content": system_prompt}]

        # Add conversation history
        for msg in history[-6:]:  # Last 3 exchanges
            messages.append(msg)

        messages.append({"role": "user", "content": message})

        response = await deepseek_chat(messages=messages, temperature=0.5)

        return {
            "response": response,
            "metadata": {}
        }
