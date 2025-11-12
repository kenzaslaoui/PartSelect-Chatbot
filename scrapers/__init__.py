"""
PartSelect Scrapers Package

This package contains web scrapers for extracting data from PartSelect.com
to support the case study chatbot for refrigerator and dishwasher parts.

Modules:
- config: Configuration constants and settings
- utils: Shared utility functions
- blog_scraper: Blog article scraper
- parts_scraper: Parts catalog and pricing scraper
- repair_scraper: Repair symptom and troubleshooting guide scraper

Usage Examples:
    # Blog scraper (50+ articles across 5 topics)
    from scrapers import BlogScraper
    scraper = BlogScraper()
    scraper.scrape_all_topics()

    # Repair scraper (21 symptom guides: 12 fridge + 9 dishwasher)
    from scrapers import RepairScraper
    scraper = RepairScraper()
    scraper.scrape_all_appliances()

    # Parts scraper (1000s of parts across brands)
    from scrapers import PartsScraper
    scraper = PartsScraper()
    scraper.scrape_all_appliances()
"""

# Import main classes for easier access
from .blog_scraper import BlogScraper
from .repair_scraper import RepairScraper
from .parts_scraper import PartsScraper

__all__ = ['BlogScraper', 'RepairScraper', 'PartsScraper']
