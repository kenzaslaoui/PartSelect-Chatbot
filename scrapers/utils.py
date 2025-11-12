"""
Utility functions for PartSelect scrapers.

This module provides shared helper functions used across different scrapers
for data extraction, validation, text processing, and file I/O operations.

Functions are organized by category:
- Brand extraction (shared)
- Part number extraction (shared)
- Appliance type detection (shared)
- Text processing (shared)
- Video extraction (format-specific helpers)
- URL handling (shared)
- Data validation (shared)
- File operations (shared)
- Timestamp utilities (shared)
- Progress tracking (shared)
"""

import re
import json
import logging
from datetime import datetime
from typing import Optional, List, Dict, Any
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup
from pathlib import Path

# Import configuration
from .config import (
    BRAND_PATTERNS,
    BRANDS,
    REFRIGERATOR_KEYWORDS,
    DISHWASHER_KEYWORDS,
    PARTSELECT_NUMBER_PATTERN,
    MANUFACTURER_NUMBER_PATTERN,
    MAX_CONTENT_LENGTH,
    MIN_CONTENT_LENGTH,
    VALID_IMAGE_EXTENSIONS,
    VIDEO_PLATFORMS,
    REQUIRED_BLOG_FIELDS,
    DOC_ID_PREFIXES
)

# Set up logging
logger = logging.getLogger(__name__)


# BRAND EXTRACTION

def extract_brand(text: str) -> Optional[str]:
    """
    Extract appliance brand from text (title, description, or content).

    Uses the BRAND_PATTERNS dictionary to match canonical brand names
    and their variations. Case-insensitive matching.

    Args:
        text: Text to search for brand names (e.g., article title)

    Returns:
        str: Canonical brand name if found (e.g., "KitchenAid")
        None: If no brand is detected

    Examples:
        >>> extract_brand("How to Fix Your LG Refrigerator")
        'LG'
        >>> extract_brand("KitchenAid Dishwasher Repair Guide")
        'KitchenAid'
        >>> extract_brand("Generic repair tips")
        None
    """
    if not text:
        return None

    text_lower = text.lower()

    # Iterate through brand patterns (canonical name -> variations)
    for canonical_brand, variations in BRAND_PATTERNS.items():
        for variation in variations:
            if variation.lower() in text_lower:
                logger.debug(f"Brand '{canonical_brand}' detected via pattern '{variation}'")
                return canonical_brand

    logger.debug(f"No brand detected in text: {text[:50]}...")
    return None


def extract_multiple_brands(text: str) -> List[str]:
    """
    Extract all brands mentioned in text (some articles cover multiple brands).

    Args:
        text: Text to search

    Returns:
        list: List of unique brand names found

    Example:
        >>> extract_multiple_brands("LG and Samsung refrigerators")
        ['LG', 'Samsung']
    """
    if not text:
        return []

    text_lower = text.lower()
    found_brands = []

    for canonical_brand, variations in BRAND_PATTERNS.items():
        for variation in variations:
            if variation.lower() in text_lower:
                if canonical_brand not in found_brands:
                    found_brands.append(canonical_brand)
                break  # Move to next brand once found

    return found_brands


# PART NUMBER EXTRACTION

def extract_part_numbers(text: str, include_manufacturer: bool = True) -> Dict[str, List[str]]:
    """
    Extract part numbers from text (both PartSelect and manufacturer numbers).

    PartSelect numbers: PS followed by 6-10 digits (e.g., PS11752778)
    Manufacturer numbers: 2-4 letters + 6-15 alphanumeric chars (e.g., WPW10321304)

    Args:
        text: Text or HTML to search
        include_manufacturer: Whether to extract manufacturer part numbers

    Returns:
        dict: {
            'partselect': ['PS11752778', 'PS358591'],
            'manufacturer': ['WPW10321304', 'DA97-12650A']
        }

    Example:
        >>> extract_part_numbers("Replace PS11752778 with WPW10321304")
        {'partselect': ['PS11752778'], 'manufacturer': ['WPW10321304']}
    """
    if not text:
        return {'partselect': [], 'manufacturer': []}

    # Extract PartSelect numbers (PS######)
    partselect_numbers = re.findall(PARTSELECT_NUMBER_PATTERN, text)
    partselect_numbers = list(set(partselect_numbers))  # Remove duplicates

    # Extract manufacturer numbers if requested
    manufacturer_numbers = []
    if include_manufacturer:
        manufacturer_numbers = re.findall(MANUFACTURER_NUMBER_PATTERN, text)
        manufacturer_numbers = list(set(manufacturer_numbers))  # Remove duplicates

        # Filter out false positives (e.g., dates, model numbers that are too generic)
        # This is a heuristic and may need refinement
        manufacturer_numbers = [
            num for num in manufacturer_numbers
            if not re.match(r'^\d{4}-\d{2}-\d{2}$', num)  # Not a date
        ]

    logger.debug(f"Found {len(partselect_numbers)} PartSelect numbers, "
                f"{len(manufacturer_numbers)} manufacturer numbers")

    return {
        'partselect': sorted(partselect_numbers),
        'manufacturer': sorted(manufacturer_numbers)
    }


