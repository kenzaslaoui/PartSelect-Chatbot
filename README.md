# PartSelect Assistant

An intelligent appliance parts assistant using **agentic reasoning** with FastAPI, React, Deepseek LLM, and ChromaDB RAG.

## Overview

PartSelect combines **agentic AI** with **retrieval-augmented generation (RAG)** to provide expert guidance on appliance parts, repairs, and installation. The system uses 5 specialized AI agents that understand context, reason through problems, and retrieve relevant information from a vector database.

**Scope**: Refrigerators and dishwashers only

```
User Query → Intent Classification → Agent Routing → ChromaDB Retrieval → Deepseek LLM → Intelligent Response
```

## Project Structure

```
backend/
  ├── app/                      # FastAPI application core
  │   ├── main.py             # Entry point (uvicorn)
  │   ├── routers/            # API endpoints
  │   ├── models/             # Pydantic schemas
  │   └── config/             # Settings
  ├── agents/                  # 5 specialized reasoning agents
  │   ├── orchestrator.py      # Intent classification & routing
  │   ├── base_agent.py        # Agent base class
  │   ├── part_search_agent.py
  │   ├── troubleshooting_agent.py
  │   ├── installation_agent.py
  │   ├── compatibility_agent.py
  │   └── review_compare_agent.py
  └── rag/                     # Retrieval system
      ├── chroma_db.py         # Vector DB connection
      ├── hybrid_search.py     # BM25 + Vector search
      └── retrieval.py         # Agent-specific retrievers

frontend/                       # React + TypeScript
  └── src/
      ├── components/          # ChatInterface, MessageBubble, ResourceList
      └── types.ts             # TypeScript interfaces

scrapers/                       # Web data collection
  ├── blog_scraper.py
  ├── repair_scraper.py
  └── parts_scraper.py

data/
  ├── raw/                     # Scraped data (JSON)
  ├── processed/               # Chunked data for RAG
  └── chroma_db/               # Vector database (persistent)
```

## Quick Start

### Prerequisites
- Python 3.10+
- Node.js 16+
- Deepseek API key: https://platform.deepseek.com/api_keys

### Backend Setup

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Configure environment
export DEEPSEEK_API_KEY="sk-your-api-key"

# 3. Start backend
python -m uvicorn backend.app.main:app --reload --port 8000
```

Backend API: `http://localhost:8000/docs` (interactive Swagger UI)

### Frontend Setup

```bash
cd frontend
npm install
npm run dev
```

Frontend: `http://localhost:5173`

## Design & Architecture

### Why Agentic Reasoning?
Unlike simple RAG, PartSelect agents **reason through problems**:
- Parse complex user intent (multiple appliances, conflicting requirements)
- Extract key entities (brand, model, part type)
- Choose between multiple retrieval strategies
- Synthesize information from multiple sources
- Provide confidence levels and next steps

This provides more accurate, contextual answers vs. simple vector search.

### Core Architecture

**5 Specialized Agents** (each handles one aspect):
1. **PartSearchAgent** - Find parts by natural language (vector search + ranking)
2. **TroubleshootingAgent** - Diagnose issues (hybrid keyword + semantic search)
3. **InstallationAgent** - Step-by-step guides (structured extraction)
4. **CompatibilityAgent** - Check part-model compatibility
5. **ReviewCompareAgent** - Compare parts and analyze reviews

**ConversationOrchestrator** - Routes queries to appropriate agents based on intent

**Hybrid Search** - Best of both worlds:
- BM25 (keyword exact match): Catch "E5 error", "water dispenser"
- Vector (semantic): Find "malfunction", "water leaking"
- Combined 50/50 weight for robustness

**ChromaDB Collections** (4 focused databases):
- `parts_refrigerator` (6.5K docs)
- `parts_dishwasher` (6.5K docs)
- `repair_symptoms` (300-400 chunks)
- `blogs_articles` (200-300 chunks)

### Data Flow

```
Scrapers → Raw JSON Data
    ↓
Processors (clean, extract metadata)
    ↓
Chunking (intelligent, context-preserving)
    ↓
Embeddings (all-MiniLM-L6-v2, 384-dim)
    ↓
ChromaDB (vector storage + HNSW indexing)
    ↓
Agent Retrieval (with metadata filtering + reranking)
    ↓
LLM Response (Deepseek formats answer)
    ↓
User sees answer + relevant parts/guides/repairs
```

## Setup & Configuration

### Environment Variables (.env)
```bash
# Required
DEEPSEEK_API_KEY=sk-your-api-key

# Optional (defaults below)
BACKEND_HOST=0.0.0.0
BACKEND_PORT=8000
CHROMA_DB_PATH=./data/chroma_db
VITE_API_URL=http://localhost:8000
```

### Deepseek API Setup
1. Create account: https://platform.deepseek.com
2. Get API key: https://platform.deepseek.com/api_keys
3. Add to environment: `export DEEPSEEK_API_KEY="sk-..."`

