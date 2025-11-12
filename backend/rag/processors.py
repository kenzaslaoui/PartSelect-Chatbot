"""
Data processors for converting raw scraped data into ChromaDB documents.

This module handles:
- Parts collection processing (no chunking)
- Blog collection processing (chunking by section)
- Repair symptoms collection processing (chunking by part + repair guide)
"""

import json
import logging
from typing import List, Dict, Any, Optional
from pathlib import Path

from .chunking import chunk_text, estimate_tokens

logger = logging.getLogger(__name__)


class PartsProcessor:
    """Process parts catalog data into ChromaDB documents."""

    def process(self, parts_data: Dict[str, Any], appliance_type: str) -> Dict[str, Any]:
        """
        Convert parts data to ChromaDB format.

        Args:
            parts_data: Raw parts data from scrapers
            appliance_type: "refrigerator" or "dishwasher"

        Returns:
            Dict with 'ids', 'documents', 'metadatas' for ChromaDB
        """
        documents = parts_data.get("documents", [])
        filtered = [d for d in documents if d.get("appliance_type") == appliance_type]

        logger.info(f"Processing {len(filtered)} {appliance_type} parts")

        ids = []
        docs = []
        metadatas = []

        for i, part in enumerate(filtered, 1):
            part_id = f"part_{i:05d}"

            # Document text: combination of title, description, and specs
            doc_text = self._create_document_text(part)

            # Metadata: structured data for filtering
            metadata = self._create_metadata(part)

            ids.append(part_id)
            docs.append(doc_text)
            metadatas.append(metadata)

        return {
            "ids": ids,
            "documents": docs,
            "metadatas": metadatas,
            "stats": {
                "total_parts": len(filtered),
                "appliance_type": appliance_type
            }
        }

    def _create_document_text(self, part: Dict[str, Any]) -> str:
        """Create searchable document text from part."""
        elements = []

        # Title
        if part.get("title"):
            elements.append(part["title"])

        # Product description
        if part.get("product_description"):
            elements.append(part["product_description"])

        # Brand and type info
        if part.get("brand"):
            elements.append(f"Brand: {part['brand']}")
        if part.get("part_type"):
            elements.append(f"Type: {part['part_type']}")
        if part.get("machine_type"):
            elements.append(f"Machine: {part['machine_type']}")

        # Installation info
        if part.get("installation_type"):
            elements.append(f"Installation: {part['installation_type']}")
        if part.get("average_installation_time"):
            elements.append(f"Time: {part['average_installation_time']}")

        # Customer reviews (summary)
        if part.get("average_customer_rating"):
            elements.append(f"Rating: {part['average_customer_rating']} stars")
        if part.get("review_count"):
            elements.append(f"Based on {part['review_count']} reviews")

        # Part numbers
        if part.get("partselect_number"):
            elements.append(f"PartSelect: {part['partselect_number']}")
        if part.get("manufacturer_number"):
            elements.append(f"Manufacturer: {part['manufacturer_number']}")

        return ". ".join(filter(None, elements))

    def _create_metadata(self, part: Dict[str, Any]) -> Dict[str, Any]:
        """Create metadata dict for ChromaDB filtering."""
        metadata = {
            "id": part.get("id"),
            "source": "parts_catalog",
            "appliance_type": part.get("appliance_type"),
            "brand": part.get("brand"),
            "manufacturer": part.get("manufacturer"),
            "part_type": part.get("part_type"),
            "title": part.get("title"),
            "url": part.get("url"),
            "partselect_number": part.get("partselect_number"),
            "manufacturer_number": part.get("manufacturer_number"),
            "price": part.get("price"),
            "stock_status": part.get("stock_status", "unknown"),
            "installation_type": part.get("installation_type"),
            "average_installation_time": part.get("average_installation_time"),
            "average_customer_rating": part.get("average_customer_rating"),
            "review_count": part.get("review_count", 0)
        }
        # ChromaDB only supports str, int, float, bool, None - remove complex types
        return {k: v for k, v in metadata.items() if isinstance(v, (str, int, float, bool, type(None)))}