# APPLIANCE TYPE DETECTION

def extract_appliance_type(title: str, content: str = None) -> Optional[str]:
    """
    Determine appliance type from title (and optionally content).

    Priority order:
    1. Check title first (most reliable)
    2. If not found in title, check content (if provided)

    Args:
        title: Article/product title
        content: Optional content text for fallback detection

    Returns:
        str: 'refrigerator' or 'dishwasher'
        None: If neither type is detected

    Examples:
        >>> extract_appliance_type("How to Fix Your LG Refrigerator")
        'refrigerator'
        >>> extract_appliance_type("Dishwasher Not Cleaning Properly")
        'dishwasher'
    """
    # Check title first (most reliable)
    appliance_type = _detect_appliance_in_text(title)
    if appliance_type:
        return appliance_type

    # Fallback to content if provided
    if content:
        appliance_type = _detect_appliance_in_text(content)
        if appliance_type:
            logger.debug(f"Appliance type '{appliance_type}' detected in content (not title)")
            return appliance_type

    logger.debug(f"No appliance type detected in title: {title[:50]}...")
    return None


def _detect_appliance_in_text(text: str) -> Optional[str]:
    """
    Internal helper to detect appliance type in text.

    Args:
        text: Text to search

    Returns:
        str: 'refrigerator' or 'dishwasher' or None
    """
    if not text:
        return None

    text_lower = text.lower()

    # Check dishwasher keywords first (more specific)
    # This prevents false positives from general refrigerator keywords
    if any(keyword in text_lower for keyword in DISHWASHER_KEYWORDS):
        return 'dishwasher'

    # Check refrigerator keywords
    if any(keyword in text_lower for keyword in REFRIGERATOR_KEYWORDS):
        return 'refrigerator'

    return None


def is_relevant_article(title: str, content: str = None) -> bool:
    """
    Check if article is relevant (about refrigerators or dishwashers).

    This is the main filtering function used during scraping.

    Args:
        title: Article title
        content: Optional content for additional checking

    Returns:
        bool: True if article is about refrigerators or dishwashers

    Example:
        >>> is_relevant_article("LG Refrigerator Ice Maker Repair")
        True
        >>> is_relevant_article("Washing Machine Won't Spin")
        False
    """
    return extract_appliance_type(title, content) is not None


# TEXT PROCESSING

def strip_html(html: str, separator: str = ' ') -> str:
    """
    Convert HTML to plain text, removing all tags.

    Args:
        html: HTML string
        separator: String to use between elements (default: space)

    Returns:
        str: Plain text with HTML tags removed

    Example:
        >>> strip_html("<p>Hello <b>world</b></p>")
        'Hello world'
    """
    if not html:
        return ""

    soup = BeautifulSoup(html, 'html.parser')
    text = soup.get_text(separator=separator, strip=True)

    # Clean up excessive whitespace
    text = re.sub(r'\s+', ' ', text)

    return text.strip()


def truncate_text(text: str, max_length: int = MAX_CONTENT_LENGTH) -> str:
    """
    Truncate text to maximum length (prevent memory issues).

    Args:
        text: Text to truncate
        max_length: Maximum allowed length

    Returns:
        str: Truncated text with ellipsis if truncated
    """
    if not text or len(text) <= max_length:
        return text

    logger.warning(f"Truncating text from {len(text)} to {max_length} characters")
    return text[:max_length] + "..."


