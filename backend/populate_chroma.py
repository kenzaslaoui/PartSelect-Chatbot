"""
Main script to populate ChromaDB with processed data.

This script orchestrates the complete RAG pipeline:
1. Load raw scraped data
2. Process data (chunk, add metadata)
3. Initialize ChromaDB with HNSW
4. Populate collections with embeddings

Usage:
    python populate_chroma.py
"""

import sys
import logging
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent))

from rag.processors import process_all_collections
from rag.chroma_db import initialize_chroma_with_processed_data

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('backend/rag.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)


def main():
    """Execute RAG pipeline."""
    logger.info("=" * 80)
    logger.info("PARTSELECT RAG PIPELINE - CHROMADB POPULATION")
    logger.info("=" * 80)

    # Paths
    parts_raw = "data/raw/parts_raw.json"
    blogs_raw = "data/raw/blogs_raw.json"
    repair_raw = "data/raw/repair_symptoms_raw.json"

    processed_dir = "data/processed"
    chroma_dir = "data/chroma_db"

    # Step 1: Process raw data
    logger.info("\nSTEP 1: Processing raw data into vectorizable documents...")
    logger.info("-" * 80)

    try:
        processed = process_all_collections(
            parts_raw_path=parts_raw,
            blogs_raw_path=blogs_raw,
            repair_raw_path=repair_raw,
            output_dir=processed_dir
        )
        logger.info("✓ Data processing complete!")
    except Exception as e:
        logger.error(f"✗ Error during data processing: {e}")
        raise

    # Step 2: Initialize ChromaDB and populate collections
    logger.info("\nSTEP 2: Initializing ChromaDB and populating collections...")
    logger.info("-" * 80)

    try:
        chroma_manager = initialize_chroma_with_processed_data(
            processed_data_dir=processed_dir,
            persist_directory=chroma_dir,
            embedding_model="sentence-transformers/all-MiniLM-L6-v2",
            skip_existing=False
        )
        logger.info("✓ ChromaDB population complete!")
    except Exception as e:
        logger.error(f"✗ Error during ChromaDB initialization: {e}")
        raise

    # Step 3: Summary
    logger.info("\n" + "=" * 80)
    logger.info("PIPELINE COMPLETE!")
    logger.info("=" * 80)

    stats = chroma_manager.get_collection_stats()
    logger.info("\nCollection Statistics:")
    for collection_name, count in stats.items():
        logger.info(f"  {collection_name}: {count} documents")

    total_docs = sum(stats.values())
    logger.info(f"\nTotal documents indexed: {total_docs}")

    logger.info("\nNext steps:")
    logger.info("1. Test retrieval with test_chroma_retrieval.py")
    logger.info("2. Build agent orchestrator")
    logger.info("3. Integrate Deepseek LLM")
    logger.info("4. Build FastAPI backend")
    logger.info("5. Build React frontend")

    return chroma_manager


if __name__ == "__main__":
    try:
        chroma_manager = main()
        logger.info("\n✓ Pipeline execution successful!")
    except Exception as e:
        logger.error(f"\n✗ Pipeline execution failed: {e}", exc_info=True)
        sys.exit(1)
