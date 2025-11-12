# RAG System & Data Pipeline

This directory contains the Retrieval-Augmented Generation (RAG) system that powers PartSelect's agentic agents. It handles data ingestion, processing, indexing, and intelligent retrieval across multiple data sources.

## System Overview

The RAG system follows a complete pipeline:

```
Raw Data
    ↓
Data Processing (Chunking, Metadata extraction)
    ↓
Embedding Generation (Vector representations)
    ↓
ChromaDB Indexing (4 separate collections)
    ↓
Agent-Specific Retrievers (Intelligent filtering & search)
    ↓
Agents & LLM (Deepseek reasoning with retrieved context)
```

## Data Sources & Collections

PartSelect ingests and indexes data from three sources into **four separate ChromaDB collections**:

### Collection Structure

```
ChromaDB Instance
├── parts_refrigerator
│   ├─ ~6,500 refrigerator parts
│   ├─ Metadata: brand, type, price, stock, rating, installation_time
│   └─ Used by: PartSearchRetriever, CompatibilityRetriever
│
├── parts_dishwasher
│   ├─ ~6,500 dishwasher parts
│   ├─ Metadata: brand, type, price, stock, rating, installation_time
│   └─ Used by: PartSearchRetriever, CompatibilityRetriever
│
├── blogs_articles
│   ├─ ~200-300 chunks from repair/installation blogs
│   ├─ Max 512 tokens per chunk with 100-token overlap
│   ├─ Metadata: topic_category, appliance_type, section_header, video_presence
│   └─ Used by: TroubleshootingRetriever, InstallationRetriever
│
└── repair_symptoms
    ├─ ~300-400 chunks from repair guides
    ├─ Separated by: part + inspection step + repair type
    ├─ Metadata: symptom_name, part_name, difficulty, video_url, repair_guide_type
    └─ Used by: TroubleshootingRetriever, InstallationRetriever
```

## Data Processing Architecture

### 1. PartsProcessor - No Chunking

**Strategy:** Keep parts as individual documents

**Rationale:**
- Each part is self-contained (name, specs, price, reviews)
- No benefit to chunking - you want the complete part info
- Rich metadata enables precise filtering

**What gets indexed:**
```
Document = {
    "id": "part_12345",
    "content": "{title} {description} {specifications}",
    "metadata": {
        "title": "Water Dispenser PS123456",
        "brand": "LG",
        "part_type": "water dispenser",
        "price": 89.99,
        "stock_status": "in_stock",
        "average_customer_rating": 4.8,
        "review_count": 127,
        "installation_type": "DIY",
        "average_installation_time": "30 minutes",
        "partselect_number": "PS123456",
        "manufacturer_number": "AEQ73110302",
        "url": "https://..."
    }
}
```

**Collections:**
- `parts_refrigerator` - All refrigerator parts
- `parts_dishwasher` - All dishwasher parts

---

### 2. BlogsProcessor - Intelligent Chunking

**Strategy:** Chunk by section/paragraph, preserve context

**Chunking Parameters:**
- Max chunk size: 512 tokens (~1,500-2,000 characters)
- Overlap: 100 tokens (preserves context across chunks)
- Split on: Section headers, paragraphs

**Rationale:**
- 512 tokens balances precision vs. context
- Overlap helps maintain semantic continuity
- Sections kept together for relevance

**What gets indexed:**
```
Document = {
    "id": "blog_article_chunk_42",
    "content": "Section excerpt (512 tokens max)...",
    "metadata": {
        "title": "How to Fix a Leaking Refrigerator",
        "appliance_type": "refrigerator",
        "topic_category": "repair",
        "section_header": "Step 1: Identify the Leak Source",
        "chunk_number": 2,
        "total_chunks": 5,
        "has_video": true,
        "video_url": "https://youtube.com/...",
        "url": "https://blog.partselect.com/..."
    }
}
```

**Collection:**
- `blogs_articles` - All blog chunks (both refrigerator & dishwasher)

