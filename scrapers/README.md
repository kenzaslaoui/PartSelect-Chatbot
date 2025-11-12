# PartSelect Scrapers

Web scrapers for extracting appliance repair data from PartSelect.com. Three specialized scrapers work together to collect comprehensive information about refrigerators and dishwashers.

## Overview

| Scraper | Purpose | Coverage | Output |
|---------|---------|----------|--------|
| **blog_scraper.py** | Repair articles, how-to guides, error codes | 5 blog topics | blogs_raw.json |
| **repair_scraper.py** | Symptom guides, troubleshooting, inspection steps | 21 symptoms (12 fridge, 9 dishwasher) | repair_symptoms_raw.json |
| **parts_scraper.py** | Parts catalog, pricing, availability, specifications | 43 brands, 1000s of parts | parts_raw.json |

## Quick Start

### Installation

```bash
# Install dependencies
pip install requests beautifulsoup4
```

### Running Scrapers

```bash
# From project root directory
python -m scrapers.blog_scraper
python -m scrapers.repair_scraper
python -m scrapers.parts_scraper
```

Or import in Python:

```python
from scrapers import BlogScraper, RepairScraper, PartsScraper

# Create scraper instances
blog = BlogScraper()
repair = RepairScraper()
parts = PartsScraper()

# Run and save data
blog.scrape_all_topics()
repair.scrape_all_appliances()
parts.scrape_all_appliances()
```

---

## Detailed Scraper Documentation

### 1. Blog Scraper (`blog_scraper.py`)

**Purpose:** Extract repair articles, how-to guides, error codes, and testing tutorials from PartSelect blog.

**Data Extracted:**
- Article title, subtitle, and content (HTML + plain text)
- Images and embedded videos
- Brand detection (GE, Samsung, LG, etc.)
- Appliance type classification (refrigerator/dishwasher)
- Part numbers (PartSelect and manufacturer)
- Publication metadata

**Coverage:**
- 5 blog topics:
  - `repair`: General repair guides and troubleshooting
  - `error-codes`: Error code explanations and solutions
  - `how-to-guides`: Installation and setup guides
  - `testing`: Parts testing tutorials
  - `use-and-care`: Maintenance and care guides
- Pagination support (follows "OLDER" button links)
- 50+ articles total

**Features:**
- Intelligent title filtering (only refrigerator/dishwasher content)
- Interactive scraping (prompts user every 50 articles to continue)
- Automatic checkpointing (saves progress every 25 articles)
- Robust retry logic (5 attempts with exponential backoff)
- Polite delays between requests (2-4 seconds random)
- Deduplication by URL

**Output:** `data/raw/blogs_raw.json`
- Each article is a document with title, content, images, videos, metadata
- Includes appliance type and brand information
- Plain text version of content for RAG indexing

**Runtime:** ~5-10 minutes

**Example Usage:**
```python
from scrapers import BlogScraper

scraper = BlogScraper()
results = scraper.scrape_all_topics()
scraper.save_to_json('data/raw/blogs_raw.json')

print(f"Scraped {scraper.total_scraped} articles")
print(f"Failed: {len(scraper.failed_urls)} URLs")
```

---

### 2. Repair Scraper (`repair_scraper.py`)

**Purpose:** Extract repair symptom guides, troubleshooting information, and step-by-step inspection procedures.

**Data Extracted:**
- Symptom name and difficulty level (EASY/MEDIUM/HARD)
- Repair story/introduction text
- YouTube video tutorials with thumbnails
- Related parts with descriptions and repair guides
- Step-by-step inspection instructions
- Links to detailed repair guide pages

**Coverage:**
- 12 refrigerator symptoms:
  - Noisy, Leaking, Won't Start, Ice Maker Not Making Ice
  - Fridge Too Warm, Not Dispensing Water, Door Sweating
  - Light Not Working, Fridge Too Cold, Freezer Too Cold
  - Fridge and Freezer Too Warm, Fridge Runs Too Long

- 9 dishwasher symptoms:
  - Noisy, Leaking, Won't Start, Door Latch Failure
  - Not Cleaning Dishes, Not Draining, Won't Fill With Water
  - Won't Dispense Detergent, Not Drying Dishes

