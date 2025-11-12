"""
PartSelect Scrapers Package

This package contains web scrapers for extracting data from PartSelect.com
to support the case study chatbot for refrigerator and dishwasher parts.

Modules:
- config: Configuration constants and settings
- utils: Shared utility functions
- blog_scraper: Blog article scraper
- part_scraper: Part detail scraper (future)
- repair_guide_scraper: Repair guide scraper (future)

Usage:
    from scrapers.blog_scraper import BlogScraper

    scraper = BlogScraper()
    scraper.scrape_all_topics()
    scraper.save_to_json('data/raw/blogs_raw.json')

Author: PartSelect Case Study
Date: 2024-11-11
"""

__version__ = '1.0.0'
__author__ = 'PartSelect Case Study'

# Import main classes for easier access
from .blog_scraper import BlogScraper

__all__ = ['BlogScraper']
