"""
Pydantic models for request/response schemas and domain objects.
"""
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any


class Blog(BaseModel):
    """Blog article resource."""
    name: str = Field(..., description="Title/name of the blog article")
    url: str = Field(..., description="URL to the blog article")
    similarity_score: float = Field(..., description="Similarity score from vector search")
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="Additional blog-specific data")

    class Config:
        json_schema_extra = {
            "example": {
                "name": "How to Fix a Leaking Dishwasher",
                "url": "https://example.com/blog/fix-leaking-dishwasher",
                "similarity_score": 0.92,
                "metadata": {"author": "John Doe", "published_date": "2024-01-15"}
            }
        }


class Repair(BaseModel):
    """Repair guide resource."""
    name: str = Field(..., description="Title/name of the repair guide")
    url: str = Field(..., description="URL to the repair guide")
    similarity_score: float = Field(..., description="Similarity score from vector search")
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="Additional repair-specific data")

    class Config:
        json_schema_extra = {
            "example": {
                "name": "Refrigerator Ice Maker Repair",
                "url": "https://example.com/repair/refrigerator-ice-maker",
                "similarity_score": 0.88,
                "metadata": {"difficulty": "intermediate", "estimated_time": "30-45 minutes"}
            }
        }


class Part(BaseModel):
    """Replacement part resource."""
    name: str = Field(..., description="Name/model of the replacement part")
    url: str = Field(..., description="URL to the part details page")
    similarity_score: float = Field(..., description="Similarity score from vector search")
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="Additional part-specific data")

    class Config:
        json_schema_extra = {
            "example": {
                "name": "Dishwasher Water Inlet Valve WPW10195677",
                "url": "https://example.com/part/WPW10195677",
                "similarity_score": 0.95,
                "metadata": {"price": 29.99, "in_stock": True, "part_number": "WPW10195677"}
            }
        }


class ChatRequest(BaseModel):
    """Request model for chat endpoint."""
    query: str = Field(..., description="User's question or query", min_length=1)

    class Config:
        json_schema_extra = {
            "example": {
                "query": "My dishwasher is leaking water from the bottom. What could be wrong?"
            }
        }


class ChatResponse(BaseModel):
    """Response model for chat endpoint."""
    response: str = Field(..., description="LLM-generated response to the user query")
    blogs: List[Blog] = Field(default_factory=list, description="Relevant blog articles (above threshold)")
    repairs: List[Repair] = Field(default_factory=list, description="Relevant repair guides (above threshold)")
    parts: List[Part] = Field(default_factory=list, description="Relevant replacement parts (above threshold)")

    class Config:
        json_schema_extra = {
            "example": {
                "response": "A leaking dishwasher is often caused by a faulty water inlet valve or door seal. I recommend checking these components first...",
                "blogs": [
                    {
                        "name": "Common Dishwasher Leak Causes",
                        "url": "https://example.com/blog/dishwasher-leaks",
                        "similarity_score": 0.92,
                        "metadata": {}
                    }
                ],
                "repairs": [
                    {
                        "name": "Fix Dishwasher Water Leak",
                        "url": "https://example.com/repair/dishwasher-leak",
                        "similarity_score": 0.89,
                        "metadata": {}
                    }
                ],
                "parts": [
                    {
                        "name": "Water Inlet Valve",
                        "url": "https://example.com/part/inlet-valve",
                        "similarity_score": 0.87,
                        "metadata": {}
                    }
                ]
            }
        }


class SearchResult(BaseModel):
    """Generic search result container for internal use."""
    name: str
    url: str
    similarity_score: float
    metadata: Optional[Dict[str, Any]] = None
