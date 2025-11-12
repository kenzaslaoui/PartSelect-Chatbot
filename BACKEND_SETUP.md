# Backend Setup Guide

This guide covers setting up the PartSelect backend with Deepseek LLM and ChromaDB vector database.

## Prerequisites

- Python 3.10 or higher
- pip and virtualenv
- Deepseek API key (free trial: https://platform.deepseek.com)

## Installation

### 1. Install Python Dependencies

```bash
pip install -r requirements.txt
```

This installs:
- **FastAPI**: Web framework
- **ChromaDB**: Vector database
- **Deepseek (via OpenAI SDK)**: LLM API client
- **sentence-transformers**: Embedding model (all-MiniLM-L6-v2)
- **Data processing**: pandas, numpy, beautifulsoup4, requests

### 2. Configure Environment Variables

Create a `.env` file in the project root:

```bash
# Required
DEEPSEEK_API_KEY=sk-your-actual-api-key-here

# Optional (shown with defaults)
BACKEND_HOST=0.0.0.0
BACKEND_PORT=8000
CHROMA_DB_PATH=./data/chroma_db
VITE_API_URL=http://localhost:8000
```

Or set via environment:
```bash
export DEEPSEEK_API_KEY="sk-your-api-key"
```

## Deepseek API Setup

### Get an API Key

1. Go to https://platform.deepseek.com
2. Sign up / log in
3. Navigate to API Keys: https://platform.deepseek.com/api_keys
4. Create a new API key (free trial available)
5. Copy the key starting with `sk-`

### Verify API Connection

```bash
export DEEPSEEK_API_KEY="sk-your-api-key"

# Quick health check
python -c "
import sys
sys.path.insert(0, 'backend')
from agents.deepseek_client import DeepseekClient

client = DeepseekClient()
health = client.check_api_health()
print('Deepseek API is healthy!' if health else 'API check failed')
"
```

## ChromaDB Setup

ChromaDB is the vector database that stores embeddings of parts, repair guides, and blog articles.

### Automatic Setup

Data is automatically loaded from `data/chroma_db/` on first run.

### Manual Data Population

To refresh or repopulate the database:

```bash
python backend/populate_chroma.py
```

This creates 4 ChromaDB collections:
- `parts_refrigerator` (~6,500 docs) - Vector search only
- `parts_dishwasher` (~6,500 docs) - Vector search only
- `repair_symptoms` (300-400 chunks) - Hybrid (BM25 + vector)
- `blogs_articles` (200-300 chunks) - Hybrid (BM25 + vector)

### Collections Details

**Parts Collections** (vector search):
- Contains appliance parts with metadata (price, part number, compatibility)
- Pure vector search for semantic matching
- Configured for fast retrieval with cosine similarity

**Repair Symptoms Collection** (hybrid search):
- Contains repair guides indexed by symptom
- Uses both BM25 (keyword: "E5 error") and vector (semantic: "malfunction code")
- 50/50 weight combination for robustness

**Blog Articles Collection** (hybrid search):
- Contains installation and troubleshooting guides
- Hybrid search for finding relevant articles
- Ranked by relevance score

### Storage

Data is stored in:
```
data/chroma_db/
├── parts_refrigerator/
├── parts_dishwasher/
├── repair_symptoms/
└── blogs_articles/
```

To use remote ChromaDB (optional):

```bash
# Start ChromaDB server
chroma run --path ./data/chroma_db --port 8000

# Update .env
export CHROMA_HOST=localhost
export CHROMA_PORT=8000
```

## Starting the Backend

### Development Mode

```bash
python -m uvicorn backend.app.main:app --reload --host 0.0.0.0 --port 8000
```

Output:
```
INFO:     Uvicorn running on http://0.0.0.0:8000
INFO:     Application startup complete
```

### Production Mode

```bash
python -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8000
```

### Access the API

- **Interactive Docs**: http://localhost:8000/docs
- **Chat Endpoint**: POST http://localhost:8000/api/v1/chat
- **Health Check**: GET http://localhost:8000/api/v1/health

## System Architecture

### Request Flow

```
User Query (Frontend)
    ↓
FastAPI Endpoint (/api/v1/chat)
    ↓
AgentExecutor receives ChatRequest
    ↓
ConversationOrchestrator:
  ├─ Validates scope (refrigerator/dishwasher only)
  ├─ Classifies intent (product_search, troubleshooting, etc.)
  ├─ Extracts entities (brand, model, part type)
  └─ Routes to appropriate agents
    ↓
5 Specialized Agents (run in sequence if needed):
  ├─ PartSearchAgent (ChromaDB parts collection + vector search)
  ├─ TroubleshootingAgent (ChromaDB repair collection + hybrid search)
  ├─ InstallationAgent (ChromaDB blogs collection)
  ├─ CompatibilityAgent (metadata filtering)
  └─ ReviewCompareAgent (aggregation & ranking)
    ↓
Deepseek LLM:
  - Formats agent results into natural language
  - Synthesizes information
  - Generates next steps
    ↓
ChatResponse (answer + parts + repairs + blogs)
    ↓
Frontend displays response
```

## API Endpoints

### POST /api/v1/chat

Send a query and get agentic response.

**Request:**
```json
{
  "query": "Find a water dispenser for my LG refrigerator"
}
```

**Response:**
```json
{
  "response": "I found several water dispensers compatible with LG refrigerators...",
  "parts": [
    {
      "part_number": "WD123",
      "name": "LG Water Dispenser",
      "description": "...",
      "price": 89.99,
      "compatible_models": ["WDT780", "WDT790"]
    }
  ],
  "repairs": [
    {
      "symptom": "No water dispensing",
      "solution": "...",
      "has_video": true,
      "video_url": "https://..."
    }
  ],
  "blogs": [
    {
      "title": "How to Replace a Water Dispenser",
      "content": "...",
      "url": "https://..."
    }
  ]
}
```

### GET /api/v1/health

Check system health (all services).

**Response:**
```json
{
  "status": "healthy",
  "agents": {
    "chroma_db": true,
    "deepseek": true,
    "orchestrator": true,
    "overall": true
  }
}
```

### GET /api/v1/context

Get current conversation context and state.

### POST /api/v1/conversation/new

Start a new conversation thread.

## Configuration

### Agent Settings

**Location**: `backend/agents/orchestrator.py`

```python
# Conversation memory
CONTEXT_WINDOW = 10      # Last 10 messages for current reasoning
HISTORY_SIZE = 20        # Keep 20 messages in full history

# Scope validation
VALID_APPLIANCES = {"refrigerator", "dishwasher"} #parts of these appliances are also included

# Intent classification
INTENT_TO_AGENTS = {
    Intent.PRODUCT_SEARCH: ["PartSearchAgent"],
    Intent.TROUBLESHOOTING: ["TroubleshootingAgent"],
    Intent.INSTALLATION: ["InstallationAgent"],
    Intent.COMPATIBILITY: ["CompatibilityAgent"],
    Intent.REVIEW_COMPARISON: ["ReviewCompareAgent"],
}
```

### LLM Settings

**Location**: `backend/agents/deepseek_client.py`

```python
# Model configuration
MODEL = "deepseek-chat"
API_BASE = "https://api.deepseek.com/v1"
TEMPERATURE = 0.7
MAX_TOKENS = 2000
TIMEOUT = 30

# Retry logic
MAX_RETRIES = 3
RETRY_DELAY = 2  # seconds
```

### Search Settings

**Location**: `backend/rag/hybrid_search.py`

```python
# Hybrid search weights
BM25_WEIGHT = 0.5      # Keyword search weight
VECTOR_WEIGHT = 0.5    # Semantic search weight

# Retrieval settings
TOP_K = 10             # Return top 10 results
SIMILARITY_THRESHOLD = 0.3  # Filter low-relevance results
```

## Troubleshooting

### Issue: API Key Not Recognized

```
Error: "No API key provided"
```

**Solution**:
1. Verify API key is set: `echo $DEEPSEEK_API_KEY`
2. Check it starts with `sk-`
3. Verify it's valid: https://platform.deepseek.com/api_keys

### Issue: 401 Unauthorized Error

```
Error: "401 Client Error: Unauthorized for url: https://api.deepseek.com/v1/chat/completions"
```

**Causes**:
- API key expired or revoked
- API quota exceeded (free trial limit reached)
- Invalid API key format

**Solution**:
1. Check quota: https://platform.deepseek.com/usage
2. Generate new API key if needed
3. Verify internet connectivity

### Issue: ChromaDB Not Found

```
Error: "Cannot connect to ChromaDB at ./data/chroma_db"
```

**Solution**:
1. Check ChromaDB exists: `ls -la data/chroma_db/`
2. Repopulate if missing: `python backend/populate_chroma.py`
3. Verify path in .env: `CHROMA_DB_PATH=./data/chroma_db`

### Issue: Out of Memory

**If embedding model is slow or OOM**:
- `all-MiniLM-L6-v2` is 384-dimensional and very efficient
- Should work on CPU with 2GB+ RAM
- For GPU acceleration, install: `pip install sentence-transformers[cuda]`

### Issue: Slow Responses

**Typical latency**:
- Simple chat: 500ms-1s
- Product search: 1-2s
- Troubleshooting (hybrid search): 1.5-3s
- Multi-agent: 2-4s

**Optimization**:
- Reduce TOP_K in hybrid_search.py (faster but fewer results)
- Disable hybrid search for parts collections (vector-only is faster)
- Cache conversation results (already implemented)

## Performance Tuning

### ChromaDB HNSW Index

Fine-tune similarity search parameters in `backend/rag/chroma_db.py`:

```python
# HNSW tuning
HNSW_SPACE = "cosine"           # Distance metric
HNSW_CONSTRUCTION_EF = 200      # Build quality
HNSW_SEARCH_EF = 100            # Search quality
HNSW_M = 16                     # Max edges per node
```

**Recommendations**:
- **Need faster queries?** → Decrease HNSW_SEARCH_EF to 50-75
- **Need better accuracy?** → Increase HNSW_SEARCH_EF to 150-200
- **Memory constrained?** → Decrease HNSW_M to 8-12

## Testing

### Quick Health Check

```bash
# Check all services
curl http://localhost:8000/api/v1/health

# Test chat endpoint
curl -X POST http://localhost:8000/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{"query": "Find a water dispenser"}'
```

### Manual Testing

```python
import sys
sys.path.insert(0, 'backend')
from agents.agent_executor import AgentExecutor

executor = AgentExecutor()
response = executor.process_chat("Find a water dispenser for my LG refrigerator")
print(response.response)
print(f"Found {len(response.parts)} parts")
```

## Next Steps

1. Install dependencies (`pip install -r requirements.txt`)
2. Set Deepseek API key
3. Verify ChromaDB data exists
4. Start backend: `python -m uvicorn backend.app.main:app --reload`
5. Test endpoint: `curl http://localhost:8000/api/v1/health`
6. Proceed to frontend setup

## References

- [Main README](README.md) - Project overview
- [Agents System](backend/agents/README.md) - Agent architecture
- [RAG System](backend/rag/README.md) - Vector database
- [Deepseek Docs](https://docs.deepseek.com) - LLM API reference
- [ChromaDB Docs](https://docs.trychroma.com) - Vector DB reference
