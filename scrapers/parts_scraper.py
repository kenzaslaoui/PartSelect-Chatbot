"""
Parts scraper for PartSelect parts catalog.

Scrapes refrigerator and dishwasher parts to extract:
- Part names and PartSelect numbers
- Manufacturer part numbers
- Prices and stock status
- Part types and brands

Three-level scraping structure:
1. Main parts page (by appliance) -> part type links
2. Part type page -> brand links
3. Brand page -> individual parts

Author: PartSelect Case Study
Date: 2024-11-11
"""

import time
import logging
import requests
from typing import List, Dict, Optional, Any
from bs4 import BeautifulSoup

from .config import (
    PARTSELECT_BASE_URL,
    PARTS_APPLIANCES,
    PARTS_SELECTORS,
    PARTS_RAW_FILE,
    USER_AGENT,
    TIMEOUT,
    RETRY_ATTEMPTS,
    RETRY_BACKOFF,
    get_request_delay
)

from .utils import (
    save_json,
    get_timestamp,
    get_date_string,
    generate_document_id
)

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class PartsScraper:
    """
    Scraper for PartSelect parts catalog.

    Scrapes parts for refrigerators and dishwashers.
    Three-level structure:
    1. Main parts page - lists all part types
    2. Part type pages - lists all brands
    3. Brand pages - lists all parts
    """

    def __init__(self):
        """Initialize the parts scraper."""
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
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
        logger.info("Starting parts catalog scraping")
        start_time = time.time()

        # Scrape each appliance type
        for appliance_type, base_url in PARTS_APPLIANCES.items():
            logger.info(f"\nScraping {appliance_type} parts...")
            self._scrape_appliance(appliance_type, base_url)

        # Calculate statistics
        elapsed_time = time.time() - start_time
        logger.info(f"\nScraping complete!")
        logger.info(f"Total parts scraped: {self.total_scraped}")
        logger.info(f"Failed URLs: {len(self.failed_urls)}")
        logger.info(f"Time elapsed: {elapsed_time:.1f} seconds")

        # Prepare output
        return {
            'metadata': {
                'scraper_type': 'parts',
                'scraper_version': '1.0',
                'scraped_date': get_date_string(),
                'total_parts': self.total_scraped,
                'failed_urls': len(self.failed_urls),
                'appliance_types': list(PARTS_APPLIANCES.keys())
            },
            'documents': self.documents,
            'failed_urls': self.failed_urls
        }

    def _scrape_appliance(self, appliance_type: str, base_url: str):
        """
        Scrape all parts for a specific appliance type.

        Args:
            appliance_type: Type of appliance (refrigerator/dishwasher)
            base_url: Base URL for this appliance's parts page
        """
        # Fetch the main parts page
        html = self._fetch_url(base_url)
        if not html:
            logger.error(f"Failed to fetch main page: {base_url}")
            return

        # Parse part type links
        part_type_links = self._get_links_by_h2_id(html, PARTS_SELECTORS['part_type_h2_id'])
        logger.info(f"Found {len(part_type_links)} part types for {appliance_type}")

        # Scrape each part type
        for idx, part_type_url in enumerate(part_type_links, 1):
            logger.info(f"[{idx}/{len(part_type_links)}] Scraping part type: {part_type_url}")

            # Scrape brands for this part type
            self._scrape_part_type(
                part_type_url,
                appliance_type
            )

            # Polite delay between requests
            time.sleep(get_request_delay())

    def _get_links_by_h2_id(self, html: str, h2_id: str) -> List[str]:
        """
        Extract links from a page by finding h2 element with specific id.

        Args:
            html: HTML content
            h2_id: The id attribute of the h2 element to find

        Returns:
            list: List of full URLs from the sibling ul element
        """
        soup = BeautifulSoup(html, 'lxml')

        # Find h2 with specified id
        h2_element = soup.find('h2', id=h2_id)

        if not h2_element:
            logger.warning(f"Could not find h2 with id '{h2_id}'")
            return []

        # Find the next sibling ul element
        ul_element = h2_element.find_next_sibling('ul')

        if not ul_element:
            logger.warning(f"Could not find ul sibling of h2#{h2_id}")
            return []

        # Extract all links from li elements
        links = []
        for li in ul_element.find_all('li'):
            a_tag = li.find('a', href=True)
            if a_tag:
                href = a_tag['href']
                # Construct full URL
                full_url = f"{PARTSELECT_BASE_URL}{href}"
                links.append(full_url)

        return links

    def _scrape_part_type(self, url: str, appliance_type: str):
        """
        Scrape all brands for a specific part type.

        Args:
            url: URL of part type page
            appliance_type: Type of appliance
        """
        # Fetch the part type page
        html = self._fetch_url(url)
        if not html:
            self.failed_urls.append(url)
            return

        # Parse brand links
        brand_links = self._get_links_by_h2_id(html, PARTS_SELECTORS['brand_h2_id'])
        logger.info(f"  Found {len(brand_links)} brand URLs")

        # Scrape each brand
        for brand_url in brand_links:
            logger.info(f"    Scraping: {brand_url}")

            # Scrape parts for this brand
            self._scrape_brand_page(brand_url, appliance_type)

            # Polite delay between requests
            time.sleep(get_request_delay())

        # Save progress after completing this part type
        logger.info(f"  Saving progress after part type: {url}")
        self.save_to_json()

    def _scrape_brand_page(self, url: str, appliance_type: str):
        """
        Scrape parts from a brand page.

        Args:
            url: URL of brand page
            appliance_type: Type of appliance
        """
        # Fetch the brand page
        html = self._fetch_url(url)
        if not html:
            self.failed_urls.append(url)
            return

        # Extract metadata from URL
        manufacturer, machine_type, part_type = self._extract_metadata_from_url(url)

        soup = BeautifulSoup(html, 'lxml')

        # Extract parts from this page
        parts = self._extract_parts(soup, manufacturer, machine_type, part_type, appliance_type)

        for part in parts:
            self.documents.append(part)
            self.total_scraped += 1

        logger.info(f"      Found {len(parts)} parts")

    def _extract_metadata_from_url(self, url: str) -> tuple:
        """
        Extract manufacturer, machine type, and part type from URL.
        URL format: [manufacturer]-[machine]-[part-type].htm

        Args:
            url: URL to parse

        Returns:
            tuple: (manufacturer, machine_type, part_type)
        """
        try:
            # Extract filename from URL
            filename = url.split('/')[-1].replace('.htm', '')

            # Determine machine type and split pattern
            if 'Dishwasher' in filename:
                machine_type = 'Dishwasher'
                split_pattern = '-Dishwasher-'
            elif 'Refrigerator' in filename:
                machine_type = 'Refrigerator'
                split_pattern = '-Refrigerator-'
            else:
                return '', '', ''

            # Split filename and extract manufacturer and part type
            parts = filename.split(split_pattern)
            manufacturer = parts[0].replace('-', ' ')
            part_type = parts[1].replace('-', ' ') if len(parts) > 1 else ''

            return manufacturer, machine_type, part_type

        except Exception:
            return '', '', ''

    def _extract_parts(
        self,
        soup: BeautifulSoup,
        manufacturer: str,
        machine_type: str,
        part_type: str,
        appliance_type: str
    ) -> List[Dict[str, Any]]:
        """
        Extract all parts from a page.

        Args:
            soup: BeautifulSoup object
            manufacturer: Manufacturer name
            machine_type: Machine type (Refrigerator/Dishwasher)
            part_type: Part type name
            appliance_type: Type of appliance

        Returns:
            list: List of part dictionaries
        """
        parts = []

        # Find all part containers
        part_containers = soup.find_all(PARTS_SELECTORS['part_container'].split('.')[0],
                                       class_=PARTS_SELECTORS['part_container'].split('.')[1])

        for container in part_containers:
            part_info = {
                'id': generate_document_id('part', self.total_scraped + len(parts) + 1),
                'source_type': 'part',
                'appliance_type': appliance_type.lower(),
                'manufacturer': manufacturer,
                'machine_type': machine_type,
                'part_type': part_type
            }

            # Find the detail section
            part_detail = container.find(PARTS_SELECTORS['part_detail'].split('.')[0],
                                        class_=PARTS_SELECTORS['part_detail'].split('.')[1])
            if not part_detail:
                continue

            # Get title and link
            title_link = part_detail.find('a', class_=PARTS_SELECTORS['part_title'].split('.')[1])
            if title_link:
                span = title_link.find(PARTS_SELECTORS['part_title_span'])
                if span:
                    part_info['title'] = span.get_text(strip=True)
                href = title_link.get('href')
                if href:
                    part_info['url'] = f"{PARTSELECT_BASE_URL}{href.split('?')[0]}"
                    # Scrape part details page for extra fields
                    extra_details = self._scrape_part_details(part_info['url'])
                    part_info.update(extra_details)

            # Get PartSelect Number and Manufacturer Number
            part_numbers = part_detail.find_all(PARTS_SELECTORS['part_numbers'].split('.')[0],
                                               class_=PARTS_SELECTORS['part_numbers'].split('.')[1])
            for pn_div in part_numbers:
                text = pn_div.get_text(strip=True)
                strong = pn_div.find(PARTS_SELECTORS['part_number_strong'])
                if strong:
                    if 'PartSelect Number' in text:
                        part_info['partselect_number'] = strong.get_text(strip=True)
                    elif 'Manufacturer Part Number' in text:
                        part_info['manufacturer_number'] = strong.get_text(strip=True)

            # Get price and stock from left column
            left_col = container.find(PARTS_SELECTORS['part_left_col'].split('.')[0],
                                     class_=PARTS_SELECTORS['part_left_col'].split('.')[1])
            if left_col:
                stock_text = left_col.get_text(strip=True)
                if 'In Stock' in stock_text:
                    part_info['stock_status'] = 'In Stock'
                elif 'Out of Stock' in stock_text:
                    part_info['stock_status'] = 'Out of Stock'
                else:
                    part_info['stock_status'] = 'Unknown'

                # Get price
                price_div = left_col.find(PARTS_SELECTORS['price_div'].split('.')[0],
                                         class_=PARTS_SELECTORS['price_div'].split('.')[1])
                if price_div:
                    price_text = price_div.get_text(strip=True).replace('$', '')
                    part_info['price'] = price_text
                else:
                    part_info['price'] = ''

            # Add scraped timestamp
            part_info['scraped_at'] = get_timestamp()

            # Only add if we got at least some information
            if part_info.get('title') or part_info.get('partselect_number'):
                parts.append(part_info)

        return parts

    def _scrape_part_details(self, url: str) -> Dict[str, Any]:
        """
        Scrape detailed information for an individual part.

        Args:
            url: URL of the part detail page

        Returns:
            dict: Dictionary of additional fields (installation type, description, etc.)
        """
        html = self._fetch_url(url)
        if not html:
            self.failed_urls.append(url)
            return {}

        soup = BeautifulSoup(html, 'lxml')
        details = {}

        # --- Installation difficulty & time ---
        repair_container = soup.find('div', class_='pd__repair-rating__container__item')
        if repair_container:
            # Look for difficulty
            diff_text = repair_container.get_text()
            if 'Really Easy' in diff_text:
                details['installation_type'] = 'Really Easy'
            elif 'Very Easy' in diff_text:
                details['installation_type'] = 'Very Easy'
            elif 'Easy' in diff_text:
                details['installation_type'] = 'Easy'
            elif 'A Bit Difficult' in diff_text:
                details['installation_type'] = 'A Bit Difficult'

            # Look for time duration
            if 'Less than 15 mins' in diff_text:
                details['average_installation_time'] = 'Less than 15 mins'
            elif '15 - 30 mins' in diff_text:
                details['average_installation_time'] = '15 - 30 mins'
            elif '30 - 60 mins' in diff_text:
                details['average_installation_time'] = '30 - 60 mins'
            elif '1 - 2 hours' in diff_text:
                details['average_installation_time'] = '1 - 2 hours'

        # --- Product description ---
        # Try multiple ways to find the description
        desc_div = None

        # Method 1: Look in ProductDescription section
        desc_section = soup.find('div', id='ProductDescription')
        if desc_section:
            desc_div = desc_section.find('div', {'itemprop': 'description'})

        # Method 2: Look for itemprop="description" anywhere
        if not desc_div:
            desc_div = soup.find('div', {'itemprop': 'description'})

        # Method 3: Look in pd__description class
        if not desc_div:
            desc_container = soup.find('div', class_='pd__description')
            if desc_container:
                desc_div = desc_container.find('div', {'itemprop': 'description'})

        if desc_div:
            desc_text = desc_div.get_text(strip=True)
            if desc_text:
                details['product_description'] = desc_text

        # --- Part videos ---
        # video_section = soup.find('div', id='PartVideos')
        # if video_section:
        #     # Find all video containers
        #     video_containers = video_section.find_all('div', class_='yt-video')
        #     videos = []
        #     for vid_container in video_containers:
        #         yt_id = vid_container.get('data-yt-init')
        #         if yt_id:
        #             # Get video title from the following h4 or p tag
        #             title_tag = vid_container.find_next('h4')
        #             if not title_tag:
        #                 title_tag = vid_container.find_next('p')

        #             video_title = title_tag.get_text(strip=True) if title_tag else 'Part Installation Video'
                    
        #             videos.append({
        #                 'title': video_title,
        #                 'youtube_id': yt_id,
        #                 'url': f'https://www.youtube.com/watch?v={yt_id}'
        #             })

        #     if videos:
        #         details['part_videos'] = videos

        # --- Part videos ---
        video_section = soup.find('div', id='PartVideos')
        if video_section:
            videos = []
            
            # The actual video content is in the next sibling div with class "row"
            video_container_parent = video_section.find_next_sibling('div')
            
            if video_container_parent:
                # Find all video containers within the row
                video_containers = video_container_parent.find_all('div', class_='yt-video')
                
                for vid_container in video_containers:
                    yt_id = vid_container.get('data-yt-init')
                    
                    if yt_id:
                        # Find the title - it's in a preceding h4 tag at the same level or in parent
                        title_tag = None
                        
                        # Look for h4 in the parent container
                        parent_col = vid_container.find_parent('div', class_=lambda x: x and 'col' in str(x))
                        if parent_col:
                            title_tag = parent_col.find('h4')
                        
                        video_title = title_tag.get_text(strip=True) if title_tag else 'Part Installation Video'
                        
                        if video_title != "How Buying OEM Parts Can Save You Time and Money":
                            videos.append({
                                'title': video_title,
                                'youtube_id': yt_id,
                                'url': f'https://www.youtube.com/watch?v={yt_id}'
                            })
            
            if videos:
                details['part_videos'] = videos
        # --- Works with ---
        troubleshooting_section = soup.find('div', id='Troubleshooting')
        if troubleshooting_section:
            works_tag = troubleshooting_section.find('div', class_='bold', string=lambda s: s and 'works with the following products' in s.lower())
            if works_tag:
                ul = works_tag.find_next('ul', class_='list-disc')
                if ul:
                    details['works_with'] = [li.get_text(strip=True) for li in ul.find_all('li')]

        # --- Replaces ---
        if troubleshooting_section:
            replaces_tag = troubleshooting_section.find('div', class_='bold', string=lambda s: s and 'replaces' in s.lower())
            if replaces_tag:
                # The next div contains the part numbers
                next_div = replaces_tag.find_next_sibling('div')
                if next_div:
                    replaces_text = next_div.get_text(strip=True)
                    # Split by comma and clean up
                    replaces_list = [r.strip() for r in replaces_text.split(',') if r.strip()]
                    details['replaces'] = replaces_list

        # --- Fixes Symptoms ---
        if troubleshooting_section:
            fixes_tag = troubleshooting_section.find('div', class_='bold', string=lambda s: s and 'fixes the following symptoms' in s.lower())
            if fixes_tag:
                ul = fixes_tag.find_next('ul', class_='list-disc')
                if ul:
                    details['fixes_symptoms'] = [li.get_text(strip=True) for li in ul.find_all('li')]

        # --- Average customer rating and count ---
        rating_meta = soup.find('meta', {'itemprop': 'ratingValue'})
        if rating_meta:
            details['average_customer_rating'] = float(rating_meta.get('content', 0))

        review_count_meta = soup.find('meta', {'itemprop': 'reviewCount'})
        if review_count_meta:
            details['review_count'] = int(review_count_meta.get('content', 0))

        # --- Customer reviews (top visible only) ---
        reviews = []
        review_divs = soup.find_all('div', class_='pd__cust-review__submitted-review')
        for r in review_divs[:5]:  # limit to first 5 visible reviews
            # Get rating from stars
            rating_div = r.find('div', class_='rating')
            rating = 0
            if rating_div:
                stars_upper = rating_div.find('div', class_='rating__stars__upper')
                if stars_upper and stars_upper.get('style'):
                    # Extract percentage from style="width: 100%"
                    width_style = stars_upper.get('style', '')
                    if 'width:' in width_style:
                        percentage = width_style.split('width:')[1].split('%')[0].strip()
                        rating = round(float(percentage) / 20, 1)  # Convert to 5-star scale

            # Get reviewer and date from the header section
            header_div = r.find('div', class_='pd__cust-review__submitted-review__header')
            reviewer = ''
            review_date = ''
            if header_div:
                bold_span = header_div.find('span', class_='bold')
                if bold_span:
                    reviewer = bold_span.get_text(strip=True)
                # Date is the remaining text after the bold name
                full_text = header_div.get_text(strip=True)
                if ' - ' in full_text:
                    review_date = full_text.split(' - ')[-1]

            # Get title (bold div after the header/verified section)
            title_div = r.find('div', class_='bold')
            title = title_div.get_text(strip=True) if title_div else ''

            # Get content from js-searchKeys div
            content_div = r.find('div', class_='js-searchKeys')
            content = content_div.get_text(strip=True) if content_div else ''

            reviews.append({
                'title': title,
                'reviewer': reviewer,
                # 'date': review_date,
                'content': content,
                'rating': rating
            })

        if reviews:
            details['customer_reviews'] = reviews

        # --- Stock status ---
        stock_span = soup.find('span', {'itemprop': 'availability'})
        if stock_span:
            details['stock_status'] = stock_span.get_text(strip=True)

        return details


    def _fetch_url(self, url: str) -> Optional[str]:
        """
        Fetch URL with retry logic.

        Args:
            url: URL to fetch

        Returns:
            str: HTML content or None if failed
        """
        for attempt in range(1, RETRY_ATTEMPTS + 1):
            try:
                response = self.session.get(url, timeout=TIMEOUT)
                response.raise_for_status()

                logger.debug(f"Successfully fetched: {url}")
                return response.text

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

    def save_to_json(self, filepath: str = PARTS_RAW_FILE):
        """
        Save scraped data to JSON file.

        Args:
            filepath: Output file path
        """
        data = {
            'metadata': {
                'scraper_type': 'parts',
                'scraper_version': '1.0',
                'scraped_date': get_date_string(),
                'total_parts': len(self.documents),
                'failed_urls': len(self.failed_urls),
                'appliance_types': list(PARTS_APPLIANCES.keys())
            },
            'documents': self.documents,
            'failed_urls': self.failed_urls
        }

        success = save_json(data, filepath)

        if success:
            logger.info(f"Saved {len(self.documents)} parts to {filepath}")
        else:
            logger.error(f"Failed to save data to {filepath}")


def main():
    """Main entry point for running the parts scraper."""
    scraper = PartsScraper()

    try:
        # Scrape all appliances
        scraper.scrape_all_appliances()

        # Save results
        scraper.save_to_json()

        logger.info("\nScraping complete!")
        logger.info(f"Total parts: {scraper.total_scraped}")
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
