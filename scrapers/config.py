"""
Configuration file for PartSelect scrapers.

This module contains all shared constants, keywords, and settings used across
different scrapers (blog, parts, repair guides). Centralizing configuration
makes it easy to update settings and maintain consistency.
"""

import random

# FILTERING KEYWORDS

# Keywords that indicate refrigerator-related content
# Used for case-insensitive title filtering (converted to lowercase before matching)
REFRIGERATOR_KEYWORDS = [
    'fridge',
    'refrigerator',
    'freezer',
    'icemaker',
    'ice maker',
    'defrost',
    'ice dispenser',
    'water dispenser',
    'cooling'
]

# Keywords that indicate dishwasher-related content
DISHWASHER_KEYWORDS = [
    'dishwasher',
    'dish washer',
    'rinse aid',
    'detergent dispenser',
    'spray arm',
    'dish rack'
]

# Combined keywords for easy iteration
ALL_KEYWORDS = REFRIGERATOR_KEYWORDS + DISHWASHER_KEYWORDS


# BRAND RECOGNITION

# Complete list of appliance brands with common variations
# Covers all brands from PartSelect for refrigerators and dishwashers
# Key: Canonical brand name, Value: List of variations to match
BRAND_PATTERNS = {
    'Admiral': ['admiral'],
    'Amana': ['amana'],
    'Beko': ['beko'],
    'Blomberg': ['blomberg'],
    'Bosch': ['bosch'],
    'Caloric': ['caloric'],
    'Crosley': ['crosley'],
    'Dacor': ['dacor'],
    'Dynasty': ['dynasty'],
    'Electrolux': ['electrolux'],
    'Estate': ['estate'],
    'Frigidaire': ['frigidaire'],
    'Gaggenau': ['gaggenau'],
    'GE': ['ge', 'general electric', 'g.e.', 'ge appliances'],
    'Gibson': ['gibson'],
    'Haier': ['haier'],
    'Hardwick': ['hardwick'],
    'Hoover': ['hoover'],
    'Hotpoint': ['hotpoint'],
    'Inglis': ['inglis'],
    'International': ['international'],
    'Jenn-Air': ['jenn-air', 'jennair', 'jenn air'],
    'Kelvinator': ['kelvinator'],
    'Kenmore': ['kenmore'],
    'KitchenAid': ['kitchenaid', 'kitchen aid', 'kitchen-aid'],
    'LG': ['lg'],
    'Litton': ['litton'],
    'Magic Chef': ['magic chef', 'magic-chef', 'magicchef'],
    'Maytag': ['maytag'],
    'Midea': ['midea'],
    'Norge': ['norge'],
    'RCA': ['rca'],
    'Roper': ['roper'],
    'Samsung': ['samsung'],
    'Sharp': ['sharp'],
    'SMEG': ['smeg'],
    'Speed Queen': ['speed queen', 'speed-queen', 'speedqueen'],
    'Tappan': ['tappan'],
    'Thermador': ['thermador'],
    'Uni': ['uni'],
    'Whirlpool': ['whirlpool'],
    'White-Westinghouse': ['white-westinghouse', 'white westinghouse', 'whitewestinghouse'],
}

# Simple list for backward compatibility
BRANDS = list(BRAND_PATTERNS.keys())


# APPLIANCE TYPES

# Scope of the case study (only these two appliance types)
APPLIANCE_TYPES = ['refrigerator', 'dishwasher']


# PARTSELECT URLs

# Base URL for PartSelect website
PARTSELECT_BASE_URL = "https://www.partselect.com"

# Blog topics base URL
BLOG_BASE_URL = f"{PARTSELECT_BASE_URL}/blog/topics/"

# Blog topics to scrape
BLOG_TOPICS = [
    'repair',           # General repair articles
    'error-codes',      # Error code troubleshooting
    'how-to-guides',    # Installation and how-to guides
    'testing',          # Parts testing tutorials
    'use-and-care'      # Maintenance and care guides
]

