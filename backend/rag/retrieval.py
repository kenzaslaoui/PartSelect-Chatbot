"""
Agent-specific retrieval interfaces for the RAG system.

This module provides specialized retrieval functions for different agent types:
- Part Search Agent: Find parts by description, brand, type (pure vector)
- Compatibility Agent: Check part compatibility with models (pure vector)
- Troubleshooting Agent: Retrieve repair guides and diagnostic info (HYBRID: BM25 + vector)
- Installation Agent: Get installation steps and time estimates (HYBRID: BM25 + vector)

Hybrid search is used for repair guides and installation where exact matches
(error codes, part names) are critical.
"""

import logging
from typing import List, Dict, Any, Optional
from .chroma_db import ChromaDBManager
from .hybrid_search import HybridSearcher

logger = logging.getLogger(__name__)


class PartSearchRetriever:
    """Retriever for Part Search Agent."""

    def __init__(self, chroma_manager: ChromaDBManager):
        """Initialize with ChromaDB manager."""
        self.manager = chroma_manager

    def retrieve_parts(
        self,
        query: str,
        appliance_type: Optional[str] = None,
        brand: Optional[str] = None,
        in_stock_only: bool = False,
        top_k: int = 5
    ) -> Dict[str, Any]:
        """
        Retrieve relevant parts from the parts collections.

        Args:
            query: Search query (e.g., "water dispenser", "spray arm")
            appliance_type: "refrigerator" or "dishwasher" (None = search both)
            brand: Filter by brand (e.g., "LG", "Samsung")
            in_stock_only: Only return in-stock items
            top_k: Number of results to return

        Returns:
            Dict with results, metadata, and relevance scores
        """
        all_results = []

        # Determine which collection(s) to query
        collections = []
        if appliance_type is None or appliance_type == "refrigerator":
            collections.append("parts_refrigerator")
        if appliance_type is None or appliance_type == "dishwasher":
            collections.append("parts_dishwasher")

        # Query each collection
        for collection_name in collections:
            try:
                # Build metadata filters
                where_filters = {}
                if brand:
                    where_filters["brand"] = brand
                if in_stock_only:
                    where_filters["stock_status"] = "in_stock"

                results = self.manager.query_collection(
                    collection_name=collection_name,
                    query_text=query,
                    n_results=top_k,
                    where=where_filters if where_filters else None
                )

                # Format results
                for i, (doc_id, distance, metadata) in enumerate(
                    zip(
                        results["ids"][0],
                        results["distances"][0],
                        results["metadatas"][0]
                    )
                ):
                    all_results.append({
                        "id": doc_id,
                        "collection": collection_name,
                        "relevance_score": 1 - (distance / 2),  # Convert distance to 0-1 score
                        "title": metadata.get("title", "Unknown"),
                        "brand": metadata.get("brand"),
                        "part_type": metadata.get("part_type"),
                        "price": metadata.get("price"),
                        "stock_status": metadata.get("stock_status"),
                        "rating": metadata.get("average_customer_rating"),
                        "review_count": metadata.get("review_count"),
                        "partselect_number": metadata.get("partselect_number"),
                        "manufacturer_number": metadata.get("manufacturer_number"),
                        "url": metadata.get("url"),
                        "installation_type": metadata.get("installation_type"),
                        "installation_time": metadata.get("average_installation_time")
                    })
            except Exception as e:
                logger.error(f"Error querying {collection_name}: {e}")

        # Sort by relevance and return top_k
        all_results.sort(key=lambda x: x["relevance_score"], reverse=True)

        return {
            "query": query,
            "filters": {
                "appliance_type": appliance_type,
                "brand": brand,
                "in_stock_only": in_stock_only
            },
            "total_results": len(all_results),
            "results": all_results[:top_k]
        }


