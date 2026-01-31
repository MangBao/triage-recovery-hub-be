"""Background task for AI-powered ticket triage."""

import logging
import time
from sqlalchemy.exc import SQLAlchemyError

from tasks.worker import huey
from app.database import SessionLocal
from app.config import settings
from models.ticket import Ticket, TicketStatus
from models.enums import AIStatus
from services.llm import triage_service

logger = logging.getLogger(__name__)


@huey.task(retries=3, retry_delay=5)
def process_ticket_triage(ticket_id: int):
    """
    Background task: Process ticket with Gemini AI triage.
    
    Features:
    - Retries 3 times with 5 second delay on failure
    - Database transaction handling with rollback
    - Comprehensive error logging
    - Status updates: pending → processing → completed/failed
    - Fallback responses via triage_service
    - API timeout protection
    
    Args:
        ticket_id: ID of ticket to process
    """
    db = SessionLocal()
    
    try:
        logger.info(f"[WORKER] Starting triage for ticket {ticket_id}")
        start_time = time.time()
        
        # Get ticket
        ticket = db.query(Ticket).filter(Ticket.id == ticket_id).first()
        if not ticket:
            logger.error(f"[WORKER] Ticket {ticket_id} not found!")
            return
        
        # Race condition protection: Only process if still PENDING
        if ticket.status != TicketStatus.PENDING:
            logger.warning(
                f"[WORKER] Skipping ticket {ticket_id}: status is {ticket.status.value}, not PENDING. "
                "This may happen if an agent manually resolved the ticket."
            )
            return
        
        # Update status to processing
        ticket.status = TicketStatus.PROCESSING
        db.commit()
        logger.info(f"[WORKER] Ticket {ticket_id} marked as processing")
        
        # Call Gemini API (triage_service has internal timeout handling)
        logger.info(f"[WORKER] Calling Gemini for ticket {ticket_id}...")
        ai_response = triage_service.triage_complaint(
            ticket.customer_complaint,
            timeout=settings.API_TIMEOUT_SECONDS
        )
        
        if not ai_response:
            raise ValueError("Gemini service returned None")
        
        # Update ticket with AI results
        ticket.category = ai_response.category
        ticket.sentiment_score = ai_response.sentiment_score
        ticket.urgency = ai_response.urgency
        ticket.ai_draft_response = ai_response.draft_response
        ticket.ai_status = ai_response.ai_status  # Track if success or fallback
        ticket.status = TicketStatus.COMPLETED
        ticket.error_message = None
        
        db.commit()
        
        elapsed = time.time() - start_time
        logger.info(
            f"[WORKER] ✅ Completed for ticket {ticket_id} "
            f"({elapsed:.2f}s): {ai_response.category.value}, "
            f"Urgency={ai_response.urgency.value}, Sentiment={ai_response.sentiment_score}"
        )
        
    except Exception as e:
        logger.error(f"[WORKER] ❌ Error for ticket {ticket_id}: {str(e)}", exc_info=True)
        
        # Rollback any pending transaction before attempting status update
        db.rollback()
        
        # Update ticket with error status
        try:
            ticket = db.query(Ticket).filter(Ticket.id == ticket_id).first()
            if ticket:
                ticket.status = TicketStatus.FAILED
                ticket.error_message = str(e)[:500]  # Truncate long errors
                db.commit()
                logger.info(f"[WORKER] Updated ticket {ticket_id} status to failed")
        except SQLAlchemyError as db_error:
            logger.error(f"[WORKER] Failed to update error status: {db_error}")
        
        # Re-raise for Huey retry logic
        raise
    
    finally:
        try:
            db.close()
        except Exception as e:
            logger.error(f"[WORKER] Error closing database: {e}")
