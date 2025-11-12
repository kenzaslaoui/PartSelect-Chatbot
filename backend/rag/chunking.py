"""
Chunking utilities for splitting documents into embeddings-friendly chunks.

This module provides functions for:
- Splitting text by tokens (semantic units)
- Creating overlapping chunks
- Preserving context across chunks
"""

import re
from typing import List, Tuple
from dataclasses import dataclass


@dataclass
class Chunk:
    """Represents a single text chunk with metadata."""
    text: str
    chunk_number: int
    total_chunks: int
    start_position: int
    end_position: int


def estimate_tokens(text: str) -> int:
    """
    Rough estimate of token count (for planning chunk sizes).

    Using simple heuristic: ~4 characters = 1 token
    More accurate for sentence-transformers models.

    Args:
        text: Text to estimate

    Returns:
        Estimated token count
    """
    return len(text) // 4


def split_into_sentences(text: str) -> List[str]:
    """
    Split text into sentences while preserving periods.

    Args:
        text: Text to split

    Returns:
        List of sentences
    """
    # Split on sentence boundaries
    sentences = re.split(r'(?<=[.!?])\s+', text.strip())
    return [s.strip() for s in sentences if s.strip()]


def split_into_paragraphs(text: str) -> List[str]:
    """
    Split text into paragraphs.

    Args:
        text: Text to split

    Returns:
        List of paragraphs
    """
    paragraphs = text.split('\n\n')
    return [p.strip() for p in paragraphs if p.strip()]


def chunk_text(
    text: str,
    max_tokens: int = 512,
    overlap_tokens: int = 100,
    method: str = "sentence"
) -> List[Chunk]:
    """
    Split text into chunks with optional overlap.

    Args:
        text: Text to chunk
        max_tokens: Maximum tokens per chunk (~4 chars = 1 token)
        overlap_tokens: Number of tokens to overlap between chunks
        method: "sentence" or "paragraph"

    Returns:
        List of Chunk objects
    """
    if not text or not text.strip():
        return []

    # Choose split method
    if method == "paragraph":
        units = split_into_paragraphs(text)
    else:  # sentence
        units = split_into_sentences(text)

    if not units:
        return [Chunk(
            text=text,
            chunk_number=1,
            total_chunks=1,
            start_position=0,
            end_position=len(text)
        )]

    # Build chunks
    chunks_list = []
    current_chunk = ""
    current_tokens = 0
    overlap_buffer = ""
    overlap_tokens_count = 0
    start_pos = 0

    for unit in units:
        unit_tokens = estimate_tokens(unit)

        # If adding this unit would exceed max, save current chunk
        if current_tokens + unit_tokens > max_tokens and current_chunk:
            # Save chunk
            chunks_list.append({
                "text": current_chunk.strip(),
                "start_pos": start_pos,
                "end_pos": start_pos + len(current_chunk)
            })

            # Prepare overlap for next chunk
            if overlap_tokens > 0:
                overlap_buffer = current_chunk
                overlap_tokens_count = min(overlap_tokens, current_tokens)
                # Trim overlap buffer to approximate token count
                if overlap_tokens_count < current_tokens:
                    trimmed = trim_to_tokens(overlap_buffer, overlap_tokens_count)
                    overlap_buffer = trimmed

            # Start new chunk with overlap
            current_chunk = overlap_buffer
            current_tokens = overlap_tokens_count
            start_pos = max(0, start_pos + len(overlap_buffer))

        # Add unit to current chunk
        current_chunk += unit + " "
        current_tokens += unit_tokens

    # Add final chunk
    if current_chunk.strip():
        chunks_list.append({
            "text": current_chunk.strip(),
            "start_pos": start_pos,
            "end_pos": start_pos + len(current_chunk)
        })

    # Convert to Chunk objects with numbering
    total = len(chunks_list)
    chunks = []
    for i, chunk_data in enumerate(chunks_list, 1):
        chunks.append(Chunk(
            text=chunk_data["text"],
            chunk_number=i,
            total_chunks=total,
            start_position=chunk_data["start_pos"],
            end_position=chunk_data["end_pos"]
        ))

    return chunks


def trim_to_tokens(text: str, target_tokens: int) -> str:
    """
    Trim text to approximately target number of tokens.

    Args:
        text: Text to trim
        target_tokens: Target token count

    Returns:
        Trimmed text
    """
    target_chars = target_tokens * 4
    if len(text) <= target_chars:
        return text

    # Trim and find last sentence boundary
    trimmed = text[:target_chars]
    last_period = max(
        trimmed.rfind('.'),
        trimmed.rfind('!'),
        trimmed.rfind('?')
    )

    if last_period > 0:
        return trimmed[:last_period + 1]

    return trimmed


def chunk_by_sections(
    text: str,
    section_headers: List[str] = None,
    max_tokens: int = 512,
    overlap_tokens: int = 100
) -> Tuple[List[Chunk], dict]:
    """
    Chunk text by logical sections (with headers).

    Args:
        text: Full text
        section_headers: List of section header texts to split on
        max_tokens: Max tokens per chunk
        overlap_tokens: Overlap between chunks

    Returns:
        Tuple of (chunks, section_mapping)
    """
    chunks_list = []
    section_mapping = {}

    if not section_headers:
        # Fall back to regular chunking
        return chunk_text(text, max_tokens, overlap_tokens), {}

    # Split by sections
    sections = []
    current_pos = 0

    for header in section_headers:
        idx = text.find(header, current_pos)
        if idx >= 0:
            sections.append({
                "header": header,
                "start": idx,
                "position": len(sections)
            })
            current_pos = idx + len(header)

    # Extract section content
    for i, section_info in enumerate(sections):
        start = section_info["start"]
        end = sections[i + 1]["start"] if i + 1 < len(sections) else len(text)
        section_content = text[start:end]

        # Chunk each section
        section_chunks = chunk_text(section_content, max_tokens, overlap_tokens)

        for chunk in section_chunks:
            chunk.start_position = start + chunk.start_position
            chunk.end_position = start + chunk.end_position
            chunks_list.append(chunk)

            section_mapping[len(chunks_list) - 1] = {
                "section_header": section_info["header"],
                "section_position": section_info["position"]
            }

    return chunks_list, section_mapping
