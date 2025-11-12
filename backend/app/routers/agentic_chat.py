"""
Agentic chat router that uses the intelligent agent system.

This router:
1. Receives user queries
2. Routes to appropriate agents via AgentExecutor
3. Agents perform reasoning and tool use
4. Returns intelligent responses with context
"""
from fastapi import APIRouter, HTTPException, status
from app.models.schemas import ChatRequest, ChatResponse, Part, Blog, Repair
from app.utils.field_mapper import map_part_data, map_blog_data, map_repair_data
from agents.agent_executor import AgentExecutor
from agents.orchestrator import Intent
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["chat"])

# Initialize agent executor (singleton)
_agent_executor = None


def get_agent_executor() -> AgentExecutor:
    """Get or create AgentExecutor instance."""
    global _agent_executor
    if _agent_executor is None:
        logger.info("Initializing AgentExecutor...")
        _agent_executor = AgentExecutor()
    return _agent_executor


@router.post("/chat", response_model=ChatResponse)
async def agentic_chat(request: ChatRequest) -> ChatResponse:
    """
    Agentic chat endpoint that uses intelligent reasoning agents.

    This endpoint:
    1. Receives user query
    2. AgentExecutor processes through orchestrator
    3. Selects appropriate agents based on intent
    4. Agents perform reasoning and tool use
    5. Returns response with relevant resources

    Args:
        request: Chat request with user query

    Returns:
        ChatResponse with agent response and resources
    """
    try:
        logger.info(f"Agentic chat request: {request.query}")

        executor = get_agent_executor()

        # Process query through agentic system
        result = executor.process_user_input(request.query)

        logger.info(f"Agentic result: {result.get('in_scope')}, intent: {result.get('intent')}")

        # Extract response
        response_text = result.get("response", "Unable to process your request.")

        # Convert retrieved data to response format
        parts = _extract_parts(result)
        blogs = _extract_blogs(result)
        repairs = _extract_repairs(result)

        return ChatResponse(
            response=response_text,
            parts=parts,
            blogs=blogs,
            repairs=repairs,
        )

    except Exception as e:
        logger.error(f"Agentic chat error: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing request: {str(e)}",
        )


@router.get("/health")
async def health_check() -> dict:
    """
    Health check for agentic system.

    Returns:
        Health status of agents and services
    """
    try:
        executor = get_agent_executor()
        health = executor.check_health()

        return {
            "status": "healthy" if health.get("overall") else "degraded",
            "agents": health,
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Health check failed: {str(e)}",
        )


@router.get("/context")
async def get_context() -> dict:
    """
    Get current conversation context from orchestrator.

    Returns:
        Current conversation state, intent, entities, history
    """
    try:
        executor = get_agent_executor()
        context = executor.get_conversation_context()
        return context
    except Exception as e:
        logger.error(f"Failed to get context: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get context: {str(e)}",
        )


@router.post("/conversation/new")
async def new_conversation(user_id: str = None) -> dict:
    """
    Start a new conversation thread.

    Args:
        user_id: Optional user identifier

    Returns:
        Conversation ID
    """
    try:
        executor = get_agent_executor()
        conv_id = executor.new_conversation(user_id)
        return {
            "conversation_id": conv_id,
            "user_id": user_id,
            "status": "created",
        }
    except Exception as e:
        logger.error(f"Failed to create conversation: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create conversation: {str(e)}",
        )


# Helper functions to extract resources from agent results