---

### 3. RepairProcessor - Part-Based Chunking

**Strategy:** Chunk by part + repair guide type

**Chunking Parameters:**
- One chunk per part description
- Separate chunks for: "testing" vs "replacement" guides
- Include: symptom, parts involved, steps, difficulty, video

**Rationale:**
- Part-based chunking maintains repair context
- Separates diagnostic (testing) from action (replacement) guides
- Video links crucial for repair agents

**What gets indexed:**
```
Document = {
    "id": "repair_guide_water_dispenser_replacement_1",
    "content": "Water dispenser replacement guide...",
    "metadata": {
        "symptom_name": "No water dispensing",
        "appliance_type": "refrigerator",
        "part_name": "Water Dispenser",
        "difficulty": "easy",
        "repair_guide_type": "replacement",  # or "testing"
        "repair_guide_title": "How to Replace a Water Dispenser",
        "has_video": true,
        "video_url": "https://youtube.com/...",
        "video_id": "abc123def",
        "url": "https://..."
    }
}
```

**Collection:**
- `repair_symptoms` - All repair guide chunks

---

## Retrieval Layer

Each agent uses specialized retrievers optimized for its task:

### 1. PartSearchRetriever

**Purpose:** Find parts by natural language description

**Query Flow:**
```
User: "Find a water dispenser for my LG refrigerator"
    ↓
Extract entities: appliance="refrigerator", brand="LG", part="water dispenser"
    ↓
Query parts_refrigerator with filters: brand="LG"
    ↓
Vector search on filtered results
    ↓
Rerank by: stock status + customer rating
    ↓
Return top 5 parts with all metadata
```

**Supported Filters:**
- `appliance_type`: "refrigerator" or "dishwasher"
- `brand`: Filter by manufacturer
- `in_stock_only`: Only in-stock items
- `price_range`: Min/max price filtering

**Returns:**
```python
{
    "query": "water dispenser",
    "filters": {"appliance_type": "refrigerator", "brand": "LG"},
    "total_results": 12,
    "results": [
        {
            "id": "part_123",
            "title": "Water Dispenser PS123456",
            "brand": "LG",
            "price": 89.99,
            "rating": 4.8,
            "review_count": 127,
            "stock_status": "in_stock",
            "relevance_score": 0.95
        },
        # ... more results
    ]
}
```

---

### 2. CompatibilityRetriever

**Purpose:** Check if specific parts are compatible with appliance models

**Query Flow:**
```
User: "Is part PS12345 compatible with my LG model WDT780?"
    ↓
Extract: part_id="PS12345", model="WDT780"
    ↓
Query both collections (refrigerator + dishwasher) for compatibility
    ↓
Vector search + metadata matching
    ↓
Return compatible parts with fit information
```

**Supported Filters:**
- `model_number`: Find parts for specific model
- `part_type`: Narrow by part category
- `appliance_type`: Refrigerator or dishwasher

---

### 3. TroubleshootingRetriever

**Purpose:** Get repair guides and diagnostic information

**Search Strategy:** Hybrid (BM25 + Vector)

**Rationale for Hybrid:**
- Error codes (E5, F02) require exact keyword matching (BM25)
- Symptom descriptions benefit from semantic matching (Vector)
- Hybrid combines both for robustness

**Query Flow:**
```
User: "My dishwasher has an E5 error"
    ↓
Extract: appliance="dishwasher", symptom="E5 error"
    ↓
HYBRID SEARCH on repair_symptoms:
  - BM25: Find exact "E5" matches
  - Vector: Find semantic matches "error E5", "malfunction code"
  - Combine: Score = (BM25_score * 0.5) + (Vector_score * 0.5)
    ↓
Fall back to pure vector search if hybrid unavailable
    ↓
Query blogs_articles for additional context
    ↓
Boost results with video tutorials
    ↓
Return by difficulty level and relevance
```

