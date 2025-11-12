# PartSelect Web Scrapers

Comprehensive web scraping suite for extracting refrigerator and dishwasher data from PartSelect:
- Blog articles (repair guides, how-tos, error codes)
- Repair symptoms (troubleshooting guides with videos)
- Parts catalog (parts with prices and specifications)

## Features

✅ **Smart Filtering** - Only scrapes refrigerator/dishwasher content
✅ **Interactive Scraping** - User prompts every 50 articles
✅ **Auto-Checkpointing** - Saves progress every 25 articles
✅ **Robust Error Handling** - Retry logic with exponential backoff
✅ **Polite Scraping** - Random delays (1-2s) between requests
✅ **Deduplication** - Removes duplicate articles by URL
✅ **Rich Data Extraction** - Title, content, images, videos, part numbers, brands


## Usage

### Blog Scraper

```bash
# Run the blog scraper
python -m scrapers.blog_scraper

# Resume from checkpoint
python -m scrapers.blog_scraper --resume

# Custom output location
python -m scrapers.blog_scraper --output data/my_custom_output.json
```

### Repair Scraper

```bash
# Run the repair symptoms scraper
python -m scrapers.repair_scraper
```

### Parts Scraper

```bash
# Run the parts catalog scraper
python -m scrapers.parts_scraper
```

## What Gets Scraped

### Blog Topics

1. **repair** - Appliance repair articles
2. **error-codes** - Error code troubleshooting
3. **how-to-guides** - Installation and how-to guides
4. **testing** - Parts testing tutorials
5. **use-and-care** - Maintenance guides

### Filtering Keywords

**Refrigerator Keywords:**
- fridge, refrigerator, freezer, icemaker, ice maker, defrost, ice dispenser, water dispenser, cooling, crisper

**Dishwasher Keywords:**
- dishwasher, dish washer, rinse aid, detergent dispenser, spray arm, dish rack

### Repair Symptoms

Scrapes all repair symptom pages for refrigerators and dishwashers:
- Symptom names (e.g., "Not cooling", "Won't drain")
- Difficulty levels
- Repair stories and troubleshooting tips
- YouTube video tutorials
- Related parts with prices
- Step-by-step inspection guides with images

### Parts Catalog

Scrapes entire parts catalog with three-level navigation:
1. **Appliance Type** → Refrigerator or Dishwasher
2. **Part Type** → Door parts, ice maker parts, control boards, etc.
3. **Brand** → All 43 supported brands

For each brand/part-type combination, scrapes all parts with pagination support.

### Data Extracted

#### Blog Articles

Each article includes:

```json
{
  "id": "blog_0001",
  "source_type": "blog",
  "appliance_type": "refrigerator",
  "brand": "LG",
  "title": "How to Replace an LG Refrigerator's Water Filter",
  "subtitle": "What you need for good tasting water!",
  "url": "https://www.partselect.com/blog/...",
  "topic_category": "how-to-guides",
  "content_html": "<p>...</p>",
  "content_text": "Plain text version...",
  "summary": "First paragraph...",
  "images": ["https://...image1.png", "https://...image2.png"],
  "videos": ["https://www.youtube.com/embed/abc123"],
  "parts_mentioned": {
    "partselect": ["PS11752778"],
    "manufacturer": ["WPW10321304"]
  },
  "scraped_at": "2024-11-11T14:23:45.123456"
}
```

#### Repair Symptoms

Each symptom includes:

```json
{
  "id": "repair_0001",
  "source_type": "repair_symptom",
  "appliance_type": "refrigerator",
  "symptom_name": "Ice maker not making ice",
  "url": "https://www.partselect.com/Repair/...",
  "difficulty": "Easy",
  "repair_story": "Common causes and troubleshooting steps...",
  "video": {
    "video_id": "abc123xyz",
    "video_url": "https://www.youtube.com/watch?v=abc123xyz",
    "thumbnail_url": "https://img.youtube.com/vi/abc123xyz/hqdefault.jpg"
  },
  "parts": [
    {
      "name": "Ice Maker Assembly",
      "part_number": "WPW10190965",
      "price": "$89.99",
      "url": "https://www.partselect.com/PS11752778",
      "image_url": "https://...image.jpg"
    }
  ],
  "inspection_steps": [
    {
      "step_number": 1,
      "title": "Check water supply",
      "description": "Ensure water valve is turned on...",
      "image_url": "https://...step1.jpg"
    }
  ],
  "scraped_at": "2024-11-11T14:23:45.123456"
}
```

#### Parts

Each part includes:

```json
{
  "id": "part_0001",
  "source_type": "part",
  "appliance_type": "refrigerator",
  "part_type": "Ice Maker Parts",
  "brand": "Whirlpool",
  "title": "Ice Maker Assembly",
  "partselect_number": "PS11752778",
  "manufacturer_number": "WPW10190965",
  "price": "$89.99",
  "stock_status": "In Stock",
  "url": "https://www.partselect.com/PS11752778",
  "image_url": "https://...part-image.jpg",
  "scraped_at": "2024-11-11T14:23:45.123456"
}
```

## Output Structure

```
data/
├── raw/
│   ├── blogs_raw.json              # Blog articles
│   ├── repair_symptoms_raw.json    # Repair symptoms
│   └── parts_raw.json              # Parts catalog
├── processed/
│   ├── blogs.json                  # (Future: processed/cleaned data)
│   ├── repair_symptoms.json        # (Future: processed/cleaned data)
│   └── parts.json                  # (Future: processed/cleaned data)
├── combined/
│   └── all_documents.json          # (Future: all sources combined)
└── checkpoints/
    └── blog_checkpoint.json        # Auto-saved checkpoints (blog only)
```

## Output Format

