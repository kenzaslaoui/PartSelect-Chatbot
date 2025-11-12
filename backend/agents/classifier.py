from utils.deepseek import deepseek_chat
from utils.schemas import Intent

class IntentClassifier:
    """Classifies user intent for routing to appropriate agent."""

    INTENTS = [
        "product_search",
        "compatibility_check",
        "troubleshooting",
        "installation_guide",
        "general_question"
    ]

    def __init__(self):
        self.system_prompt = """You are an intent classifier for an appliance parts assistant.

Classify the user's message into one of these intents:
- product_search: User wants to find/buy a specific part
- compatibility_check: User wants to know if a part fits their appliance
- troubleshooting: User has an appliance problem and needs diagnosis
- installation_guide: User needs help installing a part
- general_question: General questions about appliances or the service

Respond with ONLY the intent name, nothing else."""

    async def classify(self, message: str) -> str:
        """Classify user message intent."""
        prompt = f"User message: {message}\n\nIntent:"

        response = await deepseek_chat(
            messages=[
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": prompt}
            ],
            temperature=0.1
        )

        intent = response.strip().lower()

        # Validate intent
        if intent not in self.INTENTS:
            return "general_question"

        return intent
