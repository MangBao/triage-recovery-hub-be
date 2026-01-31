"""Tests for models and schemas."""

import pytest
from pydantic import ValidationError
from models.schemas import TicketCreateRequest, AITriageResponse, TicketCategory, UrgencyLevel


class TestTicketSchemas:
    """Test Pydantic schemas."""
    
    def test_ticket_create_request_valid(self):
        """Test valid ticket creation request."""
        request = TicketCreateRequest(
            customer_complaint="This is a valid complaint with enough text."
        )
        assert len(request.customer_complaint) >= 10
    
    def test_ticket_create_request_too_short(self):
        """Test ticket creation with too short complaint."""
        with pytest.raises(ValidationError):
            TicketCreateRequest(customer_complaint="short")
    
    def test_ticket_create_request_empty(self):
        """Test ticket creation with empty complaint."""
        with pytest.raises(ValidationError):
            TicketCreateRequest(customer_complaint="   ")
    
    def test_ai_triage_response_valid(self):
        """Test valid AI triage response."""
        response = AITriageResponse(
            category=TicketCategory.BILLING,
            sentiment_score=5,
            urgency=UrgencyLevel.HIGH,
            draft_response="This is a valid response."
        )
        assert response.category == TicketCategory.BILLING
        assert response.sentiment_score == 5
        assert response.urgency == UrgencyLevel.HIGH
    
    def test_ai_triage_response_invalid_sentiment(self):
        """Test AI response with invalid sentiment score."""
        with pytest.raises(ValidationError):
            AITriageResponse(
                category=TicketCategory.BILLING,
                sentiment_score=15,  # Out of range (1-10)
                urgency=UrgencyLevel.HIGH,
                draft_response="This is a valid draft response text."
            )
    
    def test_ai_triage_response_invalid_category(self):
        """Test AI response with invalid category."""
        with pytest.raises(ValidationError):
            AITriageResponse(
                category="InvalidCategory",
                sentiment_score=5,
                urgency=UrgencyLevel.HIGH,
                draft_response="This is a valid draft response text."
            )
