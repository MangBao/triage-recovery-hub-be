"""Pydantic schemas for request/response validation."""

from pydantic import BaseModel, Field, field_validator
from typing import Optional
from datetime import datetime

# Import centralized enums (single source of truth)
from models.enums import TicketStatus, TicketCategory, UrgencyLevel, AIStatus


# Request Schemas

class TicketCreateRequest(BaseModel):
    """Request body for creating a new ticket."""
    customer_complaint: str = Field(..., min_length=10, max_length=5000)
    
    @field_validator('customer_complaint', mode='before')
    @classmethod
    def complaint_not_empty(cls, v: str) -> str:
        """Strip whitespace before length validation to prevent bypass."""
        if not isinstance(v, str):
            return v  # Let Pydantic handle type validation
        stripped = v.strip()
        if not stripped:
            raise ValueError('Complaint cannot be empty')
        return stripped


class TicketUpdateRequest(BaseModel):
    """Request body for updating ticket (agent edits)."""
    agent_edited_response: Optional[str] = Field(None, max_length=2000)


# AI Response Schema (for validation)

class AITriageResponse(BaseModel):
    """
    Expected structure from Gemini API.
    Used for validation of AI output.
    """
    category: TicketCategory
    sentiment_score: int = Field(..., ge=1, le=10)
    urgency: UrgencyLevel
    draft_response: str = Field(..., min_length=20, max_length=2000)
    ai_status: AIStatus = AIStatus.SUCCESS  # Default to success, service overrides for fallback
    
    model_config = {
        "use_enum_values": False
    }


# Response Schemas

class TicketResponse(BaseModel):
    """API response for single ticket."""
    id: int
    customer_complaint: str
    status: TicketStatus
    category: Optional[TicketCategory]
    sentiment_score: Optional[int]
    urgency: Optional[UrgencyLevel]
    ai_draft_response: Optional[str]
    ai_status: Optional[AIStatus]  # success, fallback, error
    agent_edited_response: Optional[str]
    resolved_at: Optional[datetime]
    agent_id: Optional[str]
    created_at: datetime
    updated_at: datetime
    error_message: Optional[str]
    
    model_config = {
        "from_attributes": True  # Allow SQLAlchemy model conversion
    }


class TicketListResponse(BaseModel):
    """API response for ticket list with pagination."""
    total: int
    items: list[TicketResponse]