**Supported Filters:**
- `appliance_type`: Refrigerator or dishwasher
- `difficulty`: "easy", "medium", "hard"
- `include_videos`: Prioritize video tutorials

**Returns:**
```python
{
    "issue": "E5 error code",
    "search_type": "hybrid",
    "total_results": 8,
    "results": [
        {
            "id": "repair_123",
            "source": "repair_guide",
            "symptom": "E5 Error Code",
            "difficulty": "medium",
            "has_video": true,
            "vector_score": 0.92,
            "keyword_score": 0.98,
            "hybrid_score": 0.95,
            "search_method": "hybrid"  # or "vector" or "keyword"
        },
        # ... more results
    ]
}
```

---

### 4. InstallationRetriever

**Purpose:** Get step-by-step installation guides

**Search Strategy:** Hybrid (BM25 + Vector)

**Rationale for Hybrid:**
- Part names require exact matching (BM25)
- Installation concepts benefit from semantic matching (Vector)

**Query Flow:**
```
User: "How do I install a water pump?"
    ↓
Extract: part_name="water pump", appliance_type=None (could be either)
    ↓
HYBRID SEARCH on repair_symptoms (replacement guides):
  - Filter where repair_guide_type="replacement"
  - BM25 + Vector search
    ↓
Query blogs_articles for additional installation guides
    ↓
Query parts catalog for time estimates
    ↓
Combine results: guides + time estimates + difficulty
    ↓
Return complete installation information
```

**Supported Filters:**
- `part_number`: PartSelect or manufacturer part number
- `part_name`: Natural language part name
- `appliance_type`: Refrigerator or dishwasher

---

## Optimization Strategies

### 1. Metadata Filtering (Query Optimization)

**Pattern:** Filter BEFORE vector search, not after

**Why:** Reduces search space, faster results, better ranking

```python
# GOOD: Filter first
results = collection.query(
    query_texts=["water dispenser"],
    where={"brand": "LG", "stock_status": "in_stock"},  # Filter BEFORE
    n_results=5
)

# LESS EFFICIENT: Search all, then filter
results = collection.query(
    query_texts=["water dispenser"],
    n_results=100  # Search everything
)
results = [r for r in results if r["brand"] == "LG"]  # Filter after
```

**Metadata Filters Available:**

Parts collections:
- `brand`: Manufacturer name
- `stock_status`: "in_stock", "out_of_stock"
- `part_type`: Category
- `price`: Numeric range

Repair collections:
- `appliance_type`: "refrigerator", "dishwasher"
- `difficulty`: "easy", "medium", "hard"
- `repair_guide_type`: "testing", "replacement"
- `has_video`: true/false

---

### 2. Result Reranking

**Pattern:** Get more results than needed, rerank by business logic

```python
# Get 20 results, rerank to return top 5
results = retriever.retrieve_parts(
    query="water dispenser",
    brand="LG",
    top_k=20  # Get extra
)

# Rerank by: stock status + rating
results.sort(key=lambda x: (
    0 if x["stock_status"] == "in_stock" else 1,  # In-stock first
    -x["rating"]  # Then highest rated
))

return results[:5]  # Return top 5
```

---

### 3. Conversation Context Caching

**Pattern:** Cache search results for follow-up queries

**Why:** Avoid redundant searches, faster multi-turn conversations

```python
# Initial search
ConversationContext = {
    "last_search": {
        "query": "water dispenser",
        "appliance": "refrigerator",
        "brand": "LG",
        "results": [part1, part2, part3, ...],
        "timestamp": now()
    }
}

# Follow-up: "Show me reviews for these parts"
→ Use cached results, don't re-search

# Follow-up: "Any in black color?"
→ Filter cached results by color metadata, don't re-search

# Follow-up: "Find all Samsung water dispensers"
→ New search (different criteria), cache new results
```

This is already implemented in [orchestrator.py](../agents/orchestrator.py) with `previous_results` tracking.

---

### 4. Embedding Model Choice

