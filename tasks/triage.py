"""Background task for AI-powered ticket triage."""

import logging
import time
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import update

from tasks.worker import huey
from app.database import SessionLocal
from app.config import settings
from app.pubsub import publish_ticket_update
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
        
        # Atomic claim: Only process if status is PENDING (prevents race condition)
        # This UPDATE only affects rows WHERE status=PENDING, returning rowcount
        result = db.execute(
            update(Ticket)
            .where(Ticket.id == ticket_id, Ticket.status == TicketStatus.PENDING)
            .values(status=TicketStatus.PROCESSING)
        )
        db.commit()
        
        if result.rowcount == 0:
            logger.warning(
                f"[WORKER] Skipping ticket {ticket_id}: already claimed or not pending. "
                "This may happen if another worker processed it or an agent manually resolved."
            )
            return
        
        # Refresh ticket to sync ORM state with DB after atomic update
        db.refresh(ticket)
        
        logger.info(f"[WORKER] Ticket {ticket_id} claimed and marked as processing")
        
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
        
        # Publish update to Redis for WebSocket broadcast
        publish_ticket_update(ticket_id, {
            "id": ticket.id,
            "status": ticket.status.value,
            "category": ticket.category.value if ticket.category else None,
            "urgency": ticket.urgency.value if ticket.urgency else None,
            "sentiment_score": ticket.sentiment_score,
            "ai_status": ticket.ai_status.value if ticket.ai_status else None,
            "ai_draft_response": ticket.ai_draft_response,
            "updated_at": str(ticket.updated_at)
        })
        
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
                
                # Publish failure to Redis for WebSocket broadcast
                publish_ticket_update(ticket_id, {
                    "id": ticket.id,
                    "status": ticket.status.value,
                    "error_message": ticket.error_message,
                    "updated_at": str(ticket.updated_at)
                })
                
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
