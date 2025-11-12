from rag.retrieval import retrieve_installation_guide
from utils.deepseek import deepseek_chat
import json

class InstallationAgent:
    """Provides installation guides and instructions for parts."""

    def __init__(self):
        self.system_prompt = """You are an appliance repair and installation expert.

Provide clear, step-by-step installation instructions for appliance parts.
Include safety warnings, required tools, and helpful tips.
Break down complex procedures into manageable steps."""

    async def get_installation_guide(self, part_number: str, model_number: str | None = None) -> dict:
        """Get installation instructions for a specific part."""

        # Retrieve installation guide from database
        guide_data = await retrieve_installation_guide(part_number, model_number)

        # Generate formatted instructions
        context = json.dumps(guide_data, indent=2)

        response = await deepseek_chat(
            messages=[
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": f"Part: {part_number}\nModel: {model_number or 'Generic'}\n\nInstallation Data:\n{context}\n\nProvide clear installation instructions."}
            ],
            temperature=0.2
        )

        return {
            "response": response,
            "steps": guide_data.get("steps", []),
            "tools_required": guide_data.get("tools", []),
            "difficulty": guide_data.get("difficulty", "medium"),
            "estimated_time": guide_data.get("time", "30-60 minutes"),
            "safety_warnings": guide_data.get("warnings", []),
            "metadata": {
                "part_number": part_number,
                "model_number": model_number
            }
        }

    async def answer_installation_question(self, question: str, part_context: dict) -> dict:
        """Answer specific questions about installation."""

        context = json.dumps(part_context, indent=2)

        response = await deepseek_chat(
            messages=[
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": f"Question: {question}\n\nPart Context:\n{context}\n\nProvide a helpful answer."}
            ],
            temperature=0.3
        )

        return {
            "response": response,
            "metadata": {
                "question": question
            }
        }
