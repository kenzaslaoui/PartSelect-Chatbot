"""
Repair symptom scraper for PartSelect repair pages.

Scrapes refrigerator and dishwasher repair symptom pages to extract:
- Symptom names and URLs
- Difficulty levels
- Repair stories
- YouTube video tutorials
- Related parts with details
- Step-by-step inspection guides

Much simpler than blog scraper - no pagination, filtering, or user prompts needed.
Only ~27 total pages to scrape (13 refrigerator + 14 dishwasher symptoms).

Author: PartSelect Case Study
Date: 2024-11-11
"""

import time
import logging
import requests
from typing import List, Dict, Optional, Any
from bs4 import BeautifulSoup

from .config import (
    REPAIR_APPLIANCES,
    REPAIR_SELECTORS,
    REPAIR_SYMPTOMS_RAW_FILE,
    USER_AGENT,
    TIMEOUT,
    RETRY_ATTEMPTS,
    RETRY_BACKOFF,
    get_request_delay
)

from .utils import (
    extract_youtube_url,
    extract_youtube_thumbnail,
    extract_difficulty,
    extract_number,
    make_absolute_url,
    save_json,
    get_timestamp,
    get_date_string,
    generate_document_id
)

# Set up logging
import os
log_level = os.getenv('LOG_LEVEL', 'INFO')
logging.basicConfig(
    level=getattr(logging, log_level),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class RepairScraper:
    """
    Scraper for PartSelect repair symptom pages.

    Scrapes repair guides for refrigerators and dishwashers.
    Two-level structure:
    1. Main repair page - lists all symptoms
    2. Individual symptom pages - detailed repair info
    """

    def __init__(self):
        """Initialize the repair scraper."""
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

        self.documents = []
        self.failed_urls = []
        self.total_scraped = 0

    def scrape_all_appliances(self) -> Dict[str, Any]:
        """
        Main entry point - scrape all appliance types.

        Returns:
            dict: Complete scraping results with metadata
        """
        logger.info("Starting repair symptom scraping")
        start_time = time.time()

        # Scrape each appliance type
        for appliance_type, base_url in REPAIR_APPLIANCES.items():
            logger.info(f"\nScraping {appliance_type} repair symptoms...")
            self._scrape_appliance(appliance_type, base_url)

        # Calculate statistics
        elapsed_time = time.time() - start_time
        logger.info(f"\nScraping complete!")
        logger.info(f"Total symptoms scraped: {self.total_scraped}")
        logger.info(f"Failed URLs: {len(self.failed_urls)}")
        logger.info(f"Time elapsed: {elapsed_time:.1f} seconds")

        # Prepare output
        return {
            'metadata': {
                'scraper_type': 'repair_symptoms',
                'scraper_version': '1.0',
                'scraped_date': get_date_string(),
                'total_symptoms': self.total_scraped,
                'failed_urls': len(self.failed_urls),
                'appliance_types': list(REPAIR_APPLIANCES.keys())
            },
            'documents': self.documents,
            'failed_urls': self.failed_urls
        }

    def _scrape_appliance(self, appliance_type: str, base_url: str):
        """
        Scrape all symptoms for a specific appliance type.

        Args:
            appliance_type: Type of appliance (refrigerator/dishwasher)
            base_url: Base URL for this appliance's repair page
        """
        # Fetch the main repair page
        html = self._fetch_url(base_url)
        if not html:
            logger.error(f"Failed to fetch main page: {base_url}")
            return

        # Parse symptom links
        symptom_links = self._parse_symptom_links(html, base_url)
        logger.info(f"Found {len(symptom_links)} symptoms for {appliance_type}")

        # Scrape each symptom page
        for idx, symptom_info in enumerate(symptom_links, 1):
            symptom_name = symptom_info['name']
            symptom_url = symptom_info['url']

            logger.info(f"[{idx}/{len(symptom_links)}] Scraping: {symptom_name}")

            # Scrape the symptom page
            symptom_doc = self._scrape_symptom_page(
                symptom_url,
                symptom_name,
                appliance_type
            )

            if symptom_doc:
                self.documents.append(symptom_doc)
                self.total_scraped += 1

            # Polite delay between requests
            time.sleep(get_request_delay())

    def _parse_symptom_links(self, html: str, base_url: str) -> List[Dict[str, str]]:
        """
        Parse symptom links from main repair page.

        Args:
            html: HTML content of main repair page
            base_url: Base URL for making absolute URLs

        Returns:
            list: List of dicts with 'name' and 'url' keys
        """
        soup = BeautifulSoup(html, 'html.parser')
        symptom_links = []

        # Save HTML for debugging if it's short (likely an error page)
        if len(html) < 10000:
            debug_file = f'/tmp/repair_page_debug_{len(html)}_bytes.html'
            with open(debug_file, 'w') as f:
                f.write(html)
            logger.info(f"Saved debug HTML to {debug_file} ({len(html)} bytes)")

        # Find all symptom links
        links = soup.select(REPAIR_SELECTORS['symptom_links'])
        logger.info(f"Found {len(links)} links using selector '{REPAIR_SELECTORS['symptom_links']}'")
        logger.info(f"HTML size: {len(html)} bytes")

        logger.info(f"Successfully found {len(links)} symptom links")

        for link in links:
            url = link.get('href', '')

            # Extract name from h3 element if selector says to use h3
            if REPAIR_SELECTORS['symptom_name'] == 'h3':
                h3_elem = link.select_one('h3')
                name = h3_elem.get_text(strip=True) if h3_elem else link.get_text(strip=True)
            else:
                name = link.get_text(strip=True)

            if name and url:
                absolute_url = make_absolute_url(url, base_url)
                symptom_links.append({
                    'name': name,
                    'url': absolute_url
                })
                logger.debug(f"Found symptom: {name} -> {absolute_url}")

        return symptom_links

    def _scrape_symptom_page(
        self,
        url: str,
        symptom_name: str,
        appliance_type: str
    ) -> Optional[Dict[str, Any]]:
        """
        Scrape a single symptom page.

        Args:
            url: URL of symptom page
            symptom_name: Name of the symptom
            appliance_type: Type of appliance

        Returns:
            dict: Document with all extracted data
            None: If scraping fails
        """
        # Fetch the page
        html = self._fetch_url(url)
        if not html:
            self.failed_urls.append(url)
            return None

        soup = BeautifulSoup(html, 'html.parser')

        # Extract all data
        document = {
            'id': generate_document_id('repair', self.total_scraped + 1),
            'source_type': 'repair_symptom',
            'appliance_type': appliance_type,
            'symptom_name': symptom_name,
            'url': url,
            'difficulty': self._extract_difficulty(soup),
            'repair_story': self._extract_repair_story(soup),
            'video': self._extract_video(soup),
            'parts': self._extract_parts(soup),
            'inspection_steps': self._extract_inspection_steps(soup),
            'scraped_at': get_timestamp()
        }

        return document

    def _extract_difficulty(self, soup: BeautifulSoup) -> Optional[str]:
        """
        Extract difficulty information.

        Args:
            soup: BeautifulSoup object

        Returns:
            str: Difficulty description or None
        """
        # Look for difficulty text in the list items (e.g., "Rated as EASY")
        difficulty_items = soup.select(REPAIR_SELECTORS['difficulty_text'])
        for item in difficulty_items:
            text = item.get_text(strip=True)
            if 'rated' in text.lower() or 'easy' in text.lower() or 'difficult' in text.lower():
                # Extract difficulty level from text like "Rated as EASY"
                difficulty = extract_difficulty(text) or text
                if difficulty:
                    return difficulty
        return None

    def _extract_repair_story(self, soup: BeautifulSoup) -> Optional[str]:
        """
        Extract repair story text.
        
        In the new structure, there's no separate repair story section.
        The introduction text is in the repair__intro section.

        Args:
            soup: BeautifulSoup object

        Returns:
            str: Repair story text or None
        """
        # Look for intro text in the repair__intro section
        intro_section = soup.select_one('div.repair__intro')
        if intro_section:
            # Get text from the intro section, excluding the part list links
            intro_text = intro_section.select_one('div.col-lg-8')
            if intro_text:
                # Remove the "Click a Part Below" heading and links
                heading = intro_text.find('h3')
                if heading:
                    heading.decompose()
                return intro_text.get_text(separator=' ', strip=True)
        return None

    def _extract_video(self, soup: BeautifulSoup) -> Optional[Dict[str, str]]:
        """
        Extract YouTube video information.

        Args:
            soup: BeautifulSoup object

        Returns:
            dict: Video info with id, url, and thumbnail or None
        """
        video_container = soup.select_one(REPAIR_SELECTORS['video_container'])
        if not video_container:
            return None

        # Extract video ID directly from data-yt-init attribute (it's a string, not JSON)
        video_id = video_container.get(REPAIR_SELECTORS['video_data_attr'])
        if not video_id:
            return None

        return {
            'video_id': video_id,
            'video_url': extract_youtube_url(video_id),
            'thumbnail_url': extract_youtube_thumbnail(video_id)
        }

    def _extract_parts(self, soup: BeautifulSoup) -> List[Dict[str, Any]]:
        """
        Extract parts information.
        
        In the new structure, parts are organized as sections with:
        - h2 title (part name)
        - Description paragraphs

        Args:
            soup: BeautifulSoup object

        Returns:
            list: List of part dictionaries
        """
        parts = []
        parts_section = soup.select_one(REPAIR_SELECTORS['parts_section'])

        if not parts_section:
            return parts

        # Find all part section titles (h2.section-title)
        part_titles = parts_section.select(REPAIR_SELECTORS['part_section_title'])

        for title_elem in part_titles:
            part_name = title_elem.get_text(strip=True)
            if not part_name:
                continue

            # Find the description section that follows this title
            # It's in the next sibling div with class symptom-list__desc
            desc_section = title_elem.find_next_sibling('div', class_='symptom-list__desc')
            if not desc_section:
                continue

            # Extract description paragraphs
            desc_paragraphs = desc_section.select(REPAIR_SELECTORS['part_description'])
            description = ' '.join([p.get_text(strip=True) for p in desc_paragraphs]) if desc_paragraphs else None

            # Extract repair guide/tutorial links (e.g., "How to check a timer", "How to replace a timer")
            all_links = desc_section.find_all('a', href=True)
            repair_guides = []
            
            for link in all_links:
                href = link.get('href', '')
                href_lower = href.lower()
                link_text = link.get_text(strip=True).lower()
                
                # Skip navigation/help links
                if (href.startswith('#') or 
                    'find-your-model-number' in href_lower or
                    'model-number' in href_lower or 
                    'model number' in link_text or
                    'view all' in link_text or
                    'need help' in link_text):
                    continue
                
                # Keep repair guide links (contain "repair.htm" in URL)
                # Examples: dishwasher+test-motor+repair.htm, dishwasher+replace-timer+repair.htm
                if 'repair.htm' in href_lower:
                    absolute_url = make_absolute_url(href, 'https://www.partselect.com')
                    repair_guides.append({
                        'title': link.get_text(strip=True),
                        'url': absolute_url
                    })

            part = {
                'name': part_name,
                'description': description,
                'repair_guides': repair_guides if repair_guides else None,
                # Note: Individual part numbers, prices, and images are not in this structure
                # They're available from the parts_scraper which has already scraped that data
            }

            parts.append(part)

        return parts

    def _extract_inspection_steps(self, soup: BeautifulSoup) -> List[Dict[str, Any]]:
        """
        Extract inspection steps.
        
        In the new structure, inspection steps are embedded within the part descriptions
        as ordered lists (ol) with step-by-step instructions. We'll extract these from
        the part description sections.

        Args:
            soup: BeautifulSoup object

        Returns:
            list: List of step dictionaries
        """
        steps = []
        
        # Look for ordered lists in the part description sections
        parts_section = soup.select_one(REPAIR_SELECTORS['parts_section'])
        if not parts_section:
            return steps

        # Find all ordered lists in part descriptions
        step_lists = parts_section.select('div.symptom-list__desc ol')
        
        for step_list in step_lists:
            # Get the parent part section to find the part name
            part_section = step_list.find_parent('div', class_='symptom-list__desc')
            part_title = None
            if part_section:
                prev_title = part_section.find_previous_sibling('h2', class_='section-title')
                if prev_title:
                    part_title = prev_title.get_text(strip=True)

            # Extract individual steps from the ordered list
            list_items = step_list.find_all('li')
            for idx, item in enumerate(list_items, 1):
                step_text = item.get_text(strip=True)
                if step_text:
                    step = {
                        'step_number': idx,
                        'title': part_title,  # Associate step with part
                        'description': step_text,
                        'image_url': None
                    }
                    steps.append(step)

        return steps

    def _fetch_url(self, url: str, referer: str = None) -> Optional[str]:
        """
        Fetch URL with retry logic.

        Args:
            url: URL to fetch
            referer: Optional referer header value

        Returns:
            str: HTML content or None if failed
        """
        for attempt in range(1, RETRY_ATTEMPTS + 1):
            try:
                # Set referer header if provided
                headers = {}
                if referer:
                    headers['Referer'] = referer
                else:
                    headers['Referer'] = 'https://www.partselect.com'

                response = self.session.get(url, timeout=TIMEOUT, headers=headers)
                response.raise_for_status()

                logger.debug(f"Successfully fetched: {url}")
                return response.text

            except requests.exceptions.HTTPError as e:
                status_code = e.response.status_code
                logger.warning(f"Attempt {attempt}/{RETRY_ATTEMPTS} failed for {url}: {status_code} Client Error")

                # Don't retry on 404 (page not found)
                if status_code == 404:
                    return None

                # Retry on 403 (might be rate limiting), but fail on 401 (unauthorized)
                if status_code == 401:
                    logger.error(f"Unauthorized access for {url}")
                    return None

                if attempt < RETRY_ATTEMPTS:
                    sleep_time = RETRY_BACKOFF ** attempt
                    logger.info(f"Retrying in {sleep_time} seconds...")
                    time.sleep(sleep_time)
                else:
                    logger.error(f"Failed to fetch {url} after {RETRY_ATTEMPTS} attempts")
                    return None

            except requests.exceptions.RequestException as e:
                logger.warning(f"Attempt {attempt}/{RETRY_ATTEMPTS} failed for {url}: {e}")

                if attempt < RETRY_ATTEMPTS:
                    sleep_time = RETRY_BACKOFF ** attempt
                    logger.info(f"Retrying in {sleep_time} seconds...")
                    time.sleep(sleep_time)
                else:
                    logger.error(f"Failed to fetch {url} after {RETRY_ATTEMPTS} attempts")
                    return None

        return None

    def save_to_json(self, filepath: str = REPAIR_SYMPTOMS_RAW_FILE):
        """
        Save scraped data to JSON file.

        Args:
            filepath: Output file path
        """
        data = {
            'metadata': {
                'scraper_type': 'repair_symptoms',
                'scraper_version': '1.0',
                'scraped_date': get_date_string(),
                'total_symptoms': len(self.documents),
                'failed_urls': len(self.failed_urls),
                'appliance_types': list(REPAIR_APPLIANCES.keys())
            },
            'documents': self.documents,
            'failed_urls': self.failed_urls
        }

        success = save_json(data, filepath)

        if success:
            logger.info(f"Saved {len(self.documents)} symptoms to {filepath}")
        else:
            logger.error(f"Failed to save data to {filepath}")


def main():
    """Main entry point for running the repair scraper."""
    scraper = RepairScraper()

    try:
        # Scrape all appliances
        scraper.scrape_all_appliances()

        # Save results
        scraper.save_to_json()

        logger.info("\nScraping complete!")
        logger.info(f"Total symptoms: {scraper.total_scraped}")
        logger.info(f"Failed URLs: {len(scraper.failed_urls)}")

    except KeyboardInterrupt:
        logger.info("\nScraping interrupted by user")
        logger.info("Saving progress...")
        scraper.save_to_json()

    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        logger.info("Saving progress...")
        scraper.save_to_json()


if __name__ == '__main__':
    main()
