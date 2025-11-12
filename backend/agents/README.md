# Agentic Implementation

This directory contains the core agentic system for PartSelect. These agents are **specialized tool executors** that intelligently select and run the best tools for each query type, then use Deepseek LLM to generate natural, helpful responses.

## What Makes This "Agentic"?

**Traditional Pipeline:** Query → Fixed routing → Retrieve → Format → Response

**Agentic System:** Query → Agent determines intent → Agent picks best tool → Tool executes → LLM formats response → User gets answer

Each agent independently decides which tool is most relevant and executes it to get structured data, then the LLM transforms that into a human-friendly response with domain knowledge (refrigerators & dishwashers only).

## ⚡ Key Simplifications (Current)

### Direct Tool Execution (No Reasoning Loops)
- **Before:** Agents tried to parse structured reasoning output (THOUGHT:/ACTION:/ACTION_INPUT:) through multiple iterations
- **Now:** Agents directly execute the most relevant tool based on intent
- **Result:** Instant responses, no parsing errors, no iteration exhaustion

### Single-Tool Execution Per Query
- Each agent picks its primary tool and executes immediately
- Tool returns structured data (search results, guides, etc.)
- Deepseek LLM formats the structured data into a natural response
- User gets answer in seconds, not minutes

### Strong System Prompts
- All responses use `CLIENT_FACING_SYSTEM_PROMPT` enforcing domain boundaries
- Gracefully rejects out-of-scope questions (washing machines, ovens, etc.)
- Professional, friendly tone for all interactions
- Consistent brand voice across all agents

## Architecture

```
User Query
    ↓
ConversationOrchestrator
├─ Scope validation (refrigerator/dishwasher only)
├─ Intent classification
├─ Entity extraction
└─ Agent routing
    ↓
Specialized Agent (direct tool execution)
├─ Pick most relevant tool based on intent
├─ Execute tool → Get structured results
├─ LLM formats results using CLIENT_FACING_SYSTEM_PROMPT
└─ Return formatted response to user
    ↓
User Response (instant, accurate, domain-aware)
```

## The 5 Specialized Agents

### 1. **PartSearchAgent** (`part_search_agent.py`)
Finds and recommends the best parts for user needs.

**Primary Tool:** `vector_search_parts()` - Natural language part search

**Other Tools:**
- `filter_by_price()` - Price range filtering
- `check_stock()` - Availability checking
- `get_reviews()` - Customer reviews & ratings
- `compare_parts()` - Side-by-side comparison

**Example:** "Find me a water dispenser for my LG fridge"
- Agent executes `vector_search_parts` → Gets top 5 results → LLM formats into helpful recommendation

---

### 2. **TroubleshootingAgent** (`troubleshooting_agent.py`)
Diagnoses appliance problems and guides repairs.

**Primary Tool:** `search_repair_guides()` - Find repair guides (HYBRID BM25 + vector search)

**Other Tools:**
- `search_blogs()` - Detailed blog articles
- `get_video_tutorials()` - YouTube video guides
- `extract_parts()` - Identify parts needing replacement
- `assess_difficulty()` - Evaluate repair complexity

**Example:** "My dishwasher is leaking"
- Agent executes `search_repair_guides` → Gets guides + difficulty + videos → LLM formats into step-by-step guidance

---

### 3. **InstallationAgent** (`installation_agent.py`)
Provides step-by-step installation guidance.

**Primary Tool:** `search_installation_guides()` - Find installation docs (HYBRID search)

**Other Tools:**
- `get_difficulty_level()` - Difficulty assessment
- `get_tools_needed()` - Required tools list
- `get_time_estimate()` - Time required
- `get_video_guide()` - Video tutorials

**Example:** "How do I install a water pump?"
- Agent executes `search_installation_guides` → Gets guide + difficulty + tools needed → LLM formats into clear instructions

---

### 4. **CompatibilityAgent** (`compatibility_agent.py`)
Verifies parts are compatible with specific models.

**Primary Tool:** `search_compatible_parts()` - Find compatible parts for a model

