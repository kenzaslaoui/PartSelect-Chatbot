"""
PartSelect Blog Scraper

This scraper extracts refrigerator and dishwasher-related articles from the
PartSelect blog (https://www.partselect.com/blog/topics/).

Features:
- Scrapes 5 blog topic categories (repair, error-codes, how-to-guides, testing, use-and-care)
- Filters articles by title keywords (refrigerator/dishwasher only)
- Handles pagination (follows "OLDER" links)
- Interactive scraping (prompts user every 50 articles)
- Automatic checkpointing (saves progress every 25 articles)
- Robust error handling with retries
- Polite scraping with delays
- Deduplicates articles by URL

Output:
- Raw data: data/raw/blogs_raw.json
- Checkpoints: data/checkpoints/blog_checkpoint.json
"""

import logging
import time
import sys
from typing import List, Dict, Optional, Tuple
from pathlib import Path

import requests
from bs4 import BeautifulSoup

# Import configuration and utilities
from .config import (
    BLOG_BASE_URL,
    BLOG_TOPICS,
    BLOG_SELECTORS,
    USER_AGENT,
    get_request_delay,
    RETRY_ATTEMPTS,
    RETRY_BACKOFF,
    TIMEOUT,
    ARTICLE_PROMPT_INTERVAL,
    CHECKPOINT_INTERVAL,
    BLOG_RAW_FILE,
    BLOG_CHECKPOINT_FILE,
    CHECKPOINT_DIR,
    PARTSELECT_BASE_URL,
    LOG_FORMAT,
    LOG_LEVEL
)

from .utils import (
    extract_brand,
    extract_part_numbers,
    extract_appliance_type,
    is_relevant_article,
    strip_html,
    extract_first_paragraph,
    make_absolute_url,
    extract_video_urls,
    validate_document,
    validate_content_length,
    generate_document_id,
    get_timestamp,
    save_json,
    load_json,
    deduplicate_by_url,
    print_progress
)

