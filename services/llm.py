"""Google Gemini API integration for ticket triage."""

import logging
from typing import Optional
import google.generativeai as genai

from app.config import settings
from models.schemas import AITriageResponse
from services.validation import validation_service

logger = logging.getLogger(__name__)


class TriageService:
    """
    Google Gemini API service for customer complaint triage.
    
    Features:
    - FREE tier (1500 requests/day, 60/min)
    - No credit card required
    - JSON output with validation
    - Automatic fallback on errors
    - Comprehensive logging
    """
    
    def __init__(self):
        """Initialize Gemini API client."""
        genai.configure(api_key=settings.GOOGLE_API_KEY)
        self.model = genai.GenerativeModel(settings.GOOGLE_MODEL)
    
    def triage_complaint(self, complaint: str, timeout: int = 30) -> Optional[AITriageResponse]:
        """
        Call Gemini to analyze and triage customer complaint.
        
        Args:
            complaint: Customer complaint text
            timeout: Request timeout in seconds (default 30)
            
        Returns:
            AITriageResponse with category, sentiment, urgency, draft_response
            or fallback response if AI fails
        """
        prompt = self._build_prompt(complaint)
        
        try:
            # Log without PII (complaint content only at DEBUG level)
            logger.info(f"[TRIAGE] Starting triage for complaint (length={len(complaint)} chars)")
            logger.debug(f"[TRIAGE] Complaint preview: {complaint[:50]}...")
            
            # Call Gemini API (FREE tier)
            response = self.model.generate_content(prompt)
            response_text = response.text.strip()
            # DEBUG: Raw response may contain reflected PII - only log in development
            if settings.DEBUG:
                logger.debug(f"[TRIAGE] Raw response preview: {response_text[:200]}")
            
            # Parse JSON
            response_json = validation_service.safe_parse_json(response_text)
            if not response_json:
                logger.error("[TRIAGE] Failed to parse JSON, using fallback")
                return validation_service.get_fallback_response()
            
            # Validate against schema
            validated = validation_service.validate_ai_response(response_json)
            if not validated:
                logger.error("[TRIAGE] Schema validation failed, using fallback")
                return validation_service.get_fallback_response()
            
            logger.info(
                f"[TRIAGE] ✅ Success: {validated.category.value}, "
                f"Urgency={validated.urgency.value}, Sentiment={validated.sentiment_score}"
            )
            return validated
            
        except Exception as e:
            logger.error(f"[TRIAGE] ❌ Gemini error: {str(e)}")
            return validation_service.get_fallback_response()
    
    @staticmethod
    def _build_prompt(complaint: str) -> str:
        """
        Build the prompt for Gemini API.
        
        Designed to maximize JSON output reliability:
        - Clear structure definition
        - Explicit constraints
        - No extra text requested
        
        Args:
            complaint: Customer complaint text
            
        Returns:
            Formatted prompt string
        """
        return f"""You are a customer support triage assistant. Analyze this customer complaint and respond with ONLY valid JSON.

Customer Complaint:
{complaint}

Respond with exactly this JSON structure:
{{
  "category": "Billing" or "Technical" or "Feature Request",
  "sentiment_score": number between 1 and 10 (1=very angry, 10=very satisfied),
  "urgency": "High" or "Medium" or "Low",
  "draft_response": "polite, professional response addressing their concern"
}}

IMPORTANT RULES:
1. Return ONLY the JSON object (no markdown, no code blocks)
2. No explanations or extra text before/after JSON
3. Ensure all field values are valid and within specified ranges
4. draft_response must be 20-2000 characters
5. Use double quotes for JSON strings
6. Categories are case-sensitive: "Billing", "Technical", "Feature Request"
7. Urgency levels are case-sensitive: "High", "Medium", "Low"
"""


triage_service = TriageService()
