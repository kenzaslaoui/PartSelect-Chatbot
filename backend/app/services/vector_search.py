"""
Abstract vector search service interface and implementations.

This module defines a package-agnostic interface for vector similarity search.
Concrete implementations can be swapped out based on the chosen vector database
(e.g., Chroma, Pinecone, Weaviate, Qdrant).
"""
from abc import ABC, abstractmethod
from typing import List, Optional
from app.models.schemas import SearchResult

try:
    import chromadb
    from chromadb.config import Settings as ChromaSettings
    CHROMA_AVAILABLE = True
except ImportError:
    CHROMA_AVAILABLE = False


class VectorSearchService(ABC):
    """
    Abstract base class for vector search operations.

    Implementations should handle:
    - Connection to vector database
    - Embedding generation (if needed)
    - Similarity search
    """

    @abstractmethod
    async def search(self, query: str, top_k: int = 5) -> List[SearchResult]:
        """
        Search for similar items in the vector database.

        Args:
            query: The search query text
            top_k: Number of top results to return

        Returns:
            List of SearchResult objects sorted by similarity score (descending)
        """
        pass

    @abstractmethod
    async def health_check(self) -> bool:
        """
        Check if the vector database connection is healthy.

        Returns:
            True if connection is healthy, False otherwise
        """
        pass


class ChromaVectorSearchService(VectorSearchService):
    """
    ChromaDB-based vector search service.

    Uses HNSW (Hierarchical Navigable Small World) indexing for fast similarity search.
    ChromaDB's built-in sentence-transformers embedding function (all-MiniLM-L6-v2 by default).
    """

    def __init__(
        self,
        collection_name: str,
        persist_directory: str = "./chroma_data",
        host: str = None,
        port: int = None,
        hnsw_space: str = "cosine",
        hnsw_construction_ef: int = 200,
        hnsw_search_ef: int = 100,
        hnsw_m: int = 16,
    ):
        """
        Initialize the ChromaDB vector search service with HNSW indexing.

        Args:
            collection_name: Name of the collection (e.g., "blogs", "repairs", "parts")
            persist_directory: Local directory for persistent storage (if using local mode)
            host: ChromaDB server host (if using client/server mode)
            port: ChromaDB server port (if using client/server mode)
            hnsw_space: Distance metric for HNSW. Options: "cosine", "l2", "ip" (inner product)
            hnsw_construction_ef: HNSW construction quality (higher = better recall, slower build)
            hnsw_search_ef: HNSW search quality (higher = better recall, slower search)
            hnsw_m: HNSW max connections per node (higher = better recall, more memory)
        """
        if not CHROMA_AVAILABLE:
            raise ImportError(
                "chromadb is not installed. Install it with: pip install chromadb"
            )

        self.collection_name = collection_name
        self.persist_directory = persist_directory
        self.host = host
        self.port = port

        # Initialize ChromaDB client
        if host and port:
            # Client/server mode
            self.client = chromadb.HttpClient(host=host, port=port)
        else:
            # Local persistent mode
            self.client = chromadb.PersistentClient(path=persist_directory)

        # Get or create collection with HNSW configuration
        # ChromaDB uses HNSW index by default for fast approximate nearest neighbor search
        try:
            self.collection = self.client.get_or_create_collection(
                name=collection_name,
                metadata={
                    "hnsw:space": hnsw_space,  # Distance metric (cosine, l2, ip)
                    "hnsw:construction_ef": hnsw_construction_ef,  # Index build quality
                    "hnsw:search_ef": hnsw_search_ef,  # Search quality
                    "hnsw:M": hnsw_m,  # Max edges per node
                },
            )
        except Exception as e:
            raise RuntimeError(f"Failed to initialize collection '{collection_name}': {e}")

    async def search(self, query: str, top_k: int = 5) -> List[SearchResult]:
        """
        Search for similar items in ChromaDB.

        Args:
            query: The search query text
            top_k: Number of top results to return

        Returns:
            List of SearchResult objects sorted by similarity score (descending)
        """
        try:
            # Query the collection
            # Note: ChromaDB query is synchronous, but we're in async context
            results = self.collection.query(
                query_texts=[query],
                n_results=top_k,
                include=["documents", "metadatas", "distances"],
            )

            # Parse results into SearchResult objects
            search_results = []
            if results["ids"] and len(results["ids"][0]) > 0:
                for i in range(len(results["ids"][0])):
                    # ChromaDB returns distances (lower is better)
                    # Convert to similarity score (higher is better)
                    # For cosine distance: similarity = 1 - distance
                    distance = results["distances"][0][i]
                    similarity_score = 1.0 - distance

                    # Get metadata
                    metadata = results["metadatas"][0][i] if results["metadatas"] else {}

                    # Extract name and url from metadata
                    name = metadata.get("name", "Unknown")
                    url = metadata.get("url", "")

                    search_results.append(
                        SearchResult(
                            name=name,
                            url=url,
                            similarity_score=similarity_score,
                            metadata=metadata,
                        )
                    )

            return search_results

        except Exception as e:
            raise RuntimeError(f"Vector search failed for collection '{self.collection_name}': {e}")

    async def health_check(self) -> bool:
        """Check if ChromaDB connection is healthy."""
        try:
            # Try to access the collection
            self.collection.count()
            return True
        except Exception:
            return False


