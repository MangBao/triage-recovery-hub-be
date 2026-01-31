"""Ticket management API endpoints."""

import logging
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session
from sqlalchemy.sql import func
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.database import get_db
from app.config import settings
from models.ticket import Ticket, TicketStatus
from models.schemas import (
    TicketCreateRequest,
    TicketUpdateRequest,
    TicketResponse,
    TicketListResponse
)
from tasks.triage import process_ticket_triage

logger = logging.getLogger(__name__)
router = APIRouter()

# Rate limiter instance (shared with app via state)
limiter = Limiter(key_func=get_remote_address)


@router.post("", status_code=201, response_model=TicketResponse)
@limiter.limit(f"{settings.RATE_LIMIT_PER_MINUTE}/minute")
def create_ticket(
    ticket_create: TicketCreateRequest,
    request: Request,  # Required for slowapi (param name must be 'request' by default or configured)
    db: Session = Depends(get_db)
):
    """
    Create a new support ticket.
    
    Workflow:
    1. Validate complaint (10-5000 chars, not empty)
    2. Create ticket in database (status=pending)
    3. Enqueue background AI processing task
    4. Return immediately with ticket data
    
    Background task will:
    - Update status to processing
    - Call Gemini API for triage
    - Update category, sentiment, urgency, draft_response
    - Set status to completed or failed
    """
    try:
        # Create ticket
        ticket = Ticket(customer_complaint=ticket_create.customer_complaint)
        db.add(ticket)
        db.commit()
        db.refresh(ticket)
        
        logger.info(f"✅ Ticket {ticket.id} created (status=pending)")
        
        # Enqueue background task (returns immediately)
        process_ticket_triage(ticket.id)
        logger.info(f"📤 Queued triage task for ticket {ticket.id}")
        
        return TicketResponse.model_validate(ticket)
        
    except Exception as e:
        db.rollback()
        logger.error(f"❌ Error creating ticket: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("", response_model=TicketListResponse)
def list_tickets(
    status: str = Query(None, description="Filter by status"),
    urgency: str = Query(None, description="Filter by urgency"),
    limit: int = Query(20, ge=1, le=100, description="Results per page"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
    db: Session = Depends(get_db)
):
    """
    List tickets with optional filters and pagination.
    
    Query params:
    - status: pending|processing|completed|failed
    - urgency: High|Medium|Low
    - limit: max results (1-100, default 20)
    - offset: pagination offset
    
    Returns:
    - total: total matching tickets
    - items: list of tickets (newest first)
    """
    try:
        query = db.query(Ticket)
        
        # Apply filters
        if status:
            query = query.filter(Ticket.status == status)
        if urgency:
            query = query.filter(Ticket.urgency == urgency)
        
        # Count total
        total = query.count()
        
        # Get paginated results (newest first)
        items = query.order_by(Ticket.created_at.desc()).offset(offset).limit(limit).all()
        
        return TicketListResponse(
            total=total,
            items=[TicketResponse.model_validate(item) for item in items]
        )
        
    except Exception as e:
        logger.error(f"❌ Error listing tickets: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/{ticket_id}", response_model=TicketResponse)
def get_ticket(ticket_id: int, db: Session = Depends(get_db)):
    """
    Get single ticket detail by ID.
    
    Useful for polling ticket status during AI processing.
    Frontend can poll every 3 seconds until status != pending.
    """
    try:
        ticket = db.query(Ticket).filter(Ticket.id == ticket_id).first()
        if not ticket:
            raise HTTPException(status_code=404, detail="Ticket not found")
        
        return TicketResponse.model_validate(ticket)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error getting ticket: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.patch("/{ticket_id}", response_model=TicketResponse)
def update_ticket(
    ticket_id: int,
    request: TicketUpdateRequest,
    db: Session = Depends(get_db)
):
    """
    Update ticket (agent edits AI draft response).
    
    Only agent_edited_response can be updated.
    Original AI draft is preserved in ai_draft_response.
    """
    try:
        ticket = db.query(Ticket).filter(Ticket.id == ticket_id).first()
        if not ticket:
            raise HTTPException(status_code=404, detail="Ticket not found")
        
        # Update agent's edited response
        if request.agent_edited_response is not None:
            ticket.agent_edited_response = request.agent_edited_response
        
        db.commit()
        db.refresh(ticket)
        
        logger.info(f"✅ Ticket {ticket_id} updated")
        return TicketResponse.model_validate(ticket)
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"❌ Error updating ticket: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/{ticket_id}/resolve", response_model=TicketResponse)
def resolve_ticket(
    ticket_id: int,
    agent_id: str = Query(..., description="ID of agent resolving ticket"),
    db: Session = Depends(get_db)
):
    """
    Mark ticket as resolved.
    
    Sets:
    - status = completed
    - resolved_at = current timestamp
    - agent_id = provided agent ID
    """
    try:
        ticket = db.query(Ticket).filter(Ticket.id == ticket_id).first()
        if not ticket:
            raise HTTPException(status_code=404, detail="Ticket not found")
        
        # Mark as resolved
        ticket.status = TicketStatus.COMPLETED
        ticket.agent_id = agent_id
        ticket.resolved_at = func.now()
        
        db.commit()
        db.refresh(ticket)
        
        logger.info(f"✅ Ticket {ticket_id} resolved by {agent_id}")
        return TicketResponse.model_validate(ticket)
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"❌ Error resolving ticket: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")