class CompatibilityRetriever:
    """Retriever for Compatibility Agent."""

    def __init__(self, chroma_manager: ChromaDBManager):
        """Initialize with ChromaDB manager."""
        self.manager = chroma_manager

    def retrieve_compatible_parts(
        self,
        model_number: Optional[str] = None,
        part_type: Optional[str] = None,
        appliance_type: Optional[str] = None,
        query: Optional[str] = None,
        top_k: int = 5
    ) -> Dict[str, Any]:
        """
        Retrieve compatible parts based on model or part type.

        Args:
            model_number: Model number to find compatible parts for
            part_type: Type of part needed (e.g., "compressor", "door hinge")
            appliance_type: "refrigerator" or "dishwasher"
            query: Free-text query if model/part_type not specified
            top_k: Number of results to return

        Returns:
            Dict with compatible parts and compatibility info
        """
        search_query = query or f"{part_type or ''} for {model_number or appliance_type}".strip()

        # Determine collections
        collections = []
        if appliance_type is None or appliance_type == "refrigerator":
            collections.append("parts_refrigerator")
        if appliance_type is None or appliance_type == "dishwasher":
            collections.append("parts_dishwasher")

        all_results = []

        for collection_name in collections:
            try:
                # Build filters
                where_filters = {}
                if part_type:
                    where_filters["part_type"] = part_type

                results = self.manager.query_collection(
                    collection_name=collection_name,
                    query_text=search_query,
                    n_results=top_k,
                    where=where_filters if where_filters else None
                )

                for doc_id, distance, metadata in zip(
                    results["ids"][0],
                    results["distances"][0],
                    results["metadatas"][0]
                ):
                    all_results.append({
                        "id": doc_id,
                        "collection": collection_name,
                        "relevance_score": 1 - (distance / 2),
                        "title": metadata.get("title"),
                        "part_type": metadata.get("part_type"),
                        "manufacturer_number": metadata.get("manufacturer_number"),
                        "partselect_number": metadata.get("partselect_number"),
                        "compatible_models": [model_number] if model_number else [],
                        "price": metadata.get("price"),
                        "stock_status": metadata.get("stock_status"),
                        "url": metadata.get("url")
                    })
            except Exception as e:
                logger.error(f"Error querying {collection_name}: {e}")

        all_results.sort(key=lambda x: x["relevance_score"], reverse=True)

        return {
            "model_number": model_number,
            "part_type": part_type,
            "appliance_type": appliance_type,
            "total_results": len(all_results),
            "results": all_results[:top_k]
        }


