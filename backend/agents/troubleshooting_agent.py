from rag.retrieval import retrieve_troubleshooting_info
from utils.deepseek import deepseek_chat
import json

class TroubleshootingAgent:
    """Diagnoses appliance issues and recommends solutions/parts."""

    def __init__(self):
        self.system_prompt = """You are an expert appliance troubleshooting specialist.

Help users diagnose problems with their appliances and recommend solutions.
Use the troubleshooting database to identify likely causes and required parts.
Ask clarifying questions if needed. Provide step-by-step diagnostic guidance."""

    async def diagnose_issue(self, issue_description: str, appliance_type: str | None = None) -> dict:
        """Diagnose an appliance issue and recommend solutions."""

        # Retrieve relevant troubleshooting info
        troubleshooting_data = await retrieve_troubleshooting_info(
            issue_description,
            appliance_type
        )

        # Generate diagnostic response
        context = json.dumps(troubleshooting_data, indent=2)

        response = await deepseek_chat(
            messages=[
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": f"Issue: {issue_description}\nAppliance: {appliance_type or 'Unknown'}\n\nTroubleshooting Data:\n{context}\n\nProvide diagnosis and solution steps."}
            ],
            temperature=0.3
        )

        return {
            "response": response,
            "possible_causes": troubleshooting_data.get("causes", []),
            "recommended_parts": troubleshooting_data.get("parts", []),
            "diagnostic_steps": troubleshooting_data.get("steps", []),
            "metadata": {
                "issue": issue_description,
                "appliance_type": appliance_type
            }
        }

    async def guided_troubleshooting(self, conversation_history: list) -> dict:
        """Interactive troubleshooting with follow-up questions."""

        # Use conversation history to guide diagnosis
        messages = [{"role": "system", "content": self.system_prompt}]
        messages.extend(conversation_history)

        response = await deepseek_chat(
            messages=messages,
            temperature=0.4
        )

        return {
            "response": response,
            "next_question": self._extract_question(response),
            "metadata": {
                "conversation_length": len(conversation_history)
            }
        }

    def _extract_question(self, response: str) -> str | None:
        """Extract follow-up question from response if present."""
        if "?" in response:
            # Simple extraction - can be improved
            lines = response.split("\n")
            for line in lines:
                if "?" in line:
                    return line.strip()
        return None