class BlogVectorSearchService(ChromaVectorSearchService):
    """Vector search service for blog articles using ChromaDB with HNSW indexing."""

    def __init__(self, connection_config: dict = None):
        """
        Initialize the blog vector search service.

        Args:
            connection_config: Dict with keys: collection, persist_directory, host, port, hnsw_*
        """
        config = connection_config or {}
        super().__init__(
            collection_name=config.get("collection", "blogs"),
            persist_directory=config.get("persist_directory", "./chroma_data"),
            host=config.get("host"),
            port=config.get("port"),
            hnsw_space=config.get("hnsw_space", "cosine"),
            hnsw_construction_ef=config.get("hnsw_construction_ef", 200),
            hnsw_search_ef=config.get("hnsw_search_ef", 100),
            hnsw_m=config.get("hnsw_m", 16),
        )


class RepairVectorSearchService(ChromaVectorSearchService):
    """Vector search service for repair guides using ChromaDB with HNSW indexing."""

    def __init__(self, connection_config: dict = None):
        """
        Initialize the repair vector search service.

        Args:
            connection_config: Dict with keys: collection, persist_directory, host, port, hnsw_*
        """
        config = connection_config or {}
        super().__init__(
            collection_name=config.get("collection", "repairs"),
            persist_directory=config.get("persist_directory", "./chroma_data"),
            host=config.get("host"),
            port=config.get("port"),
            hnsw_space=config.get("hnsw_space", "cosine"),
            hnsw_construction_ef=config.get("hnsw_construction_ef", 200),
            hnsw_search_ef=config.get("hnsw_search_ef", 100),
            hnsw_m=config.get("hnsw_m", 16),
        )


class PartVectorSearchService(ChromaVectorSearchService):
    """Vector search service for replacement parts using ChromaDB with HNSW indexing."""

    def __init__(self, connection_config: dict = None):
        """
        Initialize the part vector search service.

        Args:
            connection_config: Dict with keys: collection, persist_directory, host, port, hnsw_*
        """
        config = connection_config or {}
        super().__init__(
            collection_name=config.get("collection", "parts"),
            persist_directory=config.get("persist_directory", "./chroma_data"),
            host=config.get("host"),
            port=config.get("port"),
            hnsw_space=config.get("hnsw_space", "cosine"),
            hnsw_construction_ef=config.get("hnsw_construction_ef", 200),
            hnsw_search_ef=config.get("hnsw_search_ef", 100),
            hnsw_m=config.get("hnsw_m", 16),
        )