def _extract_parts(result: dict) -> list[Part]:
    """
    Extract Part objects from agent results.

    Searches through all possible result locations where parts might be stored:
    - part_search results
    - compatibility results
    - review_compare results
    """
    parts = []

    # Check part_search results
    if "part_search" in result:
        part_results = result["part_search"]
        for part_data in _get_results_list(part_results)[:3]:  # Top 3
            try:
                mapped = map_part_data(part_data)
                parts.append(Part(**mapped))
            except Exception as e:
                logger.warning(f"Failed to map part data: {e}, data: {part_data}")

    # Check compatibility results
    if "compatibility" in result:
        compat_results = result["compatibility"]
        for part_data in _get_results_list(compat_results)[:3]:
            try:
                mapped = map_part_data(part_data)
                parts.append(Part(**mapped))
            except Exception as e:
                logger.warning(f"Failed to map compatibility part data: {e}")

    # Check review/comparison results
    if "review_compare" in result:
        review_results = result["review_compare"]
        for part_data in _get_results_list(review_results)[:3]:
            try:
                mapped = map_part_data(part_data)
                parts.append(Part(**mapped))
            except Exception as e:
                logger.warning(f"Failed to map review part data: {e}")

    return parts[:5]  # Return top 5 parts


def _extract_blogs(result: dict) -> list[Blog]:
    """
    Extract Blog objects from agent results.

    Searches through all possible result locations where blogs might be stored:
    - troubleshooting results (blog_article type)
    - installation results (blog_article type)
    """
    blogs = []

    # Check troubleshooting results (blogs)
    if "troubleshooting" in result:
        troubleshoot_results = result["troubleshooting"]
        for blog_data in _get_results_list(troubleshoot_results):
            # Filter for blog articles (not repair guides)
            if blog_data.get("source") == "blog_article":
                try:
                    mapped = map_blog_data(blog_data)
                    blogs.append(Blog(**mapped))
                except Exception as e:
                    logger.warning(f"Failed to map troubleshooting blog data: {e}")

    # Check installation results (blogs)
    if "installation" in result:
        installation_results = result["installation"]
        for blog_data in _get_results_list(installation_results):
            if blog_data.get("source") == "blog_article":
                try:
                    mapped = map_blog_data(blog_data)
                    blogs.append(Blog(**mapped))
                except Exception as e:
                    logger.warning(f"Failed to map installation blog data: {e}")

    return blogs[:5]  # Return top 5 blogs


def _extract_repairs(result: dict) -> list[Repair]:
    """
    Extract Repair objects from agent results.

    Searches through all possible result locations where repairs might be stored:
    - troubleshooting results (repair_guide type)
    - installation results (repair_guide type)
    """
    repairs = []

    # Check troubleshooting results (repair guides)
    if "troubleshooting" in result:
        troubleshoot_results = result["troubleshooting"]
        for repair_data in _get_results_list(troubleshoot_results):
            # Filter for repair guides (not blogs)
            if repair_data.get("source") == "repair_guide":
                try:
                    mapped = map_repair_data(repair_data)
                    repairs.append(Repair(**mapped))
                except Exception as e:
                    logger.warning(f"Failed to map troubleshooting repair data: {e}")

    # Check installation results (repair guides)
    if "installation" in result:
        installation_results = result["installation"]
        for repair_data in _get_results_list(installation_results):
            if repair_data.get("source") == "repair_guide":
                try:
                    mapped = map_repair_data(repair_data)
                    repairs.append(Repair(**mapped))
                except Exception as e:
                    logger.warning(f"Failed to map installation repair data: {e}")

    return repairs[:5]  # Return top 5 repairs


def _get_results_list(agent_result: dict) -> list:
    """
    Extract results list from agent result dict.

    Handles various possible structures:
    - {"results": [...]} - Standard format
    - {"agent_responses": [...]} - Alternative format
    - {...} - Treat dict as single result
    """
    if isinstance(agent_result, dict):
        # Check for "results" key (most common)
        if "results" in agent_result:
            results = agent_result.get("results", [])
            return results if isinstance(results, list) else [results]

        # Check for agent_responses
        if "agent_responses" in agent_result:
            responses = agent_result.get("agent_responses", [])
            return responses if isinstance(responses, list) else [responses]

        # Check if there's a "response" key with data
        if "response" in agent_result and isinstance(agent_result["response"], dict):
            return [agent_result["response"]]

        # If it looks like a single result item (has expected fields)
        if any(key in agent_result for key in ["title", "name", "url", "id"]):
            return [agent_result]

    # Return empty list if unable to extract
    return []
