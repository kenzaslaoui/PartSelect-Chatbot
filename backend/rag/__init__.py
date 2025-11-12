"""
RAG (Retrieval-Augmented Generation) module for PartSelect chat agent.

This module provides:
- Document chunking and processing
- ChromaDB initialization and management
- Data processors for different data types
- Agent-specific retrieval interfaces
"""

from .chunking import chunk_text, Chunk
from .processors import (
    PartsProcessor,
    BlogsProcessor,
    RepairProcessor,
    process_all_collections,
    load_raw_data
)
from .chroma_db import ChromaDBManager, initialize_chroma_with_processed_data
from .retrieval import (
    PartSearchRetriever,
    CompatibilityRetriever,
    TroubleshootingRetriever,
    InstallationRetriever,
    retrieve_parts,
    retrieve_compatibility_info,
    retrieve_troubleshooting_info,
    retrieve_installation_guide
)

__all__ = [
    "chunk_text",
    "Chunk",
    "PartsProcessor",
    "BlogsProcessor",
    "RepairProcessor",
    "process_all_collections",
    "load_raw_data",
    "ChromaDBManager",
    "initialize_chroma_with_processed_data",
    "PartSearchRetriever",
    "CompatibilityRetriever",
    "TroubleshootingRetriever",
    "InstallationRetriever",
    "retrieve_parts",
    "retrieve_compatibility_info",
    "retrieve_troubleshooting_info",
    "retrieve_installation_guide"
]
