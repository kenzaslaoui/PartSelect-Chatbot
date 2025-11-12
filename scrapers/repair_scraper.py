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

                # Filter out category pages and brand pages - only keep actual symptom pages
                # Symptom URLs have 3+ segments after /Repair/
                # e.g., /Repair/Refrigerator/Running-Too-Long/ (actual symptom)
                # Not:  /Repair/Refrigerator/ (category)
                # Not:  /Repair/Dishwasher/Amana-Dishwasher-Repair/ (brand page)
                if self._is_actual_symptom_url(absolute_url, name):
                    symptom_links.append({
                        'name': name,
                        'url': absolute_url
                    })
                    logger.debug(f"Found symptom: {name} -> {absolute_url}")
                else:
                    logger.debug(f"Skipped non-symptom page: {name} -> {absolute_url}")

        return symptom_links

    def _is_actual_symptom_url(self, url: str, symptom_name: str = None) -> bool:
        """
        Check if a URL is an actual symptom page or a category/brand page.

        Real symptom URLs have the structure: /Repair/[Appliance]/[Symptom]/
        Category URLs have only: /Repair/ or /Repair/[Appliance]/
        Brand pages should be skipped: /Repair/[Appliance]/[Brand]-[Appliance]-Repair/

        Args:
            url: Full URL to check
            symptom_name: Optional symptom name to check for brand keywords

        Returns:
            bool: True if it's an actual symptom page, False if it's a category or brand page
        """
        try:
            # Extract the path from the URL
            from urllib.parse import urlparse
            parsed = urlparse(url)
            path = parsed.path.rstrip('/')  # Remove trailing slash

            # Split path into segments
            segments = [s for s in path.split('/') if s]  # Filter out empty segments

            # Find the index of 'Repair' in the segments
            if 'Repair' not in segments:
                return False

            repair_index = segments.index('Repair')

            # Count segments after 'Repair'
            # Symptom pages should have at least 2 segments after Repair
            # (appliance type + symptom name)
            segments_after_repair = len(segments) - repair_index - 1

            if segments_after_repair < 2:
                return False

            # Filter out brand pages
            # Brand pages end with pattern like "Amana-Dishwasher-Repair", "Bosch-Dishwasher-Repair"
            # Check if the last segment contains brand name + appliance type + "repair"
            if symptom_name:
                symptom_lower = symptom_name.lower()
                # Skip if it looks like a brand page (contains "Repair" at the end)
                if symptom_lower.endswith('repair') or ' repair' in symptom_lower:
                    # Check if it also contains an appliance type name (refrigerator, dishwasher, etc.)
                    from .config import APPLIANCE_TYPES
                    for appliance in APPLIANCE_TYPES:
                        if appliance.lower() in symptom_lower:
                            return False  # This is likely a brand page

            return True
        except Exception as e:
            logger.warning(f"Error checking URL structure for {url}: {e}")
            return False

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
                    title = link.get_text(strip=True)

                    # Scrape content from the repair guide page
                    guide_content = self._scrape_repair_guide_content(absolute_url)

                    repair_guides.append({
                        'title': title,
                        'url': absolute_url,
                        'content': guide_content
                    })

            section = {
                'name': part_name,
                'description': description,
                'repair_guides': repair_guides if repair_guides else None,
                # Note: Individual part numbers, prices, and images are not in this structure
                # They're available from the parts_scraper which has already scraped that data
            }

            parts.append(section)

        return parts

    def _extract_inspection_steps(self, soup: BeautifulSoup) -> List[Dict[str, Any]]:
        """
        Extract inspection steps grouped by part name.

        In the new structure, inspection steps are embedded within the part descriptions
        as ordered lists (ol) with step-by-step instructions. We organize these by part
        title, returning a list with part_name and steps list.

        Args:
            soup: BeautifulSoup object

        Returns:
            list: List of dicts with 'part_name' and 'steps' keys
        """
        steps_by_part = {}  # Dict to group steps by part title

        # Look for ordered lists in the part description sections
        parts_section = soup.select_one(REPAIR_SELECTORS['parts_section'])
        if not parts_section:
            return []

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

            if not part_title:
                continue

            # Extract individual steps from the ordered list
            list_items = step_list.find_all('li')
            steps_list = []
            for idx, item in enumerate(list_items, 1):
                step_text = item.get_text(strip=True)
                if step_text:
                    # Prepend step number to the description
                    numbered_step = f"{idx}. {step_text}"
                    steps_list.append(numbered_step)

            # Store steps grouped by part name
            if steps_list:
                steps_by_part[part_title] = steps_list

        # Convert dict to list of dicts with 'part_name' and 'steps'
        return [
            {'part_name': section_name, 'steps': steps}
            for section_name, steps in steps_by_part.items()
        ]

    def _scrape_repair_guide_content(self, url: str) -> Optional[str]:
        """
        Scrape content from a repair guide page.

        Extracts all text content from the repair__content div, including
        paragraphs, steps, and additional information.

        Args:
            url: URL of the repair guide page

        Returns:
            str: Complete text content or None if failed
        """
        html = self._fetch_url(url)
        if not html:
            return None

        try:
            soup = BeautifulSoup(html, 'html.parser')

            # Find the repair content div
            repair_content = soup.find('div', class_='repair__content')
            if not repair_content:
                return None

            # Find the main content table
            content_table = repair_content.find('table')
            if not content_table:
                return None

            # Get the second td which contains the actual content
            tds = content_table.find_all('td')
            if len(tds) < 2:
                return None

            content_td = tds[1]
            text_parts = []

            # Extract all text content in order
            for elem in content_td.children:
                if isinstance(elem, str):
                    text = elem.strip()
                    if text:
                        text_parts.append(text)
                elif elem.name == 'p':
                    text = elem.get_text(strip=True)
                    if text:
                        text_parts.append(text)
                elif elem.name == 'ol':
                    # Extract numbered steps
                    for step in elem.find_all('li'):
                        step_text = step.get_text(strip=True)
                        if step_text:
                            text_parts.append(step_text)
                elif elem.name == 'ul':
                    # Extract additional info
                    for item in elem.find_all('li'):
                        item_text = item.get_text(strip=True)
                        if item_text:
                            text_parts.append(item_text)

            # Combine all text parts
            content = ' '.join(text_parts) if text_parts else None
            return content

        except Exception as e:
            logger.warning(f"Error scraping repair guide content from {url}: {e}")
            return None

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