class TroubleshootingRetriever:
    """Retriever for Troubleshooting Agent - Uses HYBRID search for better accuracy."""

    def __init__(self, chroma_manager: ChromaDBManager):
        """Initialize with ChromaDB manager and hybrid searcher."""
        self.manager = chroma_manager
        self.hybrid_searcher = HybridSearcher(chroma_manager)

    def retrieve_troubleshooting_guides(
        self,
        issue_description: str,
        appliance_type: Optional[str] = None,
        difficulty: Optional[str] = None,
        include_videos: bool = True,
        top_k: int = 5
    ) -> Dict[str, Any]:
        """
        Retrieve troubleshooting guides using HYBRID search (BM25 + vector).

        This method combines keyword search (for exact symptom/error codes) with
        semantic search (for similar issues) for more robust results.

        Args:
            issue_description: Description of the problem (e.g., "water leaking from bottom", "E5 error")
            appliance_type: "refrigerator" or "dishwasher"
            difficulty: "easy", "medium", or "hard" (None = any)
            include_videos: Whether to prioritize results with video tutorials
            top_k: Number of results to return

        Returns:
            Dict with troubleshooting guides, steps, and video links
        """
        all_results = []

        # Build where filters
        where_filters = {}
        if appliance_type:
            where_filters["appliance_type"] = appliance_type
        if difficulty:
            where_filters["difficulty"] = difficulty

        # Use HYBRID search for repair_symptoms (better for error codes, symptoms)
        try:
            hybrid_results = self.hybrid_searcher.hybrid_search(
                collection_name="repair_symptoms",
                query=issue_description,
                top_k=top_k,
                where=where_filters if where_filters else None,
                vector_weight=0.5,  # Balance vector and keyword search
                keyword_weight=0.5
            )

            for result in hybrid_results.get("hybrid_results", []):
                metadata = result.get("metadata", {})
                relevance = result.get("hybrid_score", 0)

                # Boost score for results with videos
                if metadata.get("has_video") and include_videos:
                    relevance = min(relevance * 1.2, 1.0)

                all_results.append({
                    "id": result["id"],
                    "source": "repair_guide",
                    "relevance_score": relevance,
                    "vector_score": result.get("vector_score"),
                    "keyword_score": result.get("keyword_score"),
                    "search_method": result.get("source"),  # "vector", "keyword", or "hybrid"
                    "symptom": metadata.get("symptom_name"),
                    "appliance_type": metadata.get("appliance_type"),
                    "difficulty": metadata.get("difficulty"),
                    "part_name": metadata.get("part_name"),
                    "has_video": metadata.get("has_video"),
                    "video_url": metadata.get("video_url"),
                    "video_id": metadata.get("video_id"),
                    "guide_type": metadata.get("repair_guide_type"),
                    "guide_title": metadata.get("repair_guide_title"),
                    "url": metadata.get("url")
                })
        except Exception as e:
            logger.error(f"Error in hybrid search for repair_symptoms: {e}")
            # Fallback to pure vector search
            try:
                repair_results = self.manager.query_collection(
                    collection_name="repair_symptoms",
                    query_text=issue_description,
                    n_results=top_k,
                    where=where_filters if where_filters else None
                )

                for doc_id, distance, metadata in zip(
                    repair_results["ids"][0],
                    repair_results["distances"][0],
                    repair_results["metadatas"][0]
                ):
                    relevance = 1 - (distance / 2)
                    if metadata.get("has_video") and include_videos:
                        relevance *= 1.2

                    all_results.append({
                        "id": doc_id,
                        "source": "repair_guide",
                        "relevance_score": min(relevance, 1.0),
                        "symptom": metadata.get("symptom_name"),
                        "appliance_type": metadata.get("appliance_type"),
                        "difficulty": metadata.get("difficulty"),
                        "part_name": metadata.get("part_name"),
                        "has_video": metadata.get("has_video"),
                        "video_url": metadata.get("video_url"),
                        "video_id": metadata.get("video_id"),
                        "guide_type": metadata.get("repair_guide_type"),
                        "guide_title": metadata.get("repair_guide_title"),
                        "url": metadata.get("url")
                    })
            except Exception as e2:
                logger.error(f"Fallback vector search also failed: {e2}")

        # Query blogs for additional guides (use pure vector for broader context)
        try:
            blog_results = self.manager.query_collection(
                collection_name="blogs_articles",
                query_text=issue_description,
                n_results=top_k // 2,
                where={"topic_category": "repair"} if appliance_type is None else None
            )

            for doc_id, distance, metadata in zip(
                blog_results["ids"][0],
                blog_results["distances"][0],
                blog_results["metadatas"][0]
            ):
                all_results.append({
                    "id": doc_id,
                    "source": "blog_article",
                    "relevance_score": 1 - (distance / 2),
                    "title": metadata.get("title"),
                    "appliance_type": metadata.get("appliance_type"),
                    "chunk_number": metadata.get("chunk_number"),
                    "total_chunks": metadata.get("total_chunks"),
                    "has_video": metadata.get("has_video"),
                    "url": metadata.get("url")
                })
        except Exception as e:
            logger.error(f"Error querying blogs_articles: {e}")

        # Sort by relevance
        all_results.sort(key=lambda x: x["relevance_score"], reverse=True)

        return {
            "issue": issue_description,
            "filters": {
                "appliance_type": appliance_type,
                "difficulty": difficulty
            },
            "search_type": "hybrid",
            "total_results": len(all_results),
            "results": all_results[:top_k]
        }


