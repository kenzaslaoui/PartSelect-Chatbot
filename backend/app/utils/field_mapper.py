"""
Field mapping utility for converting retriever results to API response schemas.

Maps database/retriever field names to the expected API schema field names.
"""

from typing import Dict, Any, Optional


# Field name mappings from retriever results to API schemas
PART_FIELD_MAPPING = {
    # From retriever/agent → To API schema
    "id": "id",
    "partselect_number": "part_number",
    "part_number": "part_number",
    "title": "name",
    "name": "name",
    "url": "url",
    "price": "price",
    "average_customer_rating": "rating",
    "rating": "rating",
    "review_count": "review_count",
    "stock_status": "stock_status",
    "relevance_score": "similarity_score",
    "score": "similarity_score",
    "appliance_type": "appliance_type",
    "manufacturer": "manufacturer",
    "compatibility_models": "compatible_models",
    "compatible_models": "compatible_models",
}

BLOG_FIELD_MAPPING = {
    # From retriever/agent → To API schema
    "id": "id",
    "title": "name",
    "name": "name",
    "url": "url",
    "relevance_score": "similarity_score",
    "score": "similarity_score",
    "appliance_type": "appliance_type",
    "topic_category": "topic",
    "has_images": "has_images",
    "has_videos": "has_videos",
}

REPAIR_FIELD_MAPPING = {
    # From retriever/agent → To API schema
    "id": "id",
    "symptom": "name",
    "symptom_name": "name",
    "title": "name",
    "url": "url",
    "relevance_score": "similarity_score",
    "score": "similarity_score",
    "appliance_type": "appliance_type",
    "difficulty": "difficulty",
    "has_video": "has_video",
    "video_url": "video_url",
    "video_id": "video_id",
    "part_name": "related_part",
}


def map_part_data(retriever_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Map retriever part data to Part schema format.

    Args:
        retriever_data: Raw data from part retriever

    Returns:
        Mapped data ready for Part schema
    """
    mapped = {}

    # Extract required fields
    for retriever_field, schema_field in PART_FIELD_MAPPING.items():
        if retriever_field in retriever_data:
            value = retriever_data[retriever_field]
            if value is not None:
                mapped[schema_field] = value

    # Set defaults for required schema fields
    if "name" not in mapped:
        mapped["name"] = mapped.get("part_number", "Unknown Part")
    if "url" not in mapped:
        mapped["url"] = ""
    if "similarity_score" not in mapped:
        mapped["similarity_score"] = 0.0

    # Store all extra data in metadata
    metadata = {}
    for key, value in retriever_data.items():
        schema_key = PART_FIELD_MAPPING.get(key, key)
        if schema_key not in mapped:  # Don't duplicate
            metadata[key] = value

    if metadata:
        mapped["metadata"] = metadata

    return mapped


def map_blog_data(retriever_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Map retriever blog data to Blog schema format.

    Args:
        retriever_data: Raw data from blog retriever

    Returns:
        Mapped data ready for Blog schema
    """
    mapped = {}

    # Extract required fields
    for retriever_field, schema_field in BLOG_FIELD_MAPPING.items():
        if retriever_field in retriever_data:
            value = retriever_data[retriever_field]
            if value is not None:
                mapped[schema_field] = value

    # Set defaults for required schema fields
    if "name" not in mapped:
        mapped["name"] = mapped.get("title", "Blog Article")
    if "url" not in mapped:
        mapped["url"] = ""
    if "similarity_score" not in mapped:
        mapped["similarity_score"] = 0.0

    # Store all extra data in metadata
    metadata = {}
    for key, value in retriever_data.items():
        schema_key = BLOG_FIELD_MAPPING.get(key, key)
        if schema_key not in mapped:  # Don't duplicate
            metadata[key] = value

    if metadata:
        mapped["metadata"] = metadata

    return mapped


def map_repair_data(retriever_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Map retriever repair data to Repair schema format.

    Args:
        retriever_data: Raw data from repair retriever

    Returns:
        Mapped data ready for Repair schema
    """
    mapped = {}

    # Extract required fields
    for retriever_field, schema_field in REPAIR_FIELD_MAPPING.items():
        if retriever_field in retriever_data:
            value = retriever_data[retriever_field]
            if value is not None:
                mapped[schema_field] = value

    # Set defaults for required schema fields
    if "name" not in mapped:
        mapped["name"] = mapped.get("symptom", "Repair Guide")
    if "url" not in mapped:
        mapped["url"] = ""
    if "similarity_score" not in mapped:
        mapped["similarity_score"] = 0.0

    # Store all extra data in metadata
    metadata = {}
    for key, value in retriever_data.items():
        schema_key = REPAIR_FIELD_MAPPING.get(key, key)
        if schema_key not in mapped:  # Don't duplicate
            metadata[key] = value

    if metadata:
        mapped["metadata"] = metadata

    return mapped
