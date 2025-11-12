"""
Hybrid Search Module - Combines BM25 keyword search with vector search.

Provides robustness for exact matches (error codes, part names) while maintaining
semantic search capabilities.

Strategy:
1. BM25 (keyword search) - Finds exact and partial matches
2. Vector search - Finds semantic/contextual matches
3. Merge results - Combine both for best coverage
"""

import logging
from typing import Dict, List, Any, Optional, Set
from collections import defaultdict
import math

logger = logging.getLogger(__name__)


class BM25Searcher:
    """BM25 keyword-based search implementation."""

    def __init__(self, k1: float = 1.5, b: float = 0.75):
        """
        Initialize BM25 with tunable parameters.

        Args:
            k1: Controls term frequency saturation (default 1.5)
            b: Controls length normalization (default 0.75)
        """
        self.k1 = k1
        self.b = b
        self.documents: List[Dict[str, Any]] = []
        self.idf_cache: Dict[str, float] = {}

    def add_documents(self, documents: List[Dict[str, Any]], text_field: str = "text") -> None:
        """
        Add documents to index.

        Args:
            documents: List of document dicts
            text_field: Field name containing searchable text
        """
        self.documents = documents
        self.text_field = text_field
        self._build_idf()
        logger.debug(f"Indexed {len(documents)} documents for BM25 search")

    def _tokenize(self, text: str) -> List[str]:
        """Simple tokenization (lowercase, split on whitespace)."""
        if not text:
            return []
        return text.lower().split()

    def _build_idf(self) -> None:
        """Build IDF (Inverse Document Frequency) cache."""
        doc_count = len(self.documents)
        term_doc_count: Dict[str, int] = defaultdict(int)

        # Count how many documents contain each term
        for doc in self.documents:
            text = doc.get(self.text_field, "")
            tokens = set(self._tokenize(text))
            for token in tokens:
                term_doc_count[token] += 1

        # Calculate IDF for each term
        for term, count in term_doc_count.items():
            self.idf_cache[term] = math.log((doc_count - count + 0.5) / (count + 0.5) + 1)

    def _get_idf(self, term: str) -> float:
        """Get IDF score for a term."""
        return self.idf_cache.get(term, 0.0)

    def search(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """
        Search documents using BM25.

        Args:
            query: Search query
            top_k: Number of top results to return

        Returns:
            List of documents with BM25 scores
        """
        if not self.documents:
            return []

        query_tokens = self._tokenize(query)
        if not query_tokens:
            return []

        scores: Dict[int, float] = defaultdict(float)
        avg_doc_length = sum(
            len(self._tokenize(doc.get(self.text_field, "")))
            for doc in self.documents
        ) / max(len(self.documents), 1)

        # Calculate BM25 score for each document
        for doc_idx, doc in enumerate(self.documents):
            doc_text = doc.get(self.text_field, "")
            doc_tokens = self._tokenize(doc_text)
            doc_length = len(doc_tokens)

            for query_token in query_tokens:
                term_freq = doc_tokens.count(query_token)
                if term_freq > 0:
                    idf = self._get_idf(query_token)
                    # BM25 formula
                    numerator = idf * term_freq * (self.k1 + 1)
                    denominator = (
                        term_freq
                        + self.k1 * (1 - self.b + self.b * (doc_length / avg_doc_length))
                    )
                    scores[doc_idx] += numerator / denominator

        # Sort by score and return top_k
        ranked = sorted(
            [(idx, score) for idx, score in scores.items()],
            key=lambda x: x[1],
            reverse=True
        )

        results = []
        for doc_idx, score in ranked[:top_k]:
            doc = self.documents[doc_idx].copy()
            doc["bm25_score"] = score
            results.append(doc)

        return results


class HybridSearcher:
    """Combines BM25 and vector search for robust retrieval."""

    def __init__(self, chroma_manager):
        """
        Initialize hybrid searcher.

        Args:
            chroma_manager: ChromaDB manager instance
        """
        self.chroma_manager = chroma_manager
        self.bm25_searchers: Dict[str, BM25Searcher] = {}

    def _prepare_bm25_index(self, collection_name: str, documents_text: List[str], metadata: List[Dict]) -> BM25Searcher:
        """
        Prepare BM25 index for a collection.

        Args:
            collection_name: Name of collection
            documents_text: List of document texts
            metadata: List of metadata dicts

        Returns:
            BM25Searcher instance
        """
        if collection_name not in self.bm25_searchers:
            docs = [
                {
                    "id": metadata[i].get("id", str(i)),
                    "text": documents_text[i],
                    "metadata": metadata[i]
                }
                for i in range(len(documents_text))
            ]
            searcher = BM25Searcher()
            searcher.add_documents(docs, text_field="text")
            self.bm25_searchers[collection_name] = searcher

        return self.bm25_searchers[collection_name]

    def hybrid_search(
        self,
        collection_name: str,
        query: str,
        documents_text: Optional[List[str]] = None,
        metadata: Optional[List[Dict]] = None,
        top_k: int = 5,
        where: Optional[Dict] = None,
        vector_weight: float = 0.6,
        keyword_weight: float = 0.4
    ) -> Dict[str, Any]:
        """
        Perform hybrid search combining vector and keyword search.

        Args:
            collection_name: ChromaDB collection name
            query: Search query
            documents_text: Document texts for BM25 (optional, will fetch from ChromaDB)
            metadata: Metadata for documents (optional)
            top_k: Number of top results
            where: Metadata filter for vector search
            vector_weight: Weight for vector search results (0-1)
            keyword_weight: Weight for keyword search results (0-1)

        Returns:
            Dict with hybrid search results
        """
        results = {"query": query, "method": "hybrid", "vector_results": [], "keyword_results": [], "hybrid_results": []}

        # Step 1: Vector search
        try:
            vector_results = self.chroma_manager.query_collection(
                collection_name=collection_name,
                query_text=query,
                n_results=top_k * 2,  # Get more to account for merging
                where=where
            )

            if vector_results.get("ids") and vector_results["ids"][0]:
                for doc_id, distance, meta in zip(
                    vector_results["ids"][0],
                    vector_results["distances"][0],
                    vector_results["metadatas"][0]
                ):
                    vector_score = 1 - (distance / 2)  # Convert distance to similarity
                    results["vector_results"].append({
                        "id": doc_id,
                        "vector_score": vector_score,
                        "distance": distance,
                        "metadata": meta
                    })
        except Exception as e:
            logger.error(f"Vector search error in {collection_name}: {e}")

        # Step 2: Keyword search (BM25)
        try:
            if documents_text is None or metadata is None:
                # Fetch from collection if not provided
                vector_data = self.chroma_manager.query_collection(
                    collection_name=collection_name,
                    query_text="",  # Get all documents
                    n_results=1000
                )
                if vector_data.get("documents") and vector_data["documents"][0]:
                    documents_text = vector_data["documents"][0]
                    metadata = vector_data.get("metadatas", [[]])[0]

            if documents_text and metadata:
                bm25_searcher = self._prepare_bm25_index(collection_name, documents_text, metadata)
                bm25_results = bm25_searcher.search(query, top_k=top_k * 2)

                # Normalize BM25 scores to 0-1 range
                max_bm25_score = max([r.get("bm25_score", 0) for r in bm25_results]) if bm25_results else 1
                for result in bm25_results:
                    keyword_score = result.get("bm25_score", 0) / max(max_bm25_score, 1)
                    results["keyword_results"].append({
                        "id": result.get("id"),
                        "keyword_score": keyword_score,
                        "bm25_score": result.get("bm25_score"),
                        "metadata": result.get("metadata", {})
                    })
        except Exception as e:
            logger.error(f"Keyword search error in {collection_name}: {e}")

        # Step 3: Merge results
        merged: Dict[str, Dict[str, Any]] = {}

        # Add vector results
        for result in results["vector_results"]:
            doc_id = result["id"]
            merged[doc_id] = {
                "id": doc_id,
                "vector_score": result["vector_score"],
                "keyword_score": 0.0,
                "metadata": result["metadata"],
                "source": "vector"
            }

        # Add/merge keyword results
        for result in results["keyword_results"]:
            doc_id = result["id"]
            if doc_id in merged:
                merged[doc_id]["keyword_score"] = result["keyword_score"]
                merged[doc_id]["source"] = "hybrid"
            else:
                merged[doc_id] = {
                    "id": doc_id,
                    "vector_score": 0.0,
                    "keyword_score": result["keyword_score"],
                    "metadata": result["metadata"],
                    "source": "keyword"
                }

        # Step 4: Score and rank
        for doc_id, doc_result in merged.items():
            hybrid_score = (
                doc_result["vector_score"] * vector_weight +
                doc_result["keyword_score"] * keyword_weight
            )
            doc_result["hybrid_score"] = hybrid_score

        # Sort by hybrid score
        ranked_results = sorted(
            merged.values(),
            key=lambda x: x["hybrid_score"],
            reverse=True
        )[:top_k]

        results["hybrid_results"] = ranked_results
        results["total_results"] = len(ranked_results)

        logger.debug(
            f"Hybrid search: {len(results['vector_results'])} vector + "
            f"{len(results['keyword_results'])} keyword = {len(ranked_results)} hybrid results"
        )

        return results
