from rag.retrieval import retrieve_compatibility_info
from utils.deepseek import deepseek_chat
import json

class CompatibilityAgent:
    """Checks if parts are compatible with specific appliance models."""

    def __init__(self):
        self.system_prompt = """You are an appliance compatibility specialist.

Help users determine if a part is compatible with their appliance model.
Use the compatibility database to provide accurate information.
If uncertain, advise users to check with manufacturer or provide their model number."""

    async def check_compatibility(self, part_number: str, model_number: str) -> dict:
        """Check if a part is compatible with a model."""

        # Retrieve compatibility data
        compat_data = await retrieve_compatibility_info(part_number, model_number)

        # Generate response
        context = json.dumps(compat_data, indent=2)

        response = await deepseek_chat(
            messages=[
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": f"Part Number: {part_number}\nModel Number: {model_number}\n\nCompatibility Data:\n{context}\n\nIs this part compatible? Explain clearly."}
            ],
            temperature=0.2
        )

        return {
            "response": response,
            "compatible": compat_data.get("compatible", False),
            "compatibility_data": compat_data,
            "metadata": {
                "part_number": part_number,
                "model_number": model_number
            }
        }

    async def find_compatible_parts(self, model_number: str, part_type: str | None = None) -> dict:
        """Find all compatible parts for a given model."""

        query = f"Compatible parts for model {model_number}"
        if part_type:
            query += f" - {part_type}"

        parts = await retrieve_compatibility_info(query=query)

        context = json.dumps(parts, indent=2)

        response = await deepseek_chat(
            messages=[
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": f"Model: {model_number}\nPart Type: {part_type or 'Any'}\n\nCompatible Parts:\n{context}\n\nList the compatible parts."}
            ],
            temperature=0.2
        )

        return {
            "response": response,
            "parts": parts,
            "metadata": {
                "model_number": model_number,
                "part_type": part_type
            }
        }