**Other Tools:**
- `lookup_model_info()` - Get model information
- `verify_fit()` - Verify specific part compatibility
- `check_alternatives()` - Find alternative options

**Example:** "Is part PS12345 compatible with my LG model WDT780?"
- Agent executes `search_compatible_parts` → Gets compatible parts → LLM confirms compatibility

---

### 5. **ReviewCompareAgent** (`review_compare_agent.py`)
Compares parts and analyzes customer reviews.

**Primary Tool:** `search_parts()` - Search for parts to compare

**Other Tools:**
- `analyze_reviews()` - Review sentiment analysis
- `compare_prices()` - Price comparison
- `rank_options()` - Rank by rating/price/value
- `get_sentiments()` - Extract common themes

**Example:** "Compare water dispensers, what has the best reviews?"
- Agent executes `search_parts` → Gets parts with ratings → LLM formats comparison and recommendation

---

## Key Features

### Instant Responses
- No reasoning loops = immediate tool execution
- No parsing errors = no retry delays
- Single LLM call to format results = fast response generation
- Typical query answered in 2-5 seconds

### Conversation Memory
- **Context window:** Last 10 messages (configurable)
- **Full history:** Keeps 20 messages for multi-turn dialogue
- Enables natural follow-up queries like "Are there better reviews?" or "How long to install?"

### Multi-Agent Coordination
Single query can invoke multiple agents:
- "Find parts AND check compatibility" → PartSearchRetriever + CompatibilityRetriever
- "Reviews and comparison" → PartSearchRetriever + ReviewAnalyzer
- "Installation with video" → InstallationRetriever + TroubleshootingRetriever

### Hybrid Search (Semantic + Index)
**TroubleshootingRetriever & InstallationRetriever use hybrid search:**
- **Vector search (50%):** Semantic similarity for understanding intent
- **BM25 keyword search (50%):** Exact matches for error codes, part names
- Falls back to pure vector search if hybrid unavailable

**PartSearchRetriever uses pure vector search:** Better for natural language part descriptions

### Scope Handling
Returns polite rejection for out-of-scope queries:
> "I specialize in refrigerator and dishwasher parts, repairs, and installations. Is there something related to your refrigerator or dishwasher I can assist with?"

### Domain Enforcement
All responses enforce strict domain boundaries via `CLIENT_FACING_SYSTEM_PROMPT`:
- ✅ Accepts: Refrigerator and dishwasher questions (parts, repairs, installation, compatibility, reviews)
- ❌ Rejects: Other appliances, general life advice, medical/legal/financial topics
- 🎯 Redirects: Politely guides users back to supported topics

---

## How Agents Work (Simplified Flow)

```python
# Agent receives query from orchestrator
def execute(self, query: str, appliance_type: Optional[str] = None) -> Dict[str, Any]:

    # 1. Determine primary tool based on agent's specialty
    tool_name = "vector_search_parts"  # PartSearchAgent's tool
    tool_inputs = {
        "query": query,
        "appliance_type": appliance_type,
        "top_k": 5
    }

    # 2. Execute tool directly (no parsing, no loops)
    result = super().execute(
        tool_name=tool_name,
        tool_inputs=tool_inputs,
        query=query
    )

    # 3. Inside base_agent.execute():
    #    - Tool executes and returns structured data
    #    - LLM formats results using CLIENT_FACING_SYSTEM_PROMPT
    #    - Returns formatted response

    return result
```

### Tool Registration

Each agent registers its tools:

```python
self.register_tool(Tool(
    name="vector_search_parts",
    description="Search for parts using natural language",
    func=vector_search_parts,
    required_params=["query"],
    optional_params=["appliance_type"]
))
```

All tools are available but the agent executes its primary tool directly.

---

## Multi-Turn Conversation Example

```
Turn 1: "Find me a water dispenser for my LG fridge"
Agent: [PartSearchAgent executes vector_search_parts]
→ "I found 5 water dispensers. The highest-rated is..."

Turn 2: "Is that compatible with model WDT780?"
Agent: [CompatibilityAgent executes search_compatible_parts]
→ "Yes, it's confirmed compatible with your model"

Turn 3: "How do I install it?"
Agent: [InstallationAgent executes search_installation_guides]
→ "Installation is straightforward. Here are the steps..."

Turn 4: "What are the alternatives?"
Agent: [ReviewCompareAgent executes search_parts]
→ "Here are 3 alternatives with similar ratings..."
```