# Repair pages base URL
REPAIR_BASE_URL = f"{PARTSELECT_BASE_URL}/Repair/"

# Repair appliance types with their URLs
REPAIR_APPLIANCES = {
    'refrigerator': f"{REPAIR_BASE_URL}Refrigerator/",
    'dishwasher': f"{REPAIR_BASE_URL}Dishwasher/"
}

# Parts appliance types with their URLs
PARTS_APPLIANCES = {
    'refrigerator': f"{PARTSELECT_BASE_URL}/Refrigerator-Parts.htm",
    'dishwasher': f"{PARTSELECT_BASE_URL}/Dishwasher-Parts.htm"
}


# SCRAPER BEHAVIOR SETTINGS

# User agent string to identify our scraper (be transparent)
USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
)

# Request timing (be polite to PartSelect servers)
REQUEST_DELAY_MIN = 2.0  # Minimum seconds between requests
REQUEST_DELAY_MAX = 4.0  # Maximum seconds between requests

def get_request_delay():
    """
    Return a random delay between min and max to appear more human-like.

    Returns:
        float: Random delay in seconds
    """
    return random.uniform(REQUEST_DELAY_MIN, REQUEST_DELAY_MAX)

# Retry settings for failed requests
RETRY_ATTEMPTS = 5          # Number of times to retry failed requests
RETRY_BACKOFF = 3           # Exponential backoff multiplier (3^n seconds)

# Request timeout (prevent hanging on slow responses)
TIMEOUT = 30  # seconds


# INTERACTIVE SCRAPING SETTINGS

# Prompt user every N articles to continue or stop
# This helps control costs and allows data quality inspection
ARTICLE_PROMPT_INTERVAL = 50

# Checkpoint saving (save progress every N articles to prevent data loss)
CHECKPOINT_INTERVAL = 25


# REGEX PATTERNS

# PartSelect part numbers (format: PS followed by 6-10 digits)
PARTSELECT_NUMBER_PATTERN = r'\bPS\d{6,10}\b'

# Manufacturer part numbers (format: 2-4 letters followed by 6-10 digits)
# Examples: WPW10321304, DA97-12650A, ADQ36006101
MANUFACTURER_NUMBER_PATTERN = r'\b[A-Z]{2,4}[\d-]{6,15}\b'

# Model number pattern (varies by manufacturer but generally alphanumeric)
# Examples: WDT780SAEM1, RF28R7351SR, KRFC704FPS
MODEL_NUMBER_PATTERN = r'\b[A-Z0-9]{5,15}\b'


# DATA EXTRACTION SETTINGS

# Maximum content length to extract (prevent memory issues with huge articles)
MAX_CONTENT_LENGTH = 100000  # 100KB of text

# Minimum content length (filter out stub articles)
MIN_CONTENT_LENGTH = 200  # 200 characters

# Image URL validation
VALID_IMAGE_EXTENSIONS = ['.jpg', '.jpeg', '.png', '.gif', '.webp', '.svg']

# Video platforms to extract
VIDEO_PLATFORMS = [
    'youtube.com',
    'youtu.be',
    'vimeo.com',
    'partselect.com'  # Self-hosted videos
]

# FILE PATHS

# Output directories
RAW_DATA_DIR = "data/raw"
PROCESSED_DATA_DIR = "data/processed"
COMBINED_DATA_DIR = "data/combined"
CHECKPOINT_DIR = "data/checkpoints"

# Output filenames
BLOG_RAW_FILE = f"{RAW_DATA_DIR}/blogs_raw.json"
BLOG_PROCESSED_FILE = f"{PROCESSED_DATA_DIR}/blogs.json"
BLOG_CHECKPOINT_FILE = f"{CHECKPOINT_DIR}/blog_checkpoint.json"

REPAIR_SYMPTOMS_RAW_FILE = f"{RAW_DATA_DIR}/repair_symptoms_raw.json"
REPAIR_SYMPTOMS_PROCESSED_FILE = f"{PROCESSED_DATA_DIR}/repair_symptoms.json"