# Set up logging
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL),
    format=LOG_FORMAT,
    handlers=[
        logging.FileHandler('scrapers/scraper.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)


# BLOG SCRAPER CLASS

class BlogScraper:
    """
    Scraper for PartSelect blog articles.

    This class handles the complete scraping workflow:
    1. Iterate through all blog topic pages
    2. Filter articles by title keywords
    3. Scrape full article content
    4. Extract structured data
    5. Save results with checkpointing

    Attributes:
        base_url (str): Base URL for blog topics
        topics (list): List of blog topics to scrape
        documents (list): List of scraped article documents
        failed_urls (list): List of URLs that failed to scrape
        seen_urls (set): Set of URLs already processed (deduplication)
        article_count (int): Total articles scraped
        filtered_count (int): Articles filtered (not relevant)
        session (requests.Session): HTTP session for connection pooling
    """

    def __init__(self, resume_from_checkpoint: bool = False):
        """
        Initialize the blog scraper.

        Args:
            resume_from_checkpoint: If True, resume from saved checkpoint
        """
        self.base_url = BLOG_BASE_URL
        self.topics = BLOG_TOPICS
        self.documents = []
        self.failed_urls = []
        self.seen_urls = set()
        self.article_count = 0
        self.filtered_count = 0

        # Set up HTTP session with headers that mimic a real browser
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': USER_AGENT,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Sec-Fetch-User': '?1',
            'Sec-Ch-Ua': '"Google Chrome";v="131", "Chromium";v="131", "Not_A Brand";v="24"',
            'Sec-Ch-Ua-Mobile': '?0',
            'Sec-Ch-Ua-Platform': '"macOS"',
            'Cache-Control': 'max-age=0'
        })

        # Resume from checkpoint if requested
        if resume_from_checkpoint:
            self._load_checkpoint()

        logger.info("BlogScraper initialized")


    # MAIN SCRAPING METHODS

    def scrape_all_topics(self):
        """
        Main entry point: Scrape all blog topics.

        This method orchestrates the entire scraping process:
        1. Iterate through each topic
        2. Paginate through topic pages
        3. Filter and scrape relevant articles
        4. Handle user prompts and checkpointing
        """
        logger.info(f"Starting blog scraping for {len(self.topics)} topics")
        print(f"\n{'='*70}")
        print(f"PartSelect Blog Scraper")
        print(f"{'='*70}")
        print(f"Topics: {', '.join(self.topics)}")
        print(f"Filtering for: refrigerator and dishwasher articles only")
        print(f"{'='*70}\n")

        try:
            for topic in self.topics:
                logger.info(f"Scraping topic: {topic}")
                print(f"\nTopic: {topic.upper()}")
                print("-" * 70)

                self._scrape_topic(topic)

            # Final deduplication
            logger.info("Performing final deduplication")
            self.documents = deduplicate_by_url(self.documents)

            print(f"\n{'='*70}")
            print(f" Scraping Complete!")
            print(f"{'='*70}")
            print(f"Total articles scraped: {len(self.documents)}")
            print(f"Articles filtered out: {self.filtered_count}")
            print(f"Failed URLs: {len(self.failed_urls)}")
            print(f"{'='*70}\n")

        except KeyboardInterrupt:
            logger.warning("Scraping interrupted by user")
            print("\n\nScraping interrupted! Saving progress...")
            self._save_checkpoint()

        except Exception as e:
            logger.error(f"Unexpected error during scraping: {e}", exc_info=True)
            print(f"\n Error: {e}")
            print("Saving progress...")
            self._save_checkpoint()


    def _scrape_topic(self, topic: str):
        """
        Scrape all pages for a single blog topic.

        Args:
            topic: Topic name (e.g., 'repair', 'how-to-guides')
        """
        page_num = 1
        has_more_pages = True

        while has_more_pages:
            logger.info(f"Scraping {topic} - page {page_num}")
            print(f"Page {page_num}...", end=' ')

            # Scrape topic page
            article_cards, has_older_button = self._scrape_topic_page(topic, page_num)

            if not article_cards:
                logger.warning(f"No articles found on {topic} page {page_num}")
                print("No articles found")
                break

            print(f"Found {len(article_cards)} articles")

            # Filter and scrape relevant articles
            relevant_count = self._filter_and_scrape_articles(article_cards, topic)
            print(f"  Scraped {relevant_count} relevant articles from this page")

            # Check if there are more pages
            has_more_pages = has_older_button
            if has_more_pages:
                page_num += 1
                time.sleep(get_request_delay())  # Be polite
            else:
                print(f" No more pages for topic: {topic}")

            # Check if user wants to continue (every N articles)
            if self.article_count > 0 and self.article_count % ARTICLE_PROMPT_INTERVAL == 0:
                if not self._prompt_user_continue():
                    logger.info("User chose to stop scraping")
                    return

            # Auto-save checkpoint
            if self.article_count > 0 and self.article_count % CHECKPOINT_INTERVAL == 0:
                self._save_checkpoint()


    def _scrape_topic_page(self, topic: str, page_num: int) -> Tuple[List[Dict], bool]:
        """
        Scrape a single topic page and extract article cards.

        Args:
            topic: Topic name
            page_num: Page number (1-indexed)

        Returns:
            tuple: (article_cards: List[Dict], has_older_button: bool)
                article_cards: List of dicts with {url, title, preview}
                has_older_button: True if there's a next page
        """
        # Build URL
        if page_num == 1:
            url = f"{self.base_url}{topic}/"
        else:
            url = f"{self.base_url}{topic}/?start={page_num}"

        # Fetch page
        html = self._fetch_url(url)
        if not html:
            return [], False

        soup = BeautifulSoup(html, 'html.parser')

        # Extract article cards
        article_cards = []
        cards = soup.select(BLOG_SELECTORS['article_cards'])

        for card in cards:
            try:
                # Extract article URL
                article_url = card.get('href', '')
                if article_url:
                    article_url = make_absolute_url(article_url, PARTSELECT_BASE_URL)

                # Extract title
                title_elem = card.select_one(BLOG_SELECTORS['article_title'])
                title = title_elem.get_text(strip=True) if title_elem else ""

                # Extract preview
                preview_elem = card.select_one(BLOG_SELECTORS['article_preview'])
                preview = preview_elem.get_text(strip=True) if preview_elem else ""

                if article_url and title:
                    article_cards.append({
                        'url': article_url,
                        'title': title,
                        'preview': preview
                    })

            except Exception as e:
                logger.warning(f"Error extracting article card: {e}")
                continue

        # Check for "OLDER" button (pagination)
        older_button = soup.select_one(BLOG_SELECTORS['older_button'])
        has_older_button = older_button is not None

        return article_cards, has_older_button


    def _filter_and_scrape_articles(self, article_cards: List[Dict], topic: str) -> int:
        """
        Filter article cards by relevance and scrape full content.

        Args:
            article_cards: List of article card dictionaries
            topic: Topic category

        Returns:
            int: Number of relevant articles scraped
        """
        relevant_count = 0

        for card in article_cards:
            url = card['url']
            title = card['title']

            # Skip if already seen (deduplication)
            if url in self.seen_urls:
                logger.debug(f"Skipping duplicate URL: {url}")
                continue

            self.seen_urls.add(url)

            # Filter by title relevance
            if not is_relevant_article(title):
                logger.debug(f"Filtered out (not relevant): {title}")
                self.filtered_count += 1
                continue

            # Article is relevant - scrape full content
            logger.info(f"Scraping article: {title}")
            article_data = self._scrape_article(url, topic)

            if article_data:
                self.documents.append(article_data)
                self.article_count += 1
                relevant_count += 1
            else:
                self.failed_urls.append(url)

            # Be polite - delay between requests
            time.sleep(get_request_delay())

        return relevant_count


    def _scrape_article(self, url: str, topic: str) -> Optional[Dict]:
        """
        Scrape full content from an individual article page.

        Args:
            url: Article URL
            topic: Topic category (e.g., 'repair', 'how-to-guides')

        Returns:
            dict: Structured article data
            None: If scraping failed
        """
        # Fetch article page
        html = self._fetch_url(url)
        if not html:
            return None

        soup = BeautifulSoup(html, 'html.parser')

        try:
            # Find article container
            article_container = soup.select_one(BLOG_SELECTORS['article_container'])
            if not article_container:
                logger.warning(f"Article container not found: {url}")
                return None

            # Extract title
            title_elem = soup.select_one(BLOG_SELECTORS['main_title'])
            title = title_elem.get_text(strip=True) if title_elem else "Untitled"

            # Extract subtitle (optional)
            subtitle_elem = soup.select_one(BLOG_SELECTORS['subtitle'])
            subtitle = subtitle_elem.get_text(strip=True) if subtitle_elem else ""

            # Extract content
            content_container = soup.select_one(BLOG_SELECTORS['content_container'])
            if not content_container:
                logger.warning(f"Content container not found: {url}")
                return None

            content_html = str(content_container)
            content_text = strip_html(content_html)

            # Validate content length
            if not validate_content_length(content_text):
                logger.warning(f"Content length invalid for {url}")
                return None

            # Extract summary (first paragraph)
            summary = extract_first_paragraph(content_html)

            # Extract images
            images = []
            for img in content_container.select(BLOG_SELECTORS['content_images']):
                img_url = img.get('src', '')
                if img_url:
                    img_url = make_absolute_url(img_url, PARTSELECT_BASE_URL)
                    images.append(img_url)

            # Also get header image
            header_img = soup.select_one(BLOG_SELECTORS['header_image'])
            if header_img:
                img_url = header_img.get('src', '')
                if img_url:
                    img_url = make_absolute_url(img_url, PARTSELECT_BASE_URL)
                    if img_url not in images:
                        images.insert(0, img_url)  # Add as first image

            # Extract videos
            videos = extract_video_urls(content_html, PARTSELECT_BASE_URL)

            # Extract part numbers
            part_numbers = extract_part_numbers(content_html)

            # Extract metadata
            appliance_type = extract_appliance_type(title, content_text)
            brand = extract_brand(title)

            # Build document
            document = {
                'id': generate_document_id('blog', self.article_count + 1),
                'source_type': 'blog',
                'appliance_type': appliance_type,
                'brand': brand,
                'title': title,
                'subtitle': subtitle,
                'url': url,
                'topic_category': topic,
                'content_html': content_html,
                'content_text': content_text,
                'summary': summary,
                'images': images,
                'videos': videos,
                'parts_mentioned': part_numbers,
                'scraped_at': get_timestamp()
            }

            # Validate document
            is_valid, missing_fields = validate_document(document, 'blog')
            if not is_valid:
                logger.error(f"Document validation failed: {missing_fields}")
                # Still return the document, but log the issue
                # In production, you might choose to skip invalid documents

            return document

        except Exception as e:
            logger.error(f"Error scraping article {url}: {e}", exc_info=True)
            return None


    # HTTP FETCHING WITH RETRY LOGIC

    def _fetch_url(self, url: str) -> Optional[str]:
        """
        Fetch URL with retry logic and error handling.

        Args:
            url: URL to fetch

        Returns:
            str: HTML content
            None: If all retry attempts failed
        """
        for attempt in range(1, RETRY_ATTEMPTS + 1):
            try:
                logger.debug(f"Fetching {url} (attempt {attempt}/{RETRY_ATTEMPTS})")

                response = self.session.get(url, timeout=TIMEOUT)
                response.raise_for_status()  # Raise exception for 4xx/5xx status codes

                return response.text

            except requests.exceptions.Timeout:
                logger.warning(f"Timeout fetching {url} (attempt {attempt}/{RETRY_ATTEMPTS})")

            except requests.exceptions.HTTPError as e:
                status_code = e.response.status_code
                logger.warning(f"HTTP {status_code} error for {url} (attempt {attempt}/{RETRY_ATTEMPTS})")

                # Don't retry on 404 (page not found)
                if status_code == 404:
                    return None

                # Retry on 403 (might be rate limiting), but fail on 401 (unauthorized)
                if status_code == 401:
                    logger.error(f"Unauthorized access for {url}")
                    return None

            except requests.exceptions.RequestException as e:
                logger.warning(f"Request error for {url}: {e}")

            # Exponential backoff before retry
            if attempt < RETRY_ATTEMPTS:
                sleep_time = RETRY_BACKOFF ** attempt
                logger.debug(f"Retrying in {sleep_time} seconds...")
                time.sleep(sleep_time)

        logger.error(f"Failed to fetch {url} after {RETRY_ATTEMPTS} attempts")
        return None


    # USER INTERACTION

    def _prompt_user_continue(self) -> bool:
        """
        Ask user if they want to continue scraping.

        Returns:
            bool: True if user wants to continue, False otherwise
        """
        print(f"\n{'='*70}")
        print(f"   Progress Update:")
        print(f"   Articles scraped: {self.article_count}")
        print(f"   Articles filtered: {self.filtered_count}")
        print(f"   Failed URLs: {len(self.failed_urls)}")
        print(f"{'='*70}")

        while True:
            response = input("Continue scraping? [Y/n]: ").strip().lower()

            if response in ['', 'y', 'yes']:
                return True
            elif response in ['n', 'no']:
                return False
            else:
                print("Please enter 'y' or 'n'")


    # CHECKPOINTING

    def _save_checkpoint(self):
        """
        Save current scraping progress to checkpoint file.

        This allows resuming if scraping is interrupted.
        """
        checkpoint_data = {
            'metadata': {
                'checkpoint_time': get_timestamp(),
                'article_count': self.article_count,
                'filtered_count': self.filtered_count,
                'failed_count': len(self.failed_urls)
            },
            'documents': self.documents,
            'failed_urls': self.failed_urls,
            'seen_urls': list(self.seen_urls)
        }

        # Create checkpoint directory
        Path(CHECKPOINT_DIR).mkdir(parents=True, exist_ok=True)

        if save_json(checkpoint_data, BLOG_CHECKPOINT_FILE):
            logger.info(f"Checkpoint saved: {self.article_count} articles")
            print(f"Checkpoint saved ({self.article_count} articles)")


    def _load_checkpoint(self):
        """
        Load progress from checkpoint file.
        """
        checkpoint_data = load_json(BLOG_CHECKPOINT_FILE)

        if checkpoint_data:
            self.documents = checkpoint_data.get('documents', [])
            self.failed_urls = checkpoint_data.get('failed_urls', [])
            self.seen_urls = set(checkpoint_data.get('seen_urls', []))
            self.article_count = len(self.documents)

            logger.info(f"Loaded checkpoint: {self.article_count} articles")
            print(f"📂 Resuming from checkpoint ({self.article_count} articles)")
        else:
            logger.warning("No checkpoint found or failed to load")


    # SAVE RESULTS

    def save_to_json(self, filepath: str = BLOG_RAW_FILE):
        """
        Save scraped data to JSON file.

        Args:
            filepath: Output file path
        """
        output_data = {
            'metadata': {
                'scraper_type': 'blog',
                'scraper_version': '1.0',
                'scraped_date': get_timestamp(),
                'total_articles': len(self.documents),
                'filtered_articles': self.filtered_count,
                'failed_urls': len(self.failed_urls),
                'topics_scraped': self.topics,
                'filters_applied': {
                    'refrigerator_keywords': True,
                    'dishwasher_keywords': True
                }
            },
            'documents': self.documents,
            'failed_urls': self.failed_urls
        }

        if save_json(output_data, filepath):
            print(f"\nData saved to: {filepath}")
            print(f"   Total articles: {len(self.documents)}")
        else:
            print(f"\nFailed to save data to: {filepath}")


# MAIN ENTRY POINT

def main():
    """
    Main entry point for the blog scraper.

    Usage:
        python -m scrapers.blog_scraper
    """
    import argparse

    parser = argparse.ArgumentParser(description='Scrape PartSelect blog articles')
    parser.add_argument(
        '--resume',
        action='store_true',
        help='Resume from checkpoint'
    )
    parser.add_argument(
        '--output',
        type=str,
        default=BLOG_RAW_FILE,
        help='Output file path'
    )

    args = parser.parse_args()

    # Create scraper instance
    scraper = BlogScraper(resume_from_checkpoint=args.resume)

    # Run scraper
    scraper.scrape_all_topics()

    # Save results
    scraper.save_to_json(args.output)

    logger.info("Blog scraping completed")


if __name__ == "__main__":
    main()