class BlogsProcessor:
    """Process blog articles into ChromaDB documents with chunking."""

    def process(
        self,
        blogs_data: Dict[str, Any],
        max_tokens: int = 512,
        overlap_tokens: int = 100
    ) -> Dict[str, Any]:
        """
        Convert blog data to ChromaDB format with chunking.

        Args:
            blogs_data: Raw blog data from scrapers
            max_tokens: Max tokens per chunk
            overlap_tokens: Overlap between chunks

        Returns:
            Dict with 'ids', 'documents', 'metadatas' for ChromaDB
        """
        documents = blogs_data.get("documents", [])
        logger.info(f"Processing {len(documents)} blog articles")

        ids = []
        docs = []
        metadatas = []
        chunk_counter = 0

        for blog in documents:
            # Extract content
            content_text = blog.get("content_text", "")
            if not content_text or estimate_tokens(content_text) < 50:
                logger.debug(f"Skipping short blog: {blog.get('title')}")
                continue

            # Chunk the content
            chunks = chunk_text(content_text, max_tokens, overlap_tokens)

            for chunk in chunks:
                chunk_counter += 1
                chunk_id = f"blog_{chunk_counter:05d}"

                # Document text with context
                doc_text = self._create_document_text(blog, chunk)

                # Metadata
                metadata = self._create_metadata(blog, chunk)

                ids.append(chunk_id)
                docs.append(doc_text)
                metadatas.append(metadata)

        return {
            "ids": ids,
            "documents": docs,
            "metadatas": metadatas,
            "stats": {
                "total_blogs": len(documents),
                "total_chunks": len(ids),
                "avg_chunks_per_blog": len(ids) / len(documents) if documents else 0
            }
        }

    def _create_document_text(self, blog: Dict[str, Any], chunk: Any) -> str:
        """Create searchable document text from blog chunk."""
        elements = []

        # Title
        if blog.get("title"):
            elements.append(f"Title: {blog['title']}")

        # Subtitle
        if blog.get("subtitle"):
            elements.append(f"Subtitle: {blog['subtitle']}")

        # The actual chunk content
        elements.append(chunk.text)

        return ". ".join(filter(None, elements))

    def _create_metadata(self, blog: Dict[str, Any], chunk: Any) -> Dict[str, Any]:
        """Create metadata dict for ChromaDB filtering."""
        metadata = {
            "id": blog.get("id"),
            "chunk_number": chunk.chunk_number,
            "total_chunks": chunk.total_chunks,
            "source": "blog_article",
            "appliance_type": blog.get("appliance_type"),
            "brand": blog.get("brand"),
            "title": blog.get("title"),
            "url": blog.get("url"),
            "topic_category": blog.get("topic_category"),
            "has_images": bool(blog.get("images")),
            "has_videos": bool(blog.get("videos"))
        }
        # ChromaDB only supports str, int, float, bool, None - remove complex types
        return {k: v for k, v in metadata.items() if isinstance(v, (str, int, float, bool, type(None)))}