```json
{
  "metadata": {
    "scraper_type": "blog",
    "scraper_version": "1.0",
    "scraped_date": "2024-11-11T14:23:45",
    "total_articles": 89,
    "filtered_articles": 150,
    "failed_urls": 2,
    "topics_scraped": ["repair", "error-codes", "how-to-guides", "testing", "use-and-care"],
    "filters_applied": {
      "refrigerator_keywords": true,
      "dishwasher_keywords": true
    }
  },
  "documents": [
    { /* article 1 */ },
    { /* article 2 */ },
    ...
  ],
  "failed_urls": [
    "https://www.partselect.com/blog/failed-article/"
  ]
}
```

## Configuration

All settings can be customized in [`scrapers/config.py`](scrapers/config.py):

```python
# Scraper behavior
REQUEST_DELAY_MIN = 1.0          # Min delay between requests (seconds)
REQUEST_DELAY_MAX = 2.0          # Max delay between requests (seconds)
RETRY_ATTEMPTS = 3               # Number of retry attempts
TIMEOUT = 30                     # Request timeout (seconds)

# Interactive settings
ARTICLE_PROMPT_INTERVAL = 50     # Prompt user every N articles
CHECKPOINT_INTERVAL = 25         # Save checkpoint every N articles

# Content validation
MIN_CONTENT_LENGTH = 200         # Minimum content length (characters)
MAX_CONTENT_LENGTH = 100000      # Maximum content length (characters)
```

## Architecture

### Module Structure

```
scrapers/
├── __init__.py           # Package initialization
├── config.py             # Configuration constants
├── utils.py              # Shared utility functions
├── blog_scraper.py       # Blog article scraper
├── repair_scraper.py     # Repair symptom scraper
└── parts_scraper.py      # Parts catalog scraper
```

### Key Components

1. **BlogScraper Class** - Blog article scraper
   - Two-level scraping: topic pages → individual articles
   - Smart filtering by keywords
   - Interactive prompts and checkpointing
   - `scrape_all_topics()` - Entry point
   - `_scrape_topic()` - Scrape single topic
   - `_scrape_article()` - Scrape individual article

2. **RepairScraper Class** - Repair symptom scraper
   - Two-level scraping: main repair page → symptom pages
   - No filtering needed (all symptoms are relevant)
   - Extracts YouTube videos, parts, and inspection steps
   - `scrape_all_appliances()` - Entry point
   - `_scrape_appliance()` - Scrape single appliance type
   - `_scrape_symptom_page()` - Scrape individual symptom

3. **PartsScraper Class** - Parts catalog scraper
   - Three-level scraping: appliance → part type → brand → parts
   - Pagination support for large part lists
   - Extracts prices, stock status, and specifications
   - `scrape_all_appliances()` - Entry point
   - `_scrape_appliance()` - Scrape single appliance type
   - `_scrape_part_type()` - Scrape part type page
   - `_scrape_brand_page()` - Scrape brand page with pagination

4. **Utility Functions** (in `utils.py`)
   - `extract_brand()` - Brand detection
   - `extract_part_numbers()` - Part number extraction
   - `extract_appliance_type()` - Appliance type detection
   - `extract_video_urls()` - Video extraction for blogs
   - `extract_youtube_id()` - YouTube ID extraction for repair pages
   - `is_relevant_article()` - Relevance filtering
   - `validate_document()` - Data validation

5. **Configuration** (in `config.py`)
   - 43 appliance brands with variations
   - Keywords and patterns
   - URL settings for all scrapers
   - Scraper behavior settings
   - HTML selectors for all page types

## Error Handling

The scraper includes robust error handling:

- **Retry Logic**: 3 attempts with exponential backoff
- **Timeout Protection**: 30-second timeout per request
- **Failed URL Tracking**: All failed URLs are logged
- **Checkpoint Recovery**: Resume from last checkpoint
- **Validation**: Content length and required fields validation

## Logging

Logs are saved to `scrapers/scraper.log`:

```
2024-11-11 14:23:45 - BlogScraper - INFO - Starting blog scraping for 5 topics
2024-11-11 14:23:46 - BlogScraper - INFO - Scraping topic: repair
2024-11-11 14:23:47 - BlogScraper - INFO - Scraping article: How to Fix LG Ice Maker
...
```

## Best Practices

### Be Polite

- Random delays (1-2 seconds) between requests
- Respect robots.txt
- Use descriptive User-Agent
- Don't overwhelm servers

### Data Quality

- Filter before scraping (saves bandwidth)
- Validate all extracted data
- Handle missing fields gracefully
- Deduplicate by URL

### Reliability

- Save checkpoints frequently
- Implement retry logic
- Log all errors
- Track failed URLs

## Troubleshooting

### Scraper stops unexpectedly

Resume from checkpoint:
```bash
python -m scrapers.blog_scraper --resume
```

### HTTP 429 (Too Many Requests)

Increase delays in `config.py`:
```python
REQUEST_DELAY_MIN = 2.0
REQUEST_DELAY_MAX = 4.0
```

### HTML structure changed

Update selectors in `config.py`:
- `BLOG_SELECTORS` for blog scraper
- `REPAIR_SELECTORS` for repair scraper
- `PARTS_SELECTORS` for parts scraper

### Memory issues

Reduce `MAX_CONTENT_LENGTH` in `config.py`.

## Future Enhancements

- [ ] Data processing pipeline (clean and normalize scraped data)
- [ ] Image downloading and local storage
- [ ] Video metadata extraction
- [ ] Multi-threading support for faster scraping
- [ ] Database integration (PostgreSQL or MongoDB)
- [ ] Web UI for monitoring scraping progress
- [ ] Incremental updates (only scrape new/changed content)