**Features:**
- Two-level scraping (main page → individual symptom pages)
- Extraction of linked repair guide content (all paragraphs and steps)
- Organized inspection steps by part name
- YouTube video ID extraction from data attributes
- Part descriptions with repair guide links
- No pagination needed (simpler than blog scraper)

**Output:** `data/raw/repair_symptoms_raw.json`
- Each symptom is a document with:
  - Difficulty level
  - Repair story
  - YouTube video info (ID, URL, thumbnail)
  - Parts with descriptions and repair guides
  - Inspection steps organized by part

**Runtime:** ~90 seconds for all symptoms

**Example Usage:**
```python
from scrapers import RepairScraper

scraper = RepairScraper()
result = scraper.scrape_all_appliances()
scraper.save_to_json('data/raw/repair_symptoms_raw.json')

print(f"Scraped {scraper.total_scraped} symptoms")
print(f"Video tutorials: {count_videos(result)}")
```

---

### 3. Parts Scraper (`parts_scraper.py`)

**Purpose:** Extract complete parts catalog with pricing, availability, and specifications.

**Data Extracted:**
- Part name and description
- PartSelect part number
- Manufacturer part number
- Price (current price, list price)
- Stock status (in stock, limited stock, discontinued)
- Part type category
- Compatible brand
- Product specifications

**Coverage:**
- 43 brands (GE, Samsung, LG, Whirlpool, KitchenAid, Maytag, Bosch, Frigidaire, etc.)
- Refrigerator and dishwasher parts
- Part types: Motors, Seals, Heaters, Control Boards, etc.
- 1000s of individual parts

**Features:**
- Three-level navigation:
  1. Appliance type (refrigerator/dishwasher)
  2. Part type category (motors, seals, heaters, etc.)
  3. Brand filtering
  4. Individual part extraction
- Pagination support for large part listings
- Stock status tracking (in stock, limited, discontinued)
- Price extraction with currency handling
- Brand recognition (43+ brands with variations)

**Output:** `data/raw/parts_raw.json`
- Each part is a document with:
  - Name, description, part numbers
  - Pricing information
  - Stock status
  - Brand and appliance type
  - Part category

**Runtime:** ~30-45 minutes

**Example Usage:**
```python
from scrapers import PartsScraper

scraper = PartsScraper()
result = scraper.scrape_all_appliances()
scraper.save_to_json('data/raw/parts_raw.json')

print(f"Scraped {scraper.total_scraped} parts")
print(f"Brands: {len(scraper.brands_found)}")
```

---

## Configuration

All scraper settings are centralized in `config.py`:

**Key Settings:**
- `REQUEST_DELAY_MIN/MAX`: 2.0-4.0 seconds between requests
- `RETRY_ATTEMPTS`: 5 attempts with exponential backoff
- `TIMEOUT`: 30 seconds per request
- `USER_AGENT`: Transparent identification
- `MAX_CONTENT_LENGTH`: 100KB per article
- `MIN_CONTENT_LENGTH`: 200 characters minimum

**CSS Selectors:**
- Blog selectors: Article cards, titles, content, images, videos
- Repair selectors: Symptoms, difficulty, parts, videos
- Parts selectors: Part containers, titles, prices, stock

**Brands:** 43 canonical brand names with variations (GE → ['ge', 'general electric', 'g.e.'])

**Keywords:** Appliance-specific keywords for filtering content

---

## Shared Utilities (`utils.py`)

The `utils.py` module provides 20+ helper functions used across all scrapers:

**Text Processing:**
- `strip_html()`: Convert HTML to plain text
- `extract_first_paragraph()`: Get first paragraph for summaries
- `truncate_text()`: Limit text to MAX_CONTENT_LENGTH

**Brand & Parts:**
- `extract_brand()`: Detect brand from text
- `extract_part_numbers()`: Extract PartSelect and manufacturer numbers
- `extract_multiple_brands()`: Extract all brands mentioned

