"""
Abstract LLM service interface and implementations.

This module defines a package-agnostic interface for LLM operations.
Concrete implementations can be swapped out based on the chosen LLM provider
(e.g., DeepSeek, OpenAI, Anthropic).
"""
from abc import ABC, abstractmethod
from typing import List, Optional
from app.models.schemas import Blog, Repair, Part

try:
    from openai import AsyncOpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False


class LLMService(ABC):
    """
    Abstract base class for LLM operations.

    Implementations should handle:
    - API authentication
    - Context formatting
    - Response generation
    """

    @abstractmethod
    async def generate_response(
        self,
        query: str,
        blogs: Optional[List[Blog]] = None,
        repairs: Optional[List[Repair]] = None,
        parts: Optional[List[Part]] = None,
    ) -> str:
        """
        Generate a response using the LLM with provided context.

        Args:
            query: User's question
            blogs: Optional relevant blog articles (top-k from vector search)
            repairs: Optional relevant repair guides (top-k from vector search)
            parts: Optional relevant replacement parts (top-k from vector search)

        Returns:
            LLM-generated response text
        """
        pass

    @abstractmethod
    async def health_check(self) -> bool:
        """
        Check if the LLM service is available.

        Returns:
            True if service is available, False otherwise
        """
        pass


class DeepSeekLLMService(LLMService):
    """
    LLM service implementation for DeepSeek.

    DeepSeek uses OpenAI-compatible API, so we use the OpenAI client
    with a custom base URL.
    """

    def __init__(self, api_key: Optional[str] = None, model: str = "deepseek-chat"):
        """
        Initialize the DeepSeek LLM service.

        Args:
            api_key: DeepSeek API key
            model: Model identifier to use (default: deepseek-chat)
        """
        if not OPENAI_AVAILABLE:
            raise ImportError(
                "openai package is required for DeepSeek. Install it with: pip install openai"
            )

        self.api_key = api_key
        self.model = model

        # Initialize OpenAI client with Groq base URL
        if api_key:
            self.client = AsyncOpenAI(
                api_key=api_key,
                base_url="https://api.groq.com/openai/v1"
            )
        else:
            self.client = None

    def _format_context(
        self,
        query: str,
        blogs: List[Blog],
        repairs: List[Repair],
        parts: List[Part],
    ) -> str:
        """
        Format the context for the LLM prompt.

        Args:
            query: User's question
            blogs: Relevant blog articles
            repairs: Relevant repair guides
            parts: Relevant replacement parts

        Returns:
            Formatted context string
        """
        context_parts = []

        if blogs:
            context_parts.append("## Relevant Blog Articles:")
            for i, blog in enumerate(blogs, 1):
                context_parts.append(f"{i}. {blog.name}")
                context_parts.append(f"   URL: {blog.url}")
                if blog.metadata:
                    context_parts.append(f"   Details: {blog.metadata}")

        if repairs:
            context_parts.append("\n## Relevant Repair Guides:")
            for i, repair in enumerate(repairs, 1):
                context_parts.append(f"{i}. {repair.name}")
                context_parts.append(f"   URL: {repair.url}")
                if repair.metadata:
                    context_parts.append(f"   Details: {repair.metadata}")

        if parts:
            context_parts.append("\n## Relevant Replacement Parts:")
            for i, part in enumerate(parts, 1):
                context_parts.append(f"{i}. {part.name}")
                context_parts.append(f"   URL: {part.url}")
                if part.metadata:
                    context_parts.append(f"   Details: {part.metadata}")

        return "\n".join(context_parts)

    def _build_prompt(
        self,
        query: str,
        blogs: List[Blog],
        repairs: List[Repair],
        parts: List[Part],
    ) -> str:
        """
        Build the complete prompt for the LLM.

        Args:
            query: User's question
            blogs: Relevant blog articles
            repairs: Relevant repair guides
            parts: Relevant replacement parts

        Returns:
            Complete prompt string
        """
        context = self._format_context(query, blogs, repairs, parts)

        prompt = f"""You are a helpful assistant for appliance repair and parts.
You have access to relevant blog articles, repair guides, and replacement parts to help answer the user's question.

{context}

User Question: {query}

Please provide a helpful, accurate response based on the context provided. If you reference any of the resources above, naturally incorporate them into your answer.
"""
        return prompt

    async def generate_response(
        self,
        query: str,
        blogs: List[Blog] = None,
        repairs: List[Repair] = None,
        parts: List[Part] = None,
    ) -> str:
        """
        Generate a response using DeepSeek LLM.

        Args:
            query: User's question
            blogs: Optional blog articles for context
            repairs: Optional repair guides for context
            parts: Optional replacement parts for context

        Returns:
            LLM-generated response text
        """
        print(f"🔵 [LLM] generate_response called with query: {query}")
        print(f"🔵 [LLM] Client exists: {self.client is not None}")
        print(f"🔵 [LLM] API key exists: {self.api_key is not None}")
        print(f"🔵 [LLM] Model: {self.model}")

        if not self.client:
            print(f"🔴 [LLM] No client - API key not configured")
            raise RuntimeError("DeepSeek API key not configured. Set LLM_API_KEY in .env")

        # For now, just send the query directly without context
        # Later we can add the context back in
        try:
            print(f"🔵 [LLM] Making API call to DeepSeek...")
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a helpful assistant for appliance repair and parts. Provide clear, concise answers to help users troubleshoot and fix their appliances."
                    },
                    {
                        "role": "user",
                        "content": query
                    }
                ],
                temperature=0.7,
                max_tokens=1000,
            )
            print(f"🟢 [LLM] API call successful")
            return response.choices[0].message.content
        except Exception as e:
            print(f"🔴 [LLM] API call failed: {type(e).__name__}: {e}")
            import traceback
            traceback.print_exc()
            raise RuntimeError(f"DeepSeek API call failed: {str(e)}")

    async def health_check(self) -> bool:
        """Check DeepSeek API availability."""
        if not self.client:
            return False
        try:
            # Simple test call
            await self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": "test"}],
                max_tokens=5,
            )
            return True
        except Exception:
            return False