Each agent works independently with direct tool execution, making responses fast and reliable.

---

## Files Structure

### Core Agent Classes
- **`base_agent.py`** - Base class with simplified tool execution and LLM response generation
- **`part_search_agent.py`** - Part search with vector_search_parts tool
- **`troubleshooting_agent.py`** - Troubleshooting with search_repair_guides tool
- **`installation_agent.py`** - Installation guidance with search_installation_guides tool
- **`compatibility_agent.py`** - Compatibility checking with search_compatible_parts tool
- **`review_compare_agent.py`** - Review analysis with search_parts tool

### Integration & Support Files
- **`orchestrator.py`** - Conversation management and agent routing
- **`intent_classifier.py`** - Intent detection and entity extraction
- **`deepseek_client.py`** - Deepseek API wrapper with retry logic
- **`agent_executor.py`** - Coordinates orchestrator and agents
- **`response_generator.py`** - Fallback response generation
- **`prompts.py`** - Centralized system prompts (CLIENT_FACING_SYSTEM_PROMPT, etc.)

---

## Testing the Agent System

### Check Deepseek Connection
```bash
export DEEPSEEK_API_KEY="sk-your-key"
python -c "
from agents.deepseek_client import DeepseekClient
client = DeepseekClient()
print('API Health:', client.check_api_health())
"
```

### Test Individual Agent
```bash
python -c "
import sys
sys.path.insert(0, 'backend')
from agents.part_search_agent import PartSearchAgent

agent = PartSearchAgent()
result = agent.execute('Find water dispensers for refrigerators')
print('Response:', result['response'])
print('Success:', result.get('success'))
"
```

### Test End-to-End with AgentExecutor
```bash
python -c "
import sys
sys.path.insert(0, 'backend')
from agents.agent_executor import AgentExecutor

executor = AgentExecutor(user_id='test_user')
response = executor.process_user_input('Find me a water dispenser')
print(response['response'])
"
```

### Run Full Test Suite
```bash
python backend/test_simplified_agents.py
```

---

## Speed Comparison

| Metric | Old (Reasoning Loops) | New (Direct Execution) |
|--------|---|---|
| **Tool Calls** | 3-5 per query | 1 per query |
| **LLM Calls** | 5+ iterations × 2 calls each | 1 call for formatting |
| **Average Response Time** | 15-30 seconds | 2-5 seconds |
| **Parsing Errors** | Common (malformed JSON) | None (structured data) |
| **Max Iterations Error** | "Exhausted reasoning attempts" | Eliminated |

---

## Why This Architecture Works for MVP

1. **Fast:** Direct tool execution, no loops = instant responses
2. **Reliable:** No parsing of structured responses = no errors
3. **Simple:** Each agent picks one tool and runs it = easy to debug
4. **Smart:** System prompts enforce domain boundaries = consistent quality
5. **Scalable:** Easy to add new agents or tools without complexity

---

## Agent Response Format

All agents return a consistent format:

```python
{
    "response": "Human-friendly answer to the user",
    "agent": "Part Search Agent",
    "tool_used": "vector_search_parts",
    "tool_result": {...},  # Structured data from tool
    "success": True,
    "agent_type": "part_search",
    "search_results": [...]  # Agent-specific data
}
```

The response is already formatted for the user; no additional processing needed.

---

## Summary

This agentic system is a **practical, fast, and reliable architecture** where:
- Agents **pick the right tool** based on query intent
- Tools **execute immediately** with no reasoning overhead
- LLM **formats results** using strong system prompts
- Responses are **instant, accurate, and domain-aware**
- System **enforces boundaries** (refrigerators & dishwashers only)

This is fundamentally more practical than complex reasoning loops. The agents are specialized, fast, and focused on solving real user problems.