**Recommendation:** `sentence-transformers/all-MiniLM-L6-v2`

**Why:**
- Small footprint (22MB)
- Fast inference
- Free to use
- Good quality for home appliance domain
- Handles both technical and descriptive text well

**Performance Characteristics:**
- Dimension: 384
- Speed: ~1000 sentences/second on CPU
- Quality: Competitive with larger models for retrieval tasks

**Alternative:** Fine-tune on repair queries for domain-specific improvements, but all-MiniLM is sufficient for MVP.

---

### 5. ChromaDB HNSW Configuration

**Default Settings (Recommended):**

For PartSelect's dataset size (13K parts + 500 blog chunks), default ChromaDB settings are optimal:

```python
from chromadb.config import Settings

settings = Settings(
    chroma_db_impl="duckdb+parquet",
    is_persistent=True,
    anonymized_telemetry=False,
    hnsw_space="cosine"  # Distance metric: cosine similarity
)

client = chromadb.Client(settings)
```

**HNSW Parameters (Advanced Tuning):**

```python
# Only adjust if you have performance issues:
{
    "hnsw": {
        "space": "cosine",      # or "l2" (Euclidean)
        "ef": 100,              # Search parameter (balance speed vs accuracy)
        "ef_construction": 200,  # Construction parameter
        "max_m": 16             # Maximum connections per node
    }
}

# Tuning guidance:
# - ef: 50 (fast), 100 (balanced), 200 (accurate)
# - max_m: 8 (small), 16 (balanced), 32 (thorough)
# Trade-off: Higher values = slower search, better accuracy
```

**For PartSelect:** Default settings are more than enough. Only tune if:
- Search latency > 100ms (unlikely at this scale)
- Relevance score variance is high

---

### 6. Hybrid Search (BM25 + Vector)

**When to Use Hybrid:**

Use hybrid search when:
- Exact keyword matching is important (error codes, part names)
- Semantic similarity alone isn't enough
- You want robustness against edge cases

**TroubleshootingRetriever & InstallationRetriever use hybrid search** because:
- Error codes (E5, F02) are exact keywords
- Part names (water dispenser, ice maker) are specific terms
- Hybrid combines keyword precision with semantic understanding

**How It Works:**

```
Query: "water dispenser error E5"

BM25 Search (Keyword):
- Finds documents containing "water dispenser" AND "E5"
- Scores: 0.98 (exact match)

Vector Search (Semantic):
- Finds semantic matches: "water dispenser problem", "error code"
- Scores: 0.85 (similar meaning)

Hybrid Combination (50-50 weight):
- Final score = (0.98 * 0.5) + (0.85 * 0.5) = 0.915
- Combines precision and recall
```

**Fallback Strategy:**

If hybrid search unavailable, automatically fall back to pure vector search. This is already implemented in the retrievers.

---

## Implementation Files

### Core Components

- **`chroma_db.py`** - ChromaDB connection and collection management
- **`retrieval.py`** - Agent-specific retriever classes
  - PartSearchRetriever
  - CompatibilityRetriever
  - TroubleshootingRetriever
  - InstallationRetriever
- **`hybrid_search.py`** - BM25 + Vector hybrid search implementation
- **`processors.py`** - Data processing (PartsProcessor, BlogsProcessor, RepairProcessor)
- **`chunking.py`** - Intelligent chunking algorithms

### Data Population

- **`populate_chroma.py`** - Ingests raw data and populates collections
- Data files located in `data/raw/` and `data/processed/`

---

## Typical Query Examples

### Example 1: Part Search

```
User: "Find me an inexpensive water dispenser for my LG refrigerator"

Flow:
1. Orchestrator extracts: appliance="refrigerator", brand="LG", part="water dispenser"
2. PartSearchRetriever.retrieve_parts(
     query="water dispenser",
     appliance_type="refrigerator",
     brand="LG"
   )
3. Query parts_refrigerator collection
4. Filters: brand="LG"
5. Vector search: "water dispenser"
6. Results reranked by: stock status + price + rating
7. Returns top 5 results with full metadata
```

