"""JSON validation and error handling for AI responses."""

import json
import logging
from typing import Optional, Dict, Any
from pydantic import ValidationError

from models.schemas import AITriageResponse

logger = logging.getLogger(__name__)


class ValidationService:
    """
    Validates and sanitizes AI responses.
    
    Handles:
    - Malformed JSON (markdown blocks, extra whitespace)
    - Missing or invalid fields
    - Fallback responses when validation fails
    """
    
    @staticmethod
    def safe_parse_json(response_text: str) -> Optional[Dict[str, Any]]:
        """
        Safely parse Gemini response as JSON.
        
        Handles edge cases:
        - Markdown code blocks (```json ... ```)
        - Leading/trailing whitespace
        - Partial JSON responses
        
        Args:
            response_text: Raw response from Gemini API
            
        Returns:
            Parsed JSON dict or None if parsing fails
        """
        # Handle non-string input to prevent TypeError
        if not isinstance(response_text, str):
            logger.error(f"Expected string, got {type(response_text).__name__}")
            return None
        
        try:
            # Try direct parse first
            return json.loads(response_text)
        except json.JSONDecodeError:
            # Try cleaning markdown blocks
            cleaned = response_text.strip()
            
            if cleaned.startswith('```json'):
                cleaned = cleaned[7:]
            elif cleaned.startswith('```'):
                cleaned = cleaned[3:]
            
            if cleaned.endswith('```'):
                cleaned = cleaned[:-3]
            
            try:
                return json.loads(cleaned.strip())
            except json.JSONDecodeError:
                logger.error(f"Failed to parse JSON: {response_text[:100]}...")
                return None
    
    @staticmethod
    def validate_ai_response(response_data: Dict[str, Any]) -> Optional[AITriageResponse]:
        """
        Validate AI response against Pydantic schema.
        
        Args:
            response_data: Parsed JSON from Gemini
            
        Returns:
            Validated AITriageResponse or None if validation fails
        """
        try:
            validated = AITriageResponse(**response_data)
            return validated
        except ValidationError as e:
            logger.error(f"Schema validation failed: {e}")
            logger.debug(f"Invalid response data: {response_data}")
            return None
    
    @staticmethod
    def get_fallback_response() -> AITriageResponse:
        """
        Return safe fallback response when Gemini fails.
        
        This ensures the system doesn't crash on bad AI output.
        Tickets will still be created with generic categorization.
        
        Returns:
            Safe fallback AITriageResponse
        """
        return AITriageResponse(
            category="Technical",
            sentiment_score=5,
            urgency="Medium",
            draft_response=(
                "Thank you for contacting us. We appreciate your feedback. "
                "We're reviewing your concern and will get back to you shortly. "
                "Our support team aims to respond within 24 hours."
            )
        )


validation_service = ValidationService()