def extract_first_paragraph(html: str) -> str:
    """
    Extract the first paragraph from HTML content.

    Used for generating article summaries.

    Args:
        html: HTML content

    Returns:
        str: First paragraph text (plain text, no HTML)

    Example:
        >>> html = "<p>First para</p><p>Second para</p>"
        >>> extract_first_paragraph(html)
        'First para'
    """
    if not html:
        return ""

    soup = BeautifulSoup(html, 'html.parser')
    first_p = soup.find('p')

    if first_p:
        return first_p.get_text(strip=True)

    # Fallback: return first 200 chars of text
    text = strip_html(html)
    return text[:200] + "..." if len(text) > 200 else text


# VIDEO EXTRACTION

def extract_video_urls(html: str, base_url: str = "") -> List[str]:
    """
    Extract video URLs from HTML (YouTube, Vimeo, etc.).

    Used by blog scraper for standard iframe/video tag embeds.

    Args:
        html: HTML content
        base_url: Base URL for relative links

    Returns:
        list: List of video URLs

    Example:
        >>> html = '<iframe src="https://www.youtube.com/embed/abc123"></iframe>'
        >>> extract_video_urls(html)
        ['https://www.youtube.com/embed/abc123']
    """
    if not html:
        return []

    soup = BeautifulSoup(html, 'html.parser')
    video_urls = []

    # Find all iframes (common for embedded videos)
    for iframe in soup.find_all('iframe'):
        src = iframe.get('src', '')
        if src:
            # Make absolute URL
            if base_url:
                src = make_absolute_url(src, base_url)

            # Check if it's from a known video platform
            if any(platform in src.lower() for platform in VIDEO_PLATFORMS):
                video_urls.append(src)

    # Also check for <video> tags (self-hosted videos)
    for video in soup.find_all('video'):
        src = video.get('src', '')
        if src:
            if base_url:
                src = make_absolute_url(src, base_url)
            video_urls.append(src)

    return list(set(video_urls))  # Remove duplicates


def extract_youtube_id(html: str) -> Optional[str]:
    """
    Extract YouTube video ID from data-yt-init JSON attribute.

    Used by repair scraper for pages that store video info in data attributes.
    Format: <div data-yt-init='{"id":"VIDEO_ID"}'>

    Args:
        html: HTML string or BeautifulSoup element

    Returns:
        str: YouTube video ID (e.g., 'dQw4w9WgXcQ')
        None: If no video ID found

    Example:
        >>> html = '<div data-yt-init="{\\"id\\":\\"dQw4w9WgXcQ\\"}"></div>'
        >>> extract_youtube_id(html)
        'dQw4w9WgXcQ'
    """
    if not html:
        return None

    soup = BeautifulSoup(html, 'html.parser') if isinstance(html, str) else html

    # Find element with data-yt-init attribute
    video_elem = soup.find(attrs={'data-yt-init': True})
    if not video_elem:
        return None

    try:
        # Parse JSON from data-yt-init
        yt_data = video_elem.get('data-yt-init', '')
        yt_json = json.loads(yt_data)
        video_id = yt_json.get('id')

        if video_id:
            logger.debug(f"Extracted YouTube ID: {video_id}")
            return video_id

    except (json.JSONDecodeError, AttributeError) as e:
        logger.warning(f"Failed to parse YouTube data: {e}")

    return None


def extract_youtube_url(video_id: str) -> str:
    """
    Generate YouTube watch URL from video ID.

    Works with video IDs from any source (data attributes, URLs, etc.).

    Args:
        video_id: YouTube video ID

    Returns:
        str: Full YouTube URL

    Example:
        >>> extract_youtube_url('dQw4w9WgXcQ')
        'https://www.youtube.com/watch?v=dQw4w9WgXcQ'
    """
    if not video_id:
        return ""

    return f"https://www.youtube.com/watch?v={video_id}"


def extract_youtube_thumbnail(video_id: str) -> str:
    """
    Generate YouTube thumbnail URL from video ID.

    Uses maxresdefault for highest quality (1280x720).

    Args:
        video_id: YouTube video ID

    Returns:
        str: YouTube thumbnail URL

    Example:
        >>> extract_youtube_thumbnail('dQw4w9WgXcQ')
        'https://img.youtube.com/vi/dQw4w9WgXcQ/maxresdefault.jpg'
    """
    if not video_id:
        return ""

    return f"https://img.youtube.com/vi/{video_id}/maxresdefault.jpg"


