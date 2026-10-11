from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
import uuid

class DisposalInstruction(BaseModel):
    step: int
    action: str
    detail: str

class ClassificationResult(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    category: str
    confidence: Optional[float] = None
    label: str
    explanation: str
    disposalInstructions: List[DisposalInstruction] = []
    precautions: List[str] = []
    recyclable: bool
    checkLocal: bool
    isDemo: bool = False
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())

class ScanRecord(BaseModel):
    id: str
    category: str
    label: str
    confidence: Optional[float] = None
    recyclable: bool
    timestamp: str
    isDemo: bool = False

class HistoryDeleteResponse(BaseModel):
    deleted: int

class HealthResponse(BaseModel):
    status: str
    ai_provider: str
    demo_mode: bool
    aws_configured: bool
