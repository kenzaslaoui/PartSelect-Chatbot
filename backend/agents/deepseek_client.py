"""
Deepseek LLM client wrapper.

Provides interface to Deepseek API (OpenAI-compatible) for:
- Natural language response generation
- Sentiment analysis
- Multi-turn conversation management

Uses centralized system prompts from prompts.py for consistency.
"""

import logging
import os
import json
import time
from typing import List, Dict, Any, Optional
import requests

# Load environment variables at module import time
try:
    from config.env_loader import load_env
    load_env()
except ImportError:
    # Fallback: load .env manually if config module not available
    from pathlib import Path
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        backend_dir = Path(__file__).parent.parent
        env_file = backend_dir / '.env'
        if env_file.exists():
            with open(env_file) as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, value = line.split('=', 1)
                        os.environ[key.strip()] = value.strip()

from .prompts import CLIENT_FACING_SYSTEM_PROMPT

logger = logging.getLogger(__name__)

# Retry configuration
MAX_RETRIES = 3
INITIAL_BACKOFF = 1  # seconds
MAX_BACKOFF = 32  # seconds
BACKOFF_MULTIPLIER = 2


class DeepseekClient:
    """Client for Deepseek LLM API (OpenAI-compatible)."""

    def __init__(self, api_key: Optional[str] = None, model: str = "deepseek-chat"):
        """
        Initialize Deepseek client.

        Args:
            api_key: Deepseek API key (defaults to DEEPSEEK_API_KEY env var)
            model: Model to use (default: deepseek-chat)
        """
        self.api_key = api_key or os.getenv("DEEPSEEK_API_KEY")
        self.model = model
        self.base_url = "https://api.deepseek.com/v1"

        if not self.api_key:
            logger.warning("No API key provided. Set DEEPSEEK_API_KEY environment variable.")
            self.client = None
        else:
            self.client = True  # Flag to indicate client is configured

        logger.info(f"DeepseekClient initialized with model: {model}")

    def _call_api_with_retry(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 1000
    ) -> Dict[str, Any]:
        """
        Call Deepseek API with exponential backoff retry.

        Args:
            messages: List of message dicts with 'role' and 'content'
            temperature: Temperature for sampling
            max_tokens: Max tokens in response

        Returns:
            API response data dict

        Raises:
            Exception: If all retries fail
        """
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": False
        }

        backoff = INITIAL_BACKOFF
        last_error = None

        for attempt in range(MAX_RETRIES):
            try:
                response = requests.post(
                    f"{self.base_url}/chat/completions",
                    headers=headers,
                    json=payload,
                    timeout=30
                )

                # Handle rate limiting and server errors with retry
                if response.status_code == 429:  # Too many requests
                    logger.warning(f"Rate limited (429). Attempt {attempt + 1}/{MAX_RETRIES}. Backing off {backoff}s...")
                    time.sleep(backoff)
                    backoff = min(backoff * BACKOFF_MULTIPLIER, MAX_BACKOFF)
                    continue
                elif response.status_code >= 500:  # Server error
                    logger.warning(f"Server error ({response.status_code}). Attempt {attempt + 1}/{MAX_RETRIES}. Backing off {backoff}s...")
                    time.sleep(backoff)
                    backoff = min(backoff * BACKOFF_MULTIPLIER, MAX_BACKOFF)
                    continue
                elif response.status_code == 401:  # Unauthorized - don't retry
                    logger.error("API authentication failed (401). Check your API key.")
                    response.raise_for_status()
                else:
                    # Success or client error (4xx besides 401/429)
                    response.raise_for_status()
                    return response.json()

            except requests.exceptions.Timeout:
                last_error = "Request timeout"
                if attempt < MAX_RETRIES - 1:
                    logger.warning(f"Timeout. Attempt {attempt + 1}/{MAX_RETRIES}. Backing off {backoff}s...")
                    time.sleep(backoff)
                    backoff = min(backoff * BACKOFF_MULTIPLIER, MAX_BACKOFF)
            except requests.exceptions.ConnectionError:
                last_error = "Connection error"
                if attempt < MAX_RETRIES - 1:
                    logger.warning(f"Connection error. Attempt {attempt + 1}/{MAX_RETRIES}. Backing off {backoff}s...")
                    time.sleep(backoff)
                    backoff = min(backoff * BACKOFF_MULTIPLIER, MAX_BACKOFF)
            except requests.exceptions.RequestException as e:
                logger.error(f"Request failed: {e}")
                raise

        raise Exception(f"API call failed after {MAX_RETRIES} attempts. Last error: {last_error}")

    def generate_response(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 1000,
        system_prompt: Optional[str] = None
    ) -> str:
        """
        Generate response from Deepseek.

        Args:
            messages: List of message dicts with 'role' and 'content'
            temperature: Temperature for sampling
            max_tokens: Max tokens in response
            system_prompt: Optional system prompt to prepend

        Returns:
            Generated response text
        """
        if not self.client:
            logger.error("Deepseek client not initialized. API key missing.")
            return "I'm unable to process your request at the moment. Please try again later."

        try:
            # Build message list with system prompt if provided
            request_messages = messages.copy()
            if system_prompt and (not request_messages or request_messages[0].get("role") != "system"):
                request_messages.insert(0, {"role": "system", "content": system_prompt})

            # Call API with retry
            response_data = self._call_api_with_retry(request_messages, temperature, max_tokens)

            # Extract response text
            if response_data.get("choices") and len(response_data["choices"]) > 0:
                return response_data["choices"][0]["message"]["content"]
            else:
                logger.error(f"Unexpected API response format: {response_data}")
                return "I encountered an error processing your request."

        except requests.exceptions.RequestException as e:
            logger.error(f"Error calling Deepseek API: {e}")
            return f"I encountered an error processing your request. Please try again later."
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            return f"I encountered an error processing your request."

    def analyze_sentiment(
        self,
        text: str,
        aspect: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Analyze sentiment of text.

        Args:
            text: Text to analyze
            aspect: Optional aspect to analyze sentiment for

        Returns:
            Dict with sentiment analysis results
        """
        prompt = f"""Analyze the sentiment of the following text.

{"Specifically analyze sentiment regarding: " + aspect if aspect else ""}

Text: {text}

Provide response in JSON format with:
- sentiment: "positive", "negative", or "neutral"
- confidence: 0-1 score
- key_phrases: list of key phrases expressing sentiment
- summary: brief summary of sentiment"""

        messages = [{"role": "user", "content": prompt}]

        try:
            response = self.generate_response(messages, temperature=0.3, max_tokens=500)

            # Parse JSON response
            import json

            # Extract JSON from response if wrapped in markdown
            if "```json" in response:
                json_str = response.split("```json")[1].split("```")[0].strip()
            elif "```" in response:
                json_str = response.split("```")[1].split("```")[0].strip()
            else:
                json_str = response

            result = json.loads(json_str)
            return result
        except Exception as e:
            logger.error(f"Error analyzing sentiment: {e}")
            return {
                "sentiment": "neutral",
                "confidence": 0.0,
                "key_phrases": [],
                "summary": "Unable to analyze sentiment"
            }

    def extract_recommendations(
        self,
        parts_data: List[Dict[str, Any]],
        context: Optional[str] = None
    ) -> str:
        """
        Generate recommendations from parts data.

        Args:
            parts_data: List of part dictionaries
            context: Additional context about user needs

        Returns:
            Recommendation text
        """
        parts_summary = "\n".join(
            [
                f"- {p.get('title', 'Unknown')} (${p.get('price', 'N/A')}, "
                f"Rating: {p.get('rating', 'N/A')}, Stock: {p.get('stock_status', 'unknown')})"
                for p in parts_data[:5]  # Top 5 parts
            ]
        )

        prompt = f"""Based on the following parts and user context, provide a recommendation.

Available Parts:
{parts_summary}

User Context: {context or "Customer looking for best option"}

Provide a concise recommendation (2-3 sentences) explaining:
1. Which part(s) you recommend and why
2. Key considerations (price, availability, ratings)
3. Any alternatives or warnings"""

        messages = [{"role": "user", "content": prompt}]

        try:
            return self.generate_response(messages, temperature=0.7, max_tokens=300)
        except Exception as e:
            logger.error(f"Error extracting recommendations: {e}")
            return "I encountered an error generating recommendations. Please try again."

    def generate_troubleshooting_response(
        self,
        issue: str,
        guides: List[Dict[str, Any]],
        conversation_history: Optional[List[Dict[str, str]]] = None
    ) -> str:
        """
        Generate troubleshooting response with guides.

        Args:
            issue: User's issue description
            guides: List of troubleshooting guides
            conversation_history: Previous conversation messages

        Returns:
            Troubleshooting response text
        """
        guides_summary = "\n".join(
            [
                f"- {g.get('symptom', g.get('title', 'Unknown'))}: "
                f"{g.get('guide_title', 'Guide')} "
                f"(Difficulty: {g.get('difficulty', 'N/A')}, "
                f"Video: {'Yes' if g.get('has_video') else 'No'})"
                for g in guides[:5]
            ]
        )

        # Use client-facing system prompt as foundation
        system_prompt = CLIENT_FACING_SYSTEM_PROMPT

        prompt = f"""User's Issue: {issue}

Available Guides:
{guides_summary}

Based on these guides, provide troubleshooting steps or diagnosis suggestions.
Use numbered steps for clarity. Be friendly and thorough.
If appropriate, mention video tutorials available.
Always recommend professional help if safety is a concern."""

        messages = conversation_history or []
        messages.append({"role": "user", "content": prompt})

        try:
            return self.generate_response(
                messages,
                system_prompt=system_prompt,
                temperature=0.7,
                max_tokens=500
            )
        except Exception as e:
            logger.error(f"Error generating troubleshooting response: {e}")
            return "I encountered an error. Please try rephrasing your question."

    def generate_installation_response(
        self,
        part_name: str,
        guides: List[Dict[str, Any]],
        context: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Generate installation guidance response.

        Args:
            part_name: Name of part being installed
            guides: List of installation guides
            context: Additional context (time estimates, difficulty, etc.)

        Returns:
            Installation guidance response
        """
        guides_summary = "\n".join(
            [
                f"- {g.get('guide_title', g.get('title', 'Unknown'))}: "
                f"Difficulty: {g.get('difficulty', 'N/A')}, "
                f"Time: {g.get('installation_time', 'N/A')}, "
                f"Video: {'Yes' if g.get('has_video') else 'No'}"
                for g in guides[:5]
            ]
        )

        # Use client-facing system prompt as foundation
        system_prompt = CLIENT_FACING_SYSTEM_PROMPT

        prompt = f"""User needs installation help for: {part_name}

Available Installation Guides:
{guides_summary}

Context:
- Recommended difficulty level: {context.get('recommended_difficulty') if context else 'Any'}
- Time available: {context.get('time_available') if context else 'Flexible'}

Provide helpful installation guidance with numbered steps for clarity.
Mention specific guides, time requirements, and difficulty level.
Recommend professional installation if the task is complex or involves electrical/gas connections.
Always prioritize safety."""

        messages = [{"role": "user", "content": prompt}]

        try:
            return self.generate_response(
                messages,
                system_prompt=system_prompt,
                temperature=0.7,
                max_tokens=500
            )
        except Exception as e:
            logger.error(f"Error generating installation response: {e}")
            return "I encountered an error generating installation guidance. Please try again."

    def check_api_health(self) -> bool:
        """Check if Deepseek API is accessible."""
        if not self.client:
            logger.error("Deepseek client not initialized (missing API key)")
            return False

        try:
            # Simple test message
            response = self.generate_response(
                [{"role": "user", "content": "Say 'ok' in one word"}],
                max_tokens=5,
                temperature=0.0
            )
            is_healthy = len(response) > 0 and "error" not in response.lower()
            if is_healthy:
                logger.info("Deepseek API health check passed")
            return is_healthy
        except Exception as e:
            logger.error(f"Deepseek API health check failed: {e}")
            return False
