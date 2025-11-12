"""
Application configuration and settings.

This module uses pydantic-settings for configuration management with environment variables.
Automatically loads .env files from both root and backend directories.
"""

# Load environment variables first (before creating Settings instance)
try:
    from config.env_loader import load_env
    load_env()
except ImportError:
    # Fallback if config.env_loader not available
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        pass

from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Application settings
    app_name: str = "PartSelect Chat API"
    app_version: str = "0.1.0"
    debug: bool = False

    # API server settings
    host: str = "0.0.0.0"
    port: int = 8000

    # LLM settings
    llm_provider: str = "deepseek"  # Could be: deepseek, openai, anthropic, etc.
    llm_api_key: Optional[str] = None
    llm_model: str = "deepseek-chat"

    # Vector database settings
    vector_db_provider: str = "chroma"  # Could be: chroma, pinecone, weaviate, qdrant, etc.

    # ChromaDB settings
    chroma_persist_directory: str = "./chroma_data"
    chroma_host: Optional[str] = None  # Set for client/server mode
    chroma_port: Optional[int] = None  # Set for client/server mode

    # HNSW index configuration for ChromaDB
    hnsw_space: str = "cosine"  # Distance metric: cosine, l2, or ip (inner product)
    hnsw_construction_ef: int = 200  # Index build quality (100-2000, higher = better recall)
    hnsw_search_ef: int = 100  # Search quality (10-500, higher = better recall)
    hnsw_m: int = 16  # Max edges per node (4-64, higher = better recall, more memory)

    # Collection names
    blog_vector_db_collection: str = "blogs"
    repair_vector_db_collection: str = "repairs"
    part_vector_db_collection: str = "parts"

    # Search settings
    top_k: int = 5  # Number of results to fetch from vector DB (sent to LLM)
    response_threshold: float = 0.7  # Minimum similarity score for results returned to user

    # API key for client authentication (optional)
    api_key: Optional[str] = None

    # CORS settings
    allow_origins: list = ["*"]
    allow_credentials: bool = True
    allow_methods: list = ["*"]
    allow_headers: list = ["*"]


# Global settings instance
settings = Settings()