PARTS_RAW_FILE = f"{RAW_DATA_DIR}/parts_raw.json"
PARTS_PROCESSED_FILE = f"{PROCESSED_DATA_DIR}/parts.json"

REPAIR_GUIDES_RAW_FILE = f"{RAW_DATA_DIR}/repair_guides_raw.json"
REPAIR_GUIDES_PROCESSED_FILE = f"{PROCESSED_DATA_DIR}/repair_guides.json"

COMBINED_FILE = f"{COMBINED_DATA_DIR}/all_documents.json"


# LOGGING SETTINGS

# Log file location
LOG_FILE = "scrapers/scraper.log"

# Log format
LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'

# Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
LOG_LEVEL = "INFO"


# HTML SELECTORS (Blog Scraper)

# CSS selectors for blog scraping
# These may need updates if PartSelect changes their HTML structure

BLOG_SELECTORS = {
    # Topic page selectors
    'article_cards': 'div.row.blog a.article-card',
    'article_url': 'href',  # attribute
    'article_title': 'div.article-card__title',
    'article_preview': 'p',
    'article_image': 'img',
    'older_button': 'div.blog__pager a',

    # Article page selectors
    'article_container': 'div.blog__article-page',
    'main_title': 'h1.blog__article-page__title',
    'subtitle': 'div.blog__article-page__subtitle',
    'header_image': 'div.blog__article-page__main-img img',
    'content_container': 'div.blog__article-page__content',
    'content_paragraphs': 'p',
    'content_images': 'img',
    'content_videos': 'iframe',
    'section_headers': 'h2, h3',
}

# Repair page selectors
REPAIR_SELECTORS = {
    # Main repair page selectors
    'symptom_links': 'a[href*="/Repair/"]',  # Links to symptom pages like /Repair/Dishwasher/Noisy/
    'symptom_name': 'h3',  # symptom name is in <h3> inside the link
    'symptom_url': 'href',  # attribute

    # Symptom page selectors
    'page_title': 'h1.title-main',
    'difficulty_text': 'div.repair__intro ul.list-disc li',  # Contains "Rated as EASY" text
    'video_container': 'div.yt-video[data-yt-init]',
    'video_data_attr': 'data-yt-init',  # YouTube ID directly in attribute
    'parts_section': 'div.symptom-list',
    'part_section_title': 'h2.section-title',  # Part name/title
    'part_description': 'div.symptom-list__desc div.col-lg-6 p',  # Description paragraphs
    # Note: Images and links are not extracted as they're navigation/help links
    # or category pages. Part details (images, prices, numbers) are available from parts_scraper
}

# Parts page selectors
PARTS_SELECTORS = {
    # Part type links from main parts page
    'part_type_h2_id': 'ShopByPartType',

    # Brand links from part type page
    'brand_h2_id': 'ShopByBrand',

    # Part containers on brand/part-type pages
    'part_container': 'div.nf__part',
    'part_detail': 'div.nf__part__detail',
    'part_title': 'a.nf__part__detail__title',
    'part_title_span': 'span',
    'part_numbers': 'div.nf__part__detail__part-number',
    'part_number_strong': 'strong',
    'part_left_col': 'div.nf__part__left-col',
    'stock_div': 'div.nf__part__left-col__basic-info__stock',
    'stock_svg': 'svg',
    'stock_svg_use': 'use',
    'price_div': 'div.price',
}


# VALIDATION SETTINGS

# Required fields for each document type
REQUIRED_BLOG_FIELDS = ['title', 'url', 'content_text', 'appliance_type', 'topic_category']
REQUIRED_PART_FIELDS = ['part_number', 'name', 'appliance_type', 'price']

# Document ID prefixes
DOC_ID_PREFIXES = {
    'blog': 'blog',
    'part': 'part',
    'repair_guide': 'guide'
}
