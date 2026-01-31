"""Centralized enum definitions for the application.

All enums should be defined here and imported elsewhere to avoid duplication.
"""

from enum import Enum


class TicketStatus(str, Enum):
    """Ticket processing status."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class TicketCategory(str, Enum):
    """Ticket category determined by AI."""
    BILLING = "Billing"
    TECHNICAL = "Technical"
    FEATURE_REQUEST = "Feature Request"


class UrgencyLevel(str, Enum):
    """Ticket urgency level determined by AI."""
    HIGH = "High"
    MEDIUM = "Medium"
    LOW = "Low"


class AIStatus(str, Enum):
    """AI processing result status."""
    SUCCESS = "success"      # Gemini returned valid response
    FALLBACK = "fallback"    # Used fallback due to API error
    ERROR = "error"          # Hard failure (should not happen often)