class InstallationRetriever:
    """Retriever for Installation Agent - Uses HYBRID search for better accuracy."""

    def __init__(self, chroma_manager: ChromaDBManager):
        """Initialize with ChromaDB manager and hybrid searcher."""
        self.manager = chroma_manager
        self.hybrid_searcher = HybridSearcher(chroma_manager)

    def retrieve_installation_guides(
        self,
        part_number: Optional[str] = None,
        part_name: Optional[str] = None,
        appliance_type: Optional[str] = None,
        top_k: int = 5
    ) -> Dict[str, Any]:
        """
        Retrieve installation guides for a specific part using HYBRID search.

        This method combines keyword search (for exact part names) with
        semantic search (for similar installation guides) for more robust results.

        Args:
            part_number: PartSelect or manufacturer part number
            part_name: Name of the part (e.g., "water dispenser")
            appliance_type: "refrigerator" or "dishwasher"
            top_k: Number of results to return

        Returns:
            Dict with installation steps, time estimates, difficulty level
        """
        search_query = f"install {part_name or part_number}".strip()
        all_results = []

        # Build where filters
        where_filters = {"repair_guide_type": "replacement"}
        if appliance_type:
            where_filters["appliance_type"] = appliance_type

        # Use HYBRID search for repair_symptoms (better for exact part names)
        try:
            hybrid_results = self.hybrid_searcher.hybrid_search(
                collection_name="repair_symptoms",
                query=search_query,
                top_k=top_k,
                where=where_filters,
                vector_weight=0.5,  # Balance vector and keyword search
                keyword_weight=0.5
            )

            for result in hybrid_results.get("hybrid_results", []):
                metadata = result.get("metadata", {})
                relevance = result.get("hybrid_score", 0)

                all_results.append({
                    "id": result["id"],
                    "source": "repair_guide",
                    "relevance_score": relevance,
                    "vector_score": result.get("vector_score"),
                    "keyword_score": result.get("keyword_score"),
                    "search_method": result.get("source"),  # "vector", "keyword", or "hybrid"
                    "part_name": metadata.get("part_name"),
                    "appliance_type": metadata.get("appliance_type"),
                    "difficulty": metadata.get("difficulty"),
                    "guide_type": metadata.get("repair_guide_type"),
                    "guide_title": metadata.get("repair_guide_title"),
                    "has_video": metadata.get("has_video"),
                    "video_url": metadata.get("video_url"),
                    "url": metadata.get("url")
                })
        except Exception as e:
            logger.error(f"Error in hybrid search for repair_symptoms: {e}")
            # Fallback to pure vector search
            try:
                results = self.manager.query_collection(
                    collection_name="repair_symptoms",
                    query_text=search_query,
                    n_results=top_k,
                    where=where_filters
                )

                for doc_id, distance, metadata in zip(
                    results["ids"][0],
                    results["distances"][0],
                    results["metadatas"][0]
                ):
                    all_results.append({
                        "id": doc_id,
                        "source": "repair_guide",
                        "relevance_score": 1 - (distance / 2),
                        "part_name": metadata.get("part_name"),
                        "appliance_type": metadata.get("appliance_type"),
                        "difficulty": metadata.get("difficulty"),
                        "guide_type": metadata.get("repair_guide_type"),
                        "guide_title": metadata.get("repair_guide_title"),
                        "has_video": metadata.get("has_video"),
                        "video_url": metadata.get("video_url"),
                        "url": metadata.get("url")
                    })
            except Exception as e2:
                logger.error(f"Fallback vector search also failed: {e2}")

        # Query blogs for installation articles
        try:
            results = self.manager.query_collection(
                collection_name="blogs_articles",
                query_text=search_query,
                n_results=top_k // 2
            )

            for doc_id, distance, metadata in zip(
                results["ids"][0],
                results["distances"][0],
                results["metadatas"][0]
            ):
                all_results.append({
                    "id": doc_id,
                    "source": "blog_article",
                    "relevance_score": 1 - (distance / 2),
                    "title": metadata.get("title"),
                    "appliance_type": metadata.get("appliance_type"),
                    "chunk_number": metadata.get("chunk_number"),
                    "total_chunks": metadata.get("total_chunks"),
                    "has_video": metadata.get("has_video"),
                    "url": metadata.get("url")
                })
        except Exception as e:
            logger.error(f"Error querying blogs_articles: {e}")

        # Query parts collection for installation time estimates
        try:
            collections = []
            if appliance_type is None or appliance_type == "refrigerator":
                collections.append("parts_refrigerator")
            if appliance_type is None or appliance_type == "dishwasher":
                collections.append("parts_dishwasher")

            for collection_name in collections:
                results = self.manager.query_collection(
                    collection_name=collection_name,
                    query_text=part_name or part_number or "",
                    n_results=3
                )

                for doc_id, distance, metadata in zip(
                    results["ids"][0],
                    results["distances"][0],
                    results["metadatas"][0]
                ):
                    if distance < 1.0:  # Only very close matches for installation time
                        all_results.append({
                            "id": doc_id,
                            "source": "parts_catalog",
                            "relevance_score": 1 - (distance / 2),
                            "title": metadata.get("title"),
                            "installation_type": metadata.get("installation_type"),
                            "installation_time": metadata.get("average_installation_time"),
                            "url": metadata.get("url")
                        })
        except Exception as e:
            logger.error(f"Error querying parts collections: {e}")

        # Sort by relevance
        all_results.sort(key=lambda x: x["relevance_score"], reverse=True)

        return {
            "part_number": part_number,
            "part_name": part_name,
            "appliance_type": appliance_type,
            "total_results": len(all_results),
            "results": all_results[:top_k]
        }