# NUMERIC AND PATTERN EXTRACTION

def extract_difficulty(text: str) -> Optional[str]:
    """
    Extract difficulty level from text.

    Looks for difficulty indicators like "Time required:", "Easy", etc.
    General-purpose function useful across scrapers.

    Args:
        text: Text containing difficulty information

    Returns:
        str: Difficulty description (e.g., "Time required: 15 minutes or less")
        None: If no difficulty info found

    Example:
        >>> extract_difficulty("Time required: 15 minutes or less")
        'Time required: 15 minutes or less'
    """
    if not text:
        return None

    # Clean up whitespace
    text = re.sub(r'\s+', ' ', text.strip())

    # Common difficulty patterns
    difficulty_patterns = [
        r'Time required:.*?(?:\.|$)',
        r'Difficulty:.*?(?:\.|$)',
        r'(?:Easy|Medium|Hard|Intermediate).*?(?:\.|$)'
    ]

    for pattern in difficulty_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return match.group(0).strip()

    return None


def extract_number(text: str) -> Optional[int]:
    """
    Extract the first number from text.

    General-purpose function for extracting step numbers, counts, etc.

    Args:
        text: Text containing a number

    Returns:
        int: First number found in text
        None: If no number found

    Example:
        >>> extract_number("Step 1: Remove panel")
        1
        >>> extract_number("Replace 3 screws")
        3
    """
    if not text:
        return None

    match = re.search(r'\d+', text)
    if match:
        return int(match.group(0))

    return None


# URL HANDLING

def make_absolute_url(url: str, base_url: str) -> str:
    """
    Convert relative URL to absolute URL.

    Args:
        url: URL (can be relative or absolute)
        base_url: Base URL to resolve against

    Returns:
        str: Absolute URL

    Examples:
        >>> make_absolute_url("/blog/article/", "https://www.partselect.com")
        'https://www.partselect.com/blog/article/'
        >>> make_absolute_url("https://example.com/page", "https://www.partselect.com")
        'https://example.com/page'
    """
    if not url:
        return ""

    return urljoin(base_url, url)


def is_valid_image_url(url: str) -> bool:
    """
    Check if URL is a valid image URL.

    Args:
        url: URL to validate

    Returns:
        bool: True if URL has valid image extension

    Example:
        >>> is_valid_image_url("https://example.com/image.jpg")
        True
        >>> is_valid_image_url("https://example.com/page.html")
        False
    """
    if not url:
        return False

    parsed = urlparse(url.lower())
    path = parsed.path

    return any(path.endswith(ext) for ext in VALID_IMAGE_EXTENSIONS)


# DATA VALIDATION

def validate_document(doc: Dict[str, Any], doc_type: str = 'blog') -> tuple[bool, List[str]]:
    """
    Validate that document has all required fields.

    Args:
        doc: Document dictionary to validate
        doc_type: Type of document ('blog', 'part', etc.)

    Returns:
        tuple: (is_valid: bool, missing_fields: List[str])

    Example:
        >>> doc = {'title': 'Test', 'url': 'http://...', 'content_text': '...'}
        >>> is_valid, missing = validate_document(doc, 'blog')
        >>> is_valid
        False
        >>> missing
        ['appliance_type', 'topic_category']
    """
    # Get required fields for this document type
    if doc_type == 'blog':
        required_fields = REQUIRED_BLOG_FIELDS
    else:
        logger.warning(f"Unknown document type: {doc_type}")
        return True, []  # Don't block unknown types

    # Check for missing or empty fields
    missing_fields = []
    for field in required_fields:
        if field not in doc or not doc[field]:
            missing_fields.append(field)

    is_valid = len(missing_fields) == 0

    if not is_valid:
        logger.warning(f"Document validation failed. Missing fields: {missing_fields}")

    return is_valid, missing_fields


def validate_content_length(text: str) -> bool:
    """
    Check if content length is within acceptable range.

    Args:
        text: Content text

    Returns:
        bool: True if content length is valid
    """
    if not text:
        return False

    length = len(text)

    if length < MIN_CONTENT_LENGTH:
        logger.debug(f"Content too short: {length} chars (min: {MIN_CONTENT_LENGTH})")
        return False

    if length > MAX_CONTENT_LENGTH:
        logger.warning(f"Content too long: {length} chars (max: {MAX_CONTENT_LENGTH})")
        return False

    return True