### ChromaDB Setup
Data is automatically loaded from `data/chroma_db/` on first run. To repopulate:
```bash
python backend/populate_chroma.py
```

## Data Sources & Web Scraping

PartSelect uses **comprehensive web scrapers** to collect real-world appliance data from PartSelect.com:

### Three Specialized Scrapers

| Scraper | Purpose | Coverage | Output |
|---------|---------|----------|--------|
| **Blog Scraper** | Repair articles, how-to guides, error codes | 50+ articles across 5 topics | `blogs_raw.json` |
| **Repair Scraper** | Symptom guides, troubleshooting, inspection steps | 21 symptoms (12 fridge, 9 dishwasher) | `repair_symptoms_raw.json` |
| **Parts Scraper** | Parts catalog, pricing, availability, specs | 43 brands, 1000s of parts | `parts_raw.json` |

### Data Coverage

- **~13,000 appliance parts** (6,500 refrigerator + 6,500 dishwasher)
- **50+ how-to guides and repair articles** with brand-specific instructions
- **21 common symptom guides** with difficulty levels and YouTube tutorials
- **43 appliance brands** (LG, Samsung, GE, Whirlpool, Bosch, etc.)
- **YouTube video links** for visual repair tutorials
- **Real pricing, stock status, and customer reviews** information

### Data Pipeline

```
Web Scrapers (polite, 2-4s delays)
    ↓
Raw JSON Data (title, content, metadata)
    ↓
Data Processors (clean, extract, validate)
    ↓
Intelligent Chunking (context-preserving for RAG)
    ↓
Embedding Generation (all-MiniLM-L6-v2)
    ↓
ChromaDB Indexing (4 specialized collections)
    ↓
Agent Retrieval (metadata filtering + reranking)
```

### Scraper Features

- **Polite scraping**: 2-4 second random delays between requests
- **Robust retry logic**: Exponential backoff for rate limiting
- **Progress checkpointing**: Saves progress every 25 articles
- **Deduplication**: Removes duplicate content
- **Brand recognition**: Extracts 43+ appliance brands automatically
- **Metadata extraction**: Part numbers, prices, compatibility info
- **YouTube integration**: Extracts video IDs and thumbnails
- **Transparent logging**: Full scraper logs for debugging

See [Scrapers Documentation](scrapers/README.md) for detailed information on each scraper, CSS selectors, and how to extend data collection.

## API Reference

**Main Endpoint**: `POST /api/v1/chat`

Request:
```json
{ "query": "Find a water dispenser for my LG refrigerator" }
```

Response:
```json
{
  "response": "I found several water dispensers compatible with LG refrigerators...",
  "parts": [
    { "part_number": "WD123", "name": "LG Water Dispenser", "price": 89.99 }
  ],
  "repairs": [...],
  "blogs": [...]
}
```

**Other Endpoints**:
- `GET /api/v1/health` - System health check
- `GET /api/v1/context` - Conversation state
- `POST /api/v1/conversation/new` - Start new conversation
- `GET /docs` - Interactive API documentation

## Key Features

- **Agentic Reasoning**: Agents think before acting, not just vector search
- **Multi-turn Conversations**: Conversation memory (last 10 messages)
- **Intelligent Intent Routing**: Automatically calls right agents
- **Hybrid Search**: Keyword + semantic search for robustness
- **Product Ranking**: By compatibility + stock + customer rating
- **Transparent**: View agent reasoning and data sources
- **Focused Scope**: Specialized for refrigerators & dishwashers

## Documentation

- **[Agents System](backend/agents/README.md)** - 5 agents, how they work, tools
- **[RAG System](backend/rag/README.md)** - Vector database, search, data pipeline
- **[Web Scrapers](scrapers/README.md)** - Data collection, sources
- **[Frontend](frontend/README.md)** - React setup, components, build

## Technology Stack

| Component | Technology |
|-----------|-----------|
| Backend | FastAPI (Python 3.10+) |
| Frontend | React 18 + TypeScript + Vite |
| LLM | Deepseek (OpenAI-compatible API) |
| Vector DB | ChromaDB (persistent HNSW) |
| Embeddings | sentence-transformers (all-MiniLM-L6-v2) |
| Search | BM25 (keyword) + Vector (semantic) |


## Troubleshooting

**Backend won't start**
- Check Deepseek API key: `echo $DEEPSEEK_API_KEY`
- Check ChromaDB exists: `ls data/chroma_db/`

**Chat returns "No action specified"**
- Usually Deepseek API quota exceeded (401 error)
- Check API key validity: https://platform.deepseek.com/api_keys
- Verify internet connection

**Empty results**
- Check ChromaDB collections exist: `GET /api/v1/health`
- Verify data populated: `python backend/populate_chroma.py`

## Roadmap

- [ ] Persistent user conversations (database storage)
- [ ] Streaming responses (show thinking as it happens)
- [ ] User feedback loop (train on corrections)
- [ ] Multi-language support
- [ ] Analytics (common queries, success rates)

