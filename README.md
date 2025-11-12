# PartSelect Assistant

AI-powered appliance parts assistant using FastAPI, React, and Deepseek LLM with RAG.

## Project Structure

```
├── backend/                    # FastAPI backend
│   ├── main.py                # Main FastAPI app
│   ├── agents/                # Specialized AI agents
│   │   ├── classifier.py      # Intent classification
│   │   ├── product_agent.py   # Product search
│   │   ├── compatibility_agent.py
│   │   ├── troubleshooting_agent.py
│   │   ├── installation_agent.py
│   │   └── orchestrator.py    # Main agent coordinator
│   ├── rag/                   # RAG implementation
│   │   ├── embeddings.py      # Vector DB setup
│   │   └── retrieval.py       # RAG logic
│   ├── data/                  # Data storage
│   │   ├── parts.json
│   │   ├── compatibility.json
│   │   ├── troubleshooting.json
│   │   └── installation_guides.json
│   └── utils/
│       ├── deepseek.py        # Deepseek API wrapper
│       └── schemas.py         # Pydantic models
├── frontend/                  # React frontend
│   ├── src/
│   │   ├── components/
│   │   │   ├── Chat.jsx
│   │   │   ├── ProductCard.jsx
│   │   │   ├── TroubleshootingFlow.jsx
│   │   │   ├── InstallationGuide.jsx
│   │   │   └── CompatibilityChecker.jsx
│   │   ├── App.jsx
│   │   └── main.jsx
│   └── package.json
├── scraper/                   # Web scrapers
│   ├── scrape_parts.py
│   ├── scrape_troubleshooting.py
│   └── scrape_compatibility.py
└── README.md
```

## Setup

### Backend

1. Create virtual environment:
```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. Install dependencies:
```bash
pip install fastapi uvicorn pydantic python-multipart
pip install openai  # For Deepseek API
pip install chromadb  # For vector database
```

3. Set environment variables:
```bash
export DEEPSEEK_API_KEY="your-api-key"
```

4. Run server:
```bash
python main.py
```

### Frontend

1. Install dependencies:
```bash
cd frontend
npm install
```

2. Run development server:
```bash
npm run dev
```

### Scraper

1. Install dependencies:
```bash
cd scraper
pip install -r requirements.txt
```

2. Run scrapers:
```bash
python scrape_parts.py
python scrape_compatibility.py
python scrape_troubleshooting.py
```

## Features

- **Product Search**: Find appliance parts by description
- **Compatibility Check**: Verify part-model compatibility
- **Troubleshooting**: Diagnose appliance issues
- **Installation Guides**: Step-by-step installation instructions
- **RAG-powered**: Context-aware responses using vector search

## Technology Stack

- **Backend**: FastAPI, Python
- **Frontend**: React, Vite
- **LLM**: Deepseek API
- **Vector DB**: ChromaDB
- **Scraping**: BeautifulSoup, Selenium

## API Endpoints

- `POST /chat` - Main chat endpoint
- `GET /health` - Health check

## Development

The project uses a multi-agent architecture:
1. **Classifier**: Routes messages to appropriate agents
2. **Product Agent**: Handles product searches
3. **Compatibility Agent**: Checks part compatibility
4. **Troubleshooting Agent**: Diagnoses issues
5. **Installation Agent**: Provides installation guides
6. **Orchestrator**: Coordinates all agents