### Example 2: Troubleshooting

```
User: "My dishwasher is making a strange noise"

Flow:
1. Orchestrator extracts: appliance="dishwasher", symptom="strange noise"
2. TroubleshootingRetriever.retrieve_troubleshooting_guides(
     issue_description="strange noise",
     appliance_type="dishwasher"
   )
3. HYBRID search on repair_symptoms + blogs_articles
4. BM25 finds: exact "noise" matches
5. Vector search finds: semantic matches "sound", "rattling"
6. Hybrid combines both with equal weight
7. Boost results with video tutorials
8. Returns guides sorted by relevance + difficulty
```

### Example 3: Installation

```
User: "How do I install a new pump in my refrigerator?"

Flow:
1. Orchestrator extracts: part="pump", appliance="refrigerator"
2. InstallationRetriever.retrieve_installation_guides(
     part_name="pump",
     appliance_type="refrigerator"
   )
3. HYBRID search on repair_symptoms (filter: repair_guide_type="replacement")
4. Query blogs_articles for additional guides
5. Query parts collections for time estimates
6. Combine all results with installation timing
7. Returns complete guide with difficulty, time estimate, video link
```

---

## Best Practices

### Data Quality

1. **Keep metadata consistent** - Use standardized values for brand, part_type, etc.
2. **Maintain rich metadata** - More metadata = better filtering and ranking
3. **Regular updates** - Keep stock status and pricing current
4. **Video links** - Boost relevance when video tutorials available

### Query Optimization

1. **Extract entities first** - Use orchestrator for intent + entity extraction
2. **Filter before searching** - Reduce search space with metadata filters
3. **Get extra results** - Retrieve 2-3x needed, rerank by business logic
4. **Cache results** - Avoid redundant searches in multi-turn conversations

### Agent Integration

1. **Use retrievers directly** - Agents call retriever methods, not raw collections
2. **Pass metadata** - Agents provide appliance_type, brand, difficulty filters
3. **Trust relevance scores** - Retrievers return normalized scores (0-1)
4. **Handle gracefully** - Retrievers never fail; they fall back to alternatives

---

## Future Enhancements

1. **Fine-tuned Embeddings** - Train embeddings on appliance repair queries
2. **Reranking Models** - Use cross-encoders for better relevance scoring
3. **Caching Layer** - Redis for frequent queries
4. **Dynamic Weighting** - Adjust BM25/Vector weights based on query type
5. **User Feedback Loop** - Learn from which results users click on

---

## Troubleshooting

### Low Relevance Scores

**Problem:** Retrieved results seem irrelevant

**Solutions:**
1. Check metadata filters are working (use `n_results=100` to see raw results)
2. Verify embeddings are for correct language/domain
3. Try different query phrasing (more specific vs. general)
4. Use hybrid search for keyword-heavy queries

### Slow Queries

**Problem:** Searches taking > 100ms

**Solutions:**
1. Add metadata filters to reduce search space
2. Check ChromaDB collection has proper indexing
3. Reduce `n_results` if requesting too many
4. Profile with `time` command to identify bottleneck

### Missing Results

**Problem:** Can't find relevant documents

**Solutions:**
1. Verify documents are in ChromaDB (`get_collection_stats()`)
2. Check metadata filters aren't too restrictive
3. Try fuzzy matching on part names
4. Review chunking strategy for blogs (check overlap)

---

## Summary

The RAG system provides:
- Four specialized collections optimized for different query types
- Intelligent hybrid search combining keyword + semantic matching
- Agent-specific retrievers with built-in optimization
- Rich metadata for precise filtering and reranking
- Fallback mechanisms for robustness

This architecture enables PartSelect's agentic agents to access the right information at the right time, powering intelligent multi-turn conversations about appliance parts, repairs, and installation.