# DOCUMENT ID GENERATION

def generate_document_id(prefix: str, index: int) -> str:
    """
    Generate unique document ID.

    Format: {prefix}_{index:04d}
    Example: blog_0001, blog_0042, part_0123

    Args:
        prefix: Document type prefix (e.g., 'blog', 'part')
        index: Document index (1-based)

    Returns:
        str: Formatted document ID

    Example:
        >>> generate_document_id('blog', 1)
        'blog_0001'
        >>> generate_document_id('part', 42)
        'part_0042'
    """
    return f"{prefix}_{index:04d}"


# TIMESTAMP UTILITIES

def get_timestamp() -> str:
    """
    Get current timestamp in ISO 8601 format.

    Returns:
        str: ISO formatted timestamp

    Example:
        >>> get_timestamp()
        '2024-11-11T14:23:45.123456'
    """
    return datetime.now().isoformat()


def get_date_string() -> str:
    """
    Get current date as YYYY-MM-DD string.

    Returns:
        str: Date string

    Example:
        >>> get_date_string()
        '2024-11-11'
    """
    return datetime.now().strftime('%Y-%m-%d')


# FILE OPERATIONS

def save_json(data: Dict[str, Any], filepath: str, indent: int = 2) -> bool:
    """
    Save data to JSON file with error handling.

    Args:
        data: Dictionary to save
        filepath: Path to output file
        indent: JSON indentation (default: 2 spaces)

    Returns:
        bool: True if successful, False otherwise
    """
    try:
        # Create directory if it doesn't exist
        Path(filepath).parent.mkdir(parents=True, exist_ok=True)

        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=indent, ensure_ascii=False)

        logger.info(f"Successfully saved data to {filepath}")
        return True

    except Exception as e:
        logger.error(f"Failed to save JSON to {filepath}: {e}")
        return False


def load_json(filepath: str) -> Optional[Dict[str, Any]]:
    """
    Load data from JSON file with error handling.

    Args:
        filepath: Path to JSON file

    Returns:
        dict: Loaded data
        None: If file doesn't exist or error occurs
    """
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)

        logger.info(f"Successfully loaded data from {filepath}")
        return data

    except FileNotFoundError:
        logger.warning(f"File not found: {filepath}")
        return None

    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in {filepath}: {e}")
        return None

    except Exception as e:
        logger.error(f"Failed to load JSON from {filepath}: {e}")
        return None


def file_exists(filepath: str) -> bool:
    """
    Check if file exists.

    Args:
        filepath: Path to check

    Returns:
        bool: True if file exists
    """
    return Path(filepath).exists()


# DEDUPLICATION (SHARED)

def deduplicate_by_url(documents: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Remove duplicate documents based on URL.

    Some articles may appear in multiple topic categories.
    Keep only the first occurrence.

    Args:
        documents: List of document dictionaries

    Returns:
        list: Deduplicated list of documents

    Example:
        >>> docs = [{'url': 'a', 'title': '1'}, {'url': 'a', 'title': '2'}]
        >>> deduplicate_by_url(docs)
        [{'url': 'a', 'title': '1'}]
    """
    seen_urls = set()
    unique_docs = []

    for doc in documents:
        url = doc.get('url')
        if url and url not in seen_urls:
            seen_urls.add(url)
            unique_docs.append(doc)
        elif url in seen_urls:
            logger.debug(f"Skipping duplicate URL: {url}")

    removed_count = len(documents) - len(unique_docs)
    if removed_count > 0:
        logger.info(f"Removed {removed_count} duplicate documents")

    return unique_docs


# PROGRESS TRACKING

def print_progress(current: int, total: int, prefix: str = "Progress"):
    """
    Print a simple progress indicator.

    Args:
        current: Current item number
        total: Total number of items
        prefix: Prefix string for progress message

    Example:
        >>> print_progress(50, 200, "Scraping articles")
        Scraping articles: 50/200 (25.0%)
    """
    percentage = (current / total * 100) if total > 0 else 0
    print(f"\r{prefix}: {current}/{total} ({percentage:.1f}%)", end='', flush=True)

    # Print newline when complete
    if current == total:
        print()
