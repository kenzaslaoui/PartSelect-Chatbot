"""
Chat service orchestration layer.

This module handles the main business logic for the chat endpoint:
1. Parallel vector searches across blogs, repairs, and parts
2. Filtering results based on thresholds
3. LLM integration with context
4. Response formatting
"""
import asyncio
from typing import List, Tuple
from app.models.schemas import (
    Blog,
    Repair,
    Part,
    ChatRequest,
    ChatResponse,
    SearchResult,
)
from app.services.vector_search import VectorSearchService
from app.services.llm import LLMService


class ChatService:
    """
    Orchestrates the chat workflow: vector search -> LLM -> filtering -> response.
    """

    def __init__(
        self,
        blog_search: VectorSearchService,
        repair_search: VectorSearchService,
        part_search: VectorSearchService,
        llm_service: LLMService,
        top_k: int = 5,
        response_threshold: float = 0.7,
    ):
        """
        Initialize the chat service.

        Args:
            blog_search: Vector search service for blogs
            repair_search: Vector search service for repairs
            part_search: Vector search service for parts
            llm_service: LLM service for generating responses
            top_k: Number of top results to fetch from each vector DB (sent to LLM)
            response_threshold: Minimum similarity score for results returned to user
        """
        self.blog_search = blog_search
        self.repair_search = repair_search
        self.part_search = part_search
        self.llm_service = llm_service
        self.top_k = top_k
        self.response_threshold = response_threshold

    async def _parallel_vector_search(
        self, query: str
    ) -> Tuple[List[SearchResult], List[SearchResult], List[SearchResult]]:
        """
        Perform parallel vector searches across all three databases.

        Args:
            query: User's search query

        Returns:
            Tuple of (blog_results, repair_results, part_results)
        """
        # Run all three searches concurrently
        blog_task = self.blog_search.search(query, self.top_k)
        repair_task = self.repair_search.search(query, self.top_k)
        part_task = self.part_search.search(query, self.top_k)

        blog_results, repair_results, part_results = await asyncio.gather(
            blog_task, repair_task, part_task
        )

        return blog_results, repair_results, part_results

    def _convert_to_typed_results(
        self,
        blog_results: List[SearchResult],
        repair_results: List[SearchResult],
        part_results: List[SearchResult],
    ) -> Tuple[List[Blog], List[Repair], List[Part]]:
        """
        Convert generic SearchResult objects to typed domain objects.

        Args:
            blog_results: Generic search results for blogs
            repair_results: Generic search results for repairs
            part_results: Generic search results for parts

        Returns:
            Tuple of typed (blogs, repairs, parts)
        """
        blogs = [
            Blog(
                name=r.name,
                url=r.url,
                similarity_score=r.similarity_score,
                metadata=r.metadata,
            )
            for r in blog_results
        ]

        repairs = [
            Repair(
                name=r.name,
                url=r.url,
                similarity_score=r.similarity_score,
                metadata=r.metadata,
            )
            for r in repair_results
        ]

        parts = [
            Part(
                name=r.name,
                url=r.url,
                similarity_score=r.similarity_score,
                metadata=r.metadata,
            )
            for r in part_results
        ]

        return blogs, repairs, parts

    def _filter_by_threshold(
        self, blogs: List[Blog], repairs: List[Repair], parts: List[Part]
    ) -> Tuple[List[Blog], List[Repair], List[Part]]:
        """
        Filter results to only include items above the response threshold.

        All top-k results are sent to the LLM for context, but only high-confidence
        results (above threshold) are returned to the user.

        Args:
            blogs: All blog results
            repairs: All repair results
            parts: All part results

        Returns:
            Filtered tuple of (blogs, repairs, parts)
        """
        filtered_blogs = [
            blog for blog in blogs if blog.similarity_score >= self.response_threshold
        ]

        filtered_repairs = [
            repair
            for repair in repairs
            if repair.similarity_score >= self.response_threshold
        ]

        filtered_parts = [
            part for part in parts if part.similarity_score >= self.response_threshold
        ]

        return filtered_blogs, filtered_repairs, filtered_parts

    async def handle_chat(self, request: ChatRequest) -> ChatResponse:
        """
        Handle a chat request end-to-end.

        Workflow:
        1. Perform parallel vector searches (3 concurrent calls)
        2. Convert results to typed objects
        3. Send all top-k results to LLM for context
        4. Filter results by threshold for user response
        5. Return formatted response

        Args:
            request: Chat request with user query

        Returns:
            Chat response with LLM answer and filtered resources
        """
        query = request.query

        # Step 1: Parallel vector searches
        blog_results, repair_results, part_results = await self._parallel_vector_search(
            query
        )

        # Step 2: Convert to typed objects
        all_blogs, all_repairs, all_parts = self._convert_to_typed_results(
            blog_results, repair_results, part_results
        )

        # Step 3: Generate LLM response using ALL top-k results as context
        llm_response = await self.llm_service.generate_response(
            query=query, blogs=all_blogs, repairs=all_repairs, parts=all_parts
        )

        # Step 4: Filter results by threshold for user response
        filtered_blogs, filtered_repairs, filtered_parts = self._filter_by_threshold(
            all_blogs, all_repairs, all_parts
        )

        # Step 5: Build and return response
        return ChatResponse(
            response=llm_response,
            blogs=filtered_blogs,
            repairs=filtered_repairs,
            parts=filtered_parts,
        )

    async def health_check(self) -> dict:
        """
        Check health of all dependent services.

        Returns:
            Dictionary with health status of each service
        """
        blog_health = await self.blog_search.health_check()
        repair_health = await self.repair_search.health_check()
        part_health = await self.part_search.health_check()
        llm_health = await self.llm_service.health_check()

        return {
            "blog_search": blog_health,
            "repair_search": repair_health,
            "part_search": part_health,
            "llm_service": llm_health,
            "overall": all([blog_health, repair_health, part_health, llm_health]),
        }