**Video Extraction:**
- `extract_youtube_id()`: Parse YouTube ID from data attributes
- `extract_youtube_url()`: Generate YouTube URL
- `extract_youtube_thumbnail()`: Generate thumbnail URL

**URLs:**
- `make_absolute_url()`: Convert relative to absolute URLs
- `is_valid_image_url()`: Validate image extensions

**Data Validation:**
- `validate_document()`: Check required fields
- `validate_content_length()`: Verify content within bounds
- `deduplicate_by_url()`: Remove duplicate documents

**File Operations:**
- `save_json()`: Save data with error handling
- `load_json()`: Load data with error handling
- `file_exists()`: Check file existence

**Utilities:**
- `generate_document_id()`: Create formatted IDs (blog_0001)
- `get_timestamp()`: ISO 8601 format
- `print_progress()`: Progress indicator

---

## Output Data Format

All scrapers output JSON files with consistent structure:

```json
{
  "metadata": {
    "scraper_type": "blog|repair|parts",
    "scraper_version": "1.0",
    "scraped_date": "2024-11-12",
    "total_documents": 50,
    "failed_urls": 0
  },
  "documents": [
    {
      "id": "blog_0001",
      "source_type": "blog_article|repair_symptom|part",
      "appliance_type": "refrigerator|dishwasher",
      "... document-specific fields ..."
    }
  ],
  "failed_urls": []
}
```

---

## Responsible Web Scraping

All scrapers follow ethical web scraping practices:

1. **Polite Delays:** 2-4 second random delays between requests
2. **Transparent Identification:** Uses Mozilla user agent with version info
3. **Retry Logic:** Exponential backoff (3^n seconds) for failed requests
4. **Graceful Degradation:**
   - 404s fail immediately (page doesn't exist)
   - 403s retry (might be temporary rate limiting)
   - Timeouts retry with backoff
5. **Session Management:** Proper headers and referer handling
6. **Progress Tracking:** Logs all requests and saves checkpoints

---

## Troubleshooting

**Issue: Scrapers are slow**
- Normal behavior; polite delays are intentional
- Blog scraper: 5-10 minutes for 50+ articles
- Repair scraper: ~90 seconds for 21 symptoms
- Parts scraper: 15-30 minutes (depends on pagination)

**Issue: Getting 403 Forbidden errors**
- Scraper will retry automatically (up to 5 times)
- Check `scraper.log` for details
- May need to increase delays in `config.py`

**Issue: CSS selectors not matching**
- PartSelect may have updated their HTML structure
- Check the actual page source and update selectors in `config.py`
- Fallback selectors can be added to `utils.py`

**Issue: Missing content in output**
- Check content length limits in `config.py` (MIN/MAX_CONTENT_LENGTH)
- Verify required fields are present
- Review failed_urls list in JSON output

---

## Development

### Adding a New Scraper

1. Create new scraper file (e.g., `new_scraper.py`)
2. Import config and utils:
   ```python
   from .config import TIMEOUT, USER_AGENT
   from .utils import make_absolute_url, save_json
   ```
3. Create scraper class following BlogScraper pattern:
   - Initialize with requests.Session()
   - Implement scraping methods
   - Add logging with `logger`
   - Return data with metadata
4. Update `__init__.py` to export new class
5. Add documentation to this README

### Modifying Selectors

CSS selectors are in `config.py`. When PartSelect updates their HTML:

1. Inspect the page source
2. Update the selector in `BLOG_SELECTORS`, `REPAIR_SELECTORS`, or `PARTS_SELECTORS`
3. Add a comment with the date and reason for change
4. Test with actual page before committing

---

## Output Examples

See [../data/raw/](../data/raw/) for actual scraped data examples:
- `blogs_raw.json`: Blog articles
- `repair_symptoms_raw.json`: Repair guides
- `parts_raw.json`: Parts catalog

---

## Testing

To test scrapers without scraping the full website:

```python
from scrapers import BlogScraper

scraper = BlogScraper()

# Test single topic
scraper._scrape_topic('repair')

# Test single URL
html = scraper._fetch_url('https://www.partselect.com/blog/topics/repair/')
articles = scraper._parse_article_links(html, ...)
```
