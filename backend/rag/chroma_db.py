"""
ChromaDB initialization and management.

This module handles:
- ChromaDB client setup with HNSW
- Collection creation and management
- Document insertion and retrieval
"""

import logging
from pathlib import Path
from typing import List, Dict, Any, Optional

import chromadb
from chromadb.utils import embedding_functions

logger = logging.getLogger(__name__)


class ChromaDBManager:
    """Manager for ChromaDB operations."""

    def __init__(
        self,
        persist_directory: str = "data/chroma_db",
        embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    ):
        """
        Initialize ChromaDB manager.

        Args:
            persist_directory: Path to persistent ChromaDB storage
            embedding_model: Embedding model to use
        """
        self.persist_directory = persist_directory
        self.embedding_model = embedding_model

        # Create directory if needed
        Path(persist_directory).mkdir(parents=True, exist_ok=True)

        # Initialize ChromaDB with persistent storage (new API)
        self.client = chromadb.PersistentClient(path=persist_directory)
        self.collections = {}

        logger.info(f"ChromaDB initialized at {persist_directory}")

    def create_collection(
        self,
        collection_name: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> chromadb.Collection:
        """
        Create or get a collection.

        Args:
            collection_name: Name of collection
            metadata: Optional metadata dict

        Returns:
            ChromaDB collection object
        """
        # Get or create collection with embedding function
        collection = self.client.get_or_create_collection(
            name=collection_name,
            metadata=metadata or {"hnsw:space": "cosine"},
            embedding_function=embedding_functions.SentenceTransformerEmbeddingFunction(
                model_name=self.embedding_model
            )
        )

        self.collections[collection_name] = collection
        logger.info(f"Created/retrieved collection: {collection_name}")

        return collection

    def populate_collection(
        self,
        collection_name: str,
        ids: List[str],
        documents: List[str],
        metadatas: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Populate a collection with documents.

        Args:
            collection_name: Name of collection
            ids: Document IDs
            documents: Document texts (will be embedded)
            metadatas: Metadata dicts

        Returns:
            Result stats
        """
        if collection_name not in self.collections:
            self.create_collection(collection_name)

        collection = self.collections[collection_name]

        # Filter out None values from metadatas (ChromaDB doesn't allow None values)
        cleaned_metadatas = []
        for meta in metadatas:
            cleaned_meta = {k: v for k, v in meta.items() if v is not None}
            cleaned_metadatas.append(cleaned_meta)

        # Add documents in batches (ChromaDB batch size limit)
        batch_size = 100
        total_added = 0

        for i in range(0, len(ids), batch_size):
            batch_ids = ids[i:i + batch_size]
            batch_docs = documents[i:i + batch_size]
            batch_meta = cleaned_metadatas[i:i + batch_size]

            collection.add(
                ids=batch_ids,
                documents=batch_docs,
                metadatas=batch_meta
            )

            total_added += len(batch_ids)
            logger.debug(f"Added {total_added}/{len(ids)} documents to {collection_name}")

        logger.info(f"✓ Populated {collection_name} with {total_added} documents")

        return {
            "collection_name": collection_name,
            "total_documents": total_added,
            "batch_size": batch_size
        }

    def query_collection(
        self,
        collection_name: str,
        query_text: str,
        n_results: int = 5,
        where: Optional[Dict[str, Any]] = None,
        where_document: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Query a collection.

        Args:
            collection_name: Name of collection
            query_text: Query text (will be embedded)
            n_results: Number of results to return
            where: Metadata filter (e.g., {"brand": "LG"})
            where_document: Document text filter

        Returns:
            Query results with embeddings, distances, and metadata
        """
        if collection_name not in self.collections:
            raise ValueError(f"Collection {collection_name} not found")

        collection = self.collections[collection_name]

        results = collection.query(
            query_texts=[query_text],
            n_results=n_results,
            where=where,
            where_document=where_document,
            include=["embeddings", "documents", "metadatas", "distances"]
        )

        return results

    def get_collection_count(self, collection_name: str) -> int:
        """Get number of documents in collection."""
        if collection_name not in self.collections:
            return 0

        return self.collections[collection_name].count()

    def get_collection_stats(self) -> Dict[str, int]:
        """Get stats for all collections."""
        return {
            name: collection.count()
            for name, collection in self.collections.items()
        }

    def persist(self):
        """Persist collections to disk (automatic with PersistentClient)."""
        logger.info("ChromaDB data is automatically persisted to disk")

    def reset_collection(self, collection_name: str):
        """Delete and reset a collection."""
        if collection_name in self.collections:
            self.client.delete_collection(name=collection_name)
            del self.collections[collection_name]
            logger.info(f"Reset collection: {collection_name}")

    def reset_all(self):
        """Delete all collections."""
        for collection_name in list(self.collections.keys()):
            self.reset_collection(collection_name)
        logger.info("Reset all collections")


def initialize_chroma_with_processed_data(
    processed_data_dir: str,
    persist_directory: str = "data/chroma_db",
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2",
    skip_existing: bool = False
) -> ChromaDBManager:
    """
    Initialize ChromaDB and populate with processed data.

    Args:
        processed_data_dir: Directory containing processed JSON files
        persist_directory: Where to persist ChromaDB
        embedding_model: Embedding model to use
        skip_existing: Skip if collections already exist

    Returns:
        Initialized ChromaDBManager
    """
    manager = ChromaDBManager(persist_directory, embedding_model)

    # List of collections to create
    collections = [
        "parts_refrigerator",
        "parts_dishwasher",
        "blogs_articles",
        "repair_symptoms"
    ]

    import json

    for collection_name in collections:
        # Check if collection already exists
        if skip_existing and manager.get_collection_count(collection_name) > 0:
            logger.info(f"Skipping existing collection: {collection_name}")
            continue

        # Load processed data
        data_path = f"{processed_data_dir}/{collection_name}.json"
        try:
            with open(data_path, 'r', encoding='utf-8') as f:
                processed_data = json.load(f)
        except FileNotFoundError:
            logger.warning(f"Data file not found: {data_path}")
            continue

        # Create collection
        manager.create_collection(collection_name)

        # Populate collection
        manager.populate_collection(
            collection_name,
            processed_data["ids"],
            processed_data["documents"],
            processed_data["metadatas"]
        )

    # Persist to disk
    manager.persist()

    logger.info("=" * 60)
    logger.info("ChromaDB INITIALIZATION COMPLETE")
    logger.info("=" * 60)
    stats = manager.get_collection_stats()
    for collection_name, count in stats.items():
        logger.info(f"{collection_name}: {count} documents")

    return manager
