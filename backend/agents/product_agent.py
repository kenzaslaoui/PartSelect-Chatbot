from rag.retrieval import retrieve_parts
from utils.deepseek import deepseek_chat
from utils.schemas import Product

class ProductAgent:
    """Handles product search and recommendation."""

    def __init__(self):
        self.system_prompt = """You are a helpful appliance parts specialist.

Your job is to help users find the right parts for their appliances.
Use the retrieved product information to provide accurate recommendations.
Always include part numbers, prices, and relevant details."""

    async def search_products(self, query: str, appliance_type: str | None = None) -> dict:
        """Search for products based on user query."""

        # Retrieve relevant products from vector DB
        products = await retrieve_parts(query, appliance_type, top_k=5)

        # Generate response using Deepseek
        context = self._format_products_context(products)

        response = await deepseek_chat(
            messages=[
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": f"User query: {query}\n\nAvailable products:\n{context}\n\nProvide a helpful response recommending the most relevant products."}
            ],
            temperature=0.3
        )

        return {
            "response": response,
            "products": products,
            "metadata": {
                "query": query,
                "appliance_type": appliance_type,
                "num_results": len(products)
            }
        }

    def _format_products_context(self, products: list) -> str:
        """Format products for LLM context."""
        context = []
        for p in products:
            context.append(
                f"- {p.get('name', 'Unknown')} (Part #{p.get('part_number', 'N/A')})\n"
                f"  Price: ${p.get('price', 'N/A')}\n"
                f"  Description: {p.get('description', 'N/A')}\n"
                f"  Compatible with: {', '.join(p.get('compatible_models', []))}"
            )
        return "\n\n".join(context)