# Convenience functions for backward compatibility
async def retrieve_parts(query: str, appliance_type: Optional[str] = None, top_k: int = 5):
    """Retrieve relevant parts from vector database."""
    try:
        manager = ChromaDBManager()
        retriever = PartSearchRetriever(manager)
        return retriever.retrieve_parts(query, appliance_type, top_k=top_k)
    except Exception as e:
        logger.error(f"Error retrieving parts: {e}")
        return {"error": str(e), "results": []}


async def retrieve_compatibility_info(
    part_number: Optional[str] = None,
    model_number: Optional[str] = None,
    query: Optional[str] = None
):
    """Retrieve compatibility information."""
    try:
        manager = ChromaDBManager()
        retriever = CompatibilityRetriever(manager)
        return retriever.retrieve_compatible_parts(
            model_number=model_number,
            query=query
        )
    except Exception as e:
        logger.error(f"Error retrieving compatibility info: {e}")
        return {"error": str(e), "results": []}


async def retrieve_troubleshooting_info(
    issue_description: str,
    appliance_type: Optional[str] = None
):
    """Retrieve troubleshooting data."""
    try:
        manager = ChromaDBManager()
        retriever = TroubleshootingRetriever(manager)
        return retriever.retrieve_troubleshooting_guides(issue_description, appliance_type)
    except Exception as e:
        logger.error(f"Error retrieving troubleshooting info: {e}")
        return {"error": str(e), "results": []}


async def retrieve_installation_guide(
    part_number: str,
    model_number: Optional[str] = None
):
    """Retrieve installation guide."""
    try:
        manager = ChromaDBManager()
        retriever = InstallationRetriever(manager)
        return retriever.retrieve_installation_guides(part_number=part_number)
    except Exception as e:
        logger.error(f"Error retrieving installation guide: {e}")
        return {"error": str(e), "results": []}
