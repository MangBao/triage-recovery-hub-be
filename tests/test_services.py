"""Tests for service layers."""

import pytest
from unittest.mock import Mock, patch
from models.schemas import AITriageResponse, TicketCategory, UrgencyLevel
from services.validation import validation_service


class TestValidationService:
    """Test JSON validation service."""
    
    def test_safe_parse_json_valid(self):
        """Test parsing valid JSON."""
        json_str = '{"category": "Billing", "sentiment_score": 5}'
        result = validation_service.safe_parse_json(json_str)
        assert result is not None
        assert result["category"] == "Billing"
    
    def test_safe_parse_json_with_markdown(self):
        """Test parsing JSON wrapped in markdown."""
        json_str = '```json\n{"category": "Billing"}\n```'
        result = validation_service.safe_parse_json(json_str)
        assert result is not None
        assert result["category"] == "Billing"
    
    def test_safe_parse_json_invalid(self):
        """Test parsing invalid JSON."""
        json_str = 'not valid json'
        result = validation_service.safe_parse_json(json_str)
        assert result is None
    
    def test_validate_ai_response_valid(self):
        """Test validating correct AI response."""
        data = {
            "category": "Billing",
            "sentiment_score": 5,
            "urgency": "High",
            "draft_response": "We apologize for the issue."
        }
        result = validation_service.validate_ai_response(data)
        assert result is not None
        assert result.category == TicketCategory.BILLING
        assert result.sentiment_score == 5
    
    def test_validate_ai_response_invalid(self):
        """Test validating incorrect AI response."""
        # Missing required field
        data = {
            "category": "Billing",
            "sentiment_score": 5
        }
        result = validation_service.validate_ai_response(data)
        assert result is None
        
        # Invalid sentiment score
        data = {
            "category": "Billing",
            "sentiment_score": 15,  # Out of range
            "urgency": "High",
            "draft_response": "Test"
        }
        result = validation_service.validate_ai_response(data)
        assert result is None
    
    def test_get_fallback_response(self):
        """Test fallback response generation."""
        fallback = validation_service.get_fallback_response()
        assert isinstance(fallback, AITriageResponse)
        assert fallback.category == TicketCategory.TECHNICAL
        assert fallback.urgency == UrgencyLevel.MEDIUM
        assert len(fallback.draft_response) > 0


class TestTriageService:
    """Test Gemini AI service."""
    
    def test_triage_complaint_success(self, sample_complaint):
        """Test successful AI triage."""
        from services.llm import triage_service, TriageService
        
        # Mock the model instance within the service
        with patch.object(triage_service.model, 'generate_content') as mock_generate:
            # Setup mock response
            mock_response = Mock()
            mock_response.text = '''{
                "category": "Billing",
                "sentiment_score": 3,
                "urgency": "High",
                "draft_response": "We sincerely apologize for the double charge."
            }'''
            mock_generate.return_value = mock_response
            
            # Call service
            result = triage_service.triage_complaint(sample_complaint)
            
            # Assertions
            assert result is not None
            assert result.category == TicketCategory.BILLING
            assert result.sentiment_score == 3
            assert result.urgency == UrgencyLevel.HIGH
            assert "apologize" in result.draft_response
            
            # Verify mock call
            mock_generate.assert_called_once()

    def test_triage_complaint_fallback(self, sample_complaint):
        """Test fallback when AI fails."""
        from services.llm import triage_service
        
        # Mock the model to raise an exception
        with patch.object(triage_service.model, 'generate_content') as mock_generate:
            mock_generate.side_effect = Exception("API Error")
            
            # Call service
            result = triage_service.triage_complaint(sample_complaint)
            
            # Assertions - should return fallback
            assert result is not None
            assert result.category == TicketCategory.TECHNICAL  # Fallback default
            assert result.urgency == UrgencyLevel.MEDIUM     # Fallback default
            
            # Verify mock call
            mock_generate.assert_called_once()
