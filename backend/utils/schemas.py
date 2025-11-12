# Pydantic models and schemas
from pydantic import BaseModel
from typing import Optional, List

class Product(BaseModel):
    part_number: str
    name: str
    description: Optional[str] = None
    price: Optional[float] = None
    compatible_models: List[str] = []

class Intent(BaseModel):
    intent_type: str
    confidence: float

class TroubleshootingIssue(BaseModel):
    issue: str
    appliance_type: Optional[str] = None
    symptoms: List[str] = []

class InstallationGuide(BaseModel):
    part_number: str
    steps: List[str]
    tools_required: List[str] = []
    difficulty: str = "medium"