class RepairProcessor:
    """Process repair symptom guides into ChromaDB documents with chunking."""

    def process(self, repair_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Convert repair symptom data to ChromaDB format with chunking.

        Each part description (especially those with repair guides)
        becomes a separate chunk for precise retrieval.

        Args:
            repair_data: Raw repair data from scrapers

        Returns:
            Dict with 'ids', 'documents', 'metadatas' for ChromaDB
        """
        documents = repair_data.get("documents", [])
        logger.info(f"Processing {len(documents)} repair symptom guides")

        ids = []
        docs = []
        metadatas = []
        chunk_counter = 0

        for repair in documents:
            parts = repair.get("parts", [])

            for part_idx, part in enumerate(parts, 1):
                # Each part description = base chunk
                if part.get("description"):
                    chunk_counter += 1
                    chunk_id = f"repair_{chunk_counter:05d}"

                    # Document text: part description + inspection steps
                    doc_text = self._create_document_text(repair, part, None)
                    metadata = self._create_metadata(repair, part, None)

                    ids.append(chunk_id)
                    docs.append(doc_text)
                    metadatas.append(metadata)

                # Each repair guide = additional chunk
                repair_guides = part.get("repair_guides") or []
                for guide_idx, guide in enumerate(repair_guides, 1):
                    chunk_counter += 1
                    chunk_id = f"repair_{chunk_counter:05d}"

                    # Document text: part description + guide content
                    doc_text = self._create_document_text(repair, part, guide)
                    metadata = self._create_metadata(repair, part, guide)

                    ids.append(chunk_id)
                    docs.append(doc_text)
                    metadatas.append(metadata)

        return {
            "ids": ids,
            "documents": docs,
            "metadatas": metadatas,
            "stats": {
                "total_symptoms": len(documents),
                "total_chunks": len(ids)
            }
        }

    def _create_document_text(
        self,
        repair: Dict[str, Any],
        part: Dict[str, Any],
        guide: Optional[Dict[str, Any]]
    ) -> str:
        """Create searchable document text from repair chunk."""
        elements = []

        # Symptom info
        if repair.get("symptom_name"):
            elements.append(f"Symptom: {repair['symptom_name']}")

        if repair.get("appliance_type"):
            elements.append(f"Appliance: {repair['appliance_type']}")

        if repair.get("difficulty"):
            elements.append(f"Difficulty: {repair['difficulty']}")

        # Part description
        if part.get("name"):
            elements.append(f"Part: {part['name']}")

        if part.get("description"):
            elements.append(f"Description: {part['description']}")

        # Repair guide content (if provided)
        if guide:
            if guide.get("title"):
                elements.append(f"Guide: {guide['title']}")

            if guide.get("content"):
                elements.append(f"Steps: {guide['content']}")

        # Inspection steps (from repair data)
        inspection_steps = repair.get("inspection_steps", [])
        if inspection_steps:
            for step_info in inspection_steps:
                if step_info.get("part_name") == part.get("name"):
                    steps = step_info.get("steps", [])
                    if steps:
                        elements.append("Inspection Steps: " + " ".join(steps))
                    break

        # Video info
        if repair.get("video"):
            video_url = repair["video"].get("video_url", "")
            if video_url:
                elements.append(f"Video Tutorial: {video_url}")

        return ". ".join(filter(None, elements))

    def _create_metadata(
        self,
        repair: Dict[str, Any],
        part: Dict[str, Any],
        guide: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Create metadata dict for ChromaDB filtering."""
        metadata = {
            "id": repair.get("id"),
            "source": "repair_symptom",
            "appliance_type": repair.get("appliance_type"),
            "symptom_name": repair.get("symptom_name"),
            "url": repair.get("url"),
            "difficulty": repair.get("difficulty"),
            "part_name": part.get("name"),
            "has_video": bool(repair.get("video")),
        }

        # Add video info if present
        if repair.get("video"):
            metadata["video_id"] = repair["video"].get("video_id")
            metadata["video_url"] = repair["video"].get("video_url")
            metadata["video_thumbnail"] = repair["video"].get("thumbnail_url")

        # Add guide info if this is a guide chunk
        if guide:
            metadata["repair_guide_type"] = "test" if "test" in guide.get("title", "").lower() else "replacement"
            metadata["repair_guide_title"] = guide.get("title")
            metadata["repair_guide_url"] = guide.get("url")

        # ChromaDB only supports str, int, float, bool, None - remove complex types
        return {k: v for k, v in metadata.items() if isinstance(v, (str, int, float, bool, type(None)))}


def load_raw_data(filepath: str) -> Dict[str, Any]:
    """Load raw JSON data from scrapers."""
    with open(filepath, 'r', encoding='utf-8') as f:
        return json.load(f)


def process_all_collections(
    parts_raw_path: str,
    blogs_raw_path: str,
    repair_raw_path: str,
    output_dir: str = "data/processed"
) -> Dict[str, Dict[str, Any]]:
    """
    Process all data collections and save to disk.

    Args:
        parts_raw_path: Path to parts raw data
        blogs_raw_path: Path to blogs raw data
        repair_raw_path: Path to repair raw data
        output_dir: Output directory for processed data

    Returns:
        Dict with processed collections
    """
    Path(output_dir).mkdir(parents=True, exist_ok=True)

    results = {}

    # Process parts
    logger.info("=" * 60)
    logger.info("PROCESSING PARTS DATA")
    logger.info("=" * 60)
    parts_data = load_raw_data(parts_raw_path)
    parts_processor = PartsProcessor()

    parts_fridge = parts_processor.process(parts_data, "refrigerator")
    results["parts_refrigerator"] = parts_fridge
    logger.info(f"✓ Processed {parts_fridge['stats']['total_parts']} refrigerator parts")

    parts_dw = parts_processor.process(parts_data, "dishwasher")
    results["parts_dishwasher"] = parts_dw
    logger.info(f"✓ Processed {parts_dw['stats']['total_parts']} dishwasher parts")

    # Process blogs
    logger.info("\n" + "=" * 60)
    logger.info("PROCESSING BLOG DATA")
    logger.info("=" * 60)
    blogs_data = load_raw_data(blogs_raw_path)
    blogs_processor = BlogsProcessor()
    blogs_result = blogs_processor.process(blogs_data)
    results["blogs_articles"] = blogs_result
    logger.info(f"✓ Processed {blogs_result['stats']['total_blogs']} blogs into {blogs_result['stats']['total_chunks']} chunks")

    # Process repair symptoms
    logger.info("\n" + "=" * 60)
    logger.info("PROCESSING REPAIR SYMPTOM DATA")
    logger.info("=" * 60)
    repair_data = load_raw_data(repair_raw_path)
    repair_processor = RepairProcessor()
    repair_result = repair_processor.process(repair_data)
    results["repair_symptoms"] = repair_result
    logger.info(f"✓ Processed {repair_result['stats']['total_symptoms']} symptoms into {repair_result['stats']['total_chunks']} chunks")

    # Save processed data
    logger.info("\n" + "=" * 60)
    logger.info("SAVING PROCESSED DATA")
    logger.info("=" * 60)
    for collection_name, collection_data in results.items():
        output_path = f"{output_dir}/{collection_name}.json"
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(collection_data, f, indent=2, ensure_ascii=False)
        logger.info(f"✓ Saved {collection_name} to {output_path}")

    return results
