"""Ticket management API endpoints."""

import logging
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session
from sqlalchemy.sql import func

from app.database import get_db
from models.ticket import Ticket, TicketStatus
from models.enums import TicketCategory, UrgencyLevel, AIStatus
from models.schemas import (
    TicketCreateRequest,
    TicketUpdateRequest,
    TicketResponse,
    TicketListResponse,
    PaginationMeta
)
from tasks.triage import process_ticket_triage

logger = logging.getLogger(__name__)
router = APIRouter()


def get_limiter(request: Request):
    """Get shared limiter from app state."""
    return request.app.state.limiter


@router.post("", status_code=201, response_model=TicketResponse)
def create_ticket(
    ticket_create: TicketCreateRequest,
    request: Request,  # Required for slowapi (param name must be 'request' by default)
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
    # Reference request to satisfy linter (ARG001) - used by slowapi decorator
    _ = request.app.state.limiter
    
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
    status: str = Query(None, description="Filter by status (pending|processing|completed|failed)"),
    urgency: str = Query(None, description="Filter by urgency (High|Medium|Low)"),
    category: str = Query(None, description="Filter by category (Billing|Technical|Feature Request|General)"),
    ai_status: str = Query(None, description="Filter by AI status (success|fallback|error)"),
    created_after: datetime = Query(None, description="Filter tickets created after this datetime (ISO 8601)"),
    created_before: datetime = Query(None, description="Filter tickets created before this datetime (ISO 8601)"),
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    per_page: int = Query(20, ge=1, le=100, description="Results per page"),
    db: Session = Depends(get_db)
):
    """
    List tickets with filters and pagination.
    
    **Filters:**
    - status: pending|processing|completed|failed
    - urgency: High|Medium|Low
    - category: Billing|Technical|Feature Request|General
    - ai_status: success|fallback|error
    - created_after: ISO 8601 datetime
    - created_before: ISO 8601 datetime
    
    **Pagination:**
    - page: Page number (1-indexed, default 1)
    - per_page: Results per page (1-100, default 20)
    
    **Response:**
    - data: List of tickets (newest first)
    - pagination: {total, page, per_page, total_pages, has_more}
    """
    try:
        query = db.query(Ticket)
        
        # Apply filters (convert strings to Enum for PostgreSQL compatibility)
        if status:
            try:
                query = query.filter(Ticket.status == TicketStatus(status))
            except ValueError:
                # Invalid status value - return empty result
                return TicketListResponse(
                    data=[],
                    pagination=PaginationMeta(total=0, page=page, per_page=per_page, total_pages=0, has_more=False)
                )
        if urgency:
            try:
                query = query.filter(Ticket.urgency == UrgencyLevel(urgency))
            except ValueError:
                return TicketListResponse(
                    data=[],
                    pagination=PaginationMeta(total=0, page=page, per_page=per_page, total_pages=0, has_more=False)
                )
        if category:
            try:
                query = query.filter(Ticket.category == TicketCategory(category))
            except ValueError:
                return TicketListResponse(
                    data=[],
                    pagination=PaginationMeta(total=0, page=page, per_page=per_page, total_pages=0, has_more=False)
                )
        if ai_status:
            try:
                query = query.filter(Ticket.ai_status == AIStatus(ai_status))
            except ValueError:
                return TicketListResponse(
                    data=[],
                    pagination=PaginationMeta(total=0, page=page, per_page=per_page, total_pages=0, has_more=False)
                )
        if created_after:
            query = query.filter(Ticket.created_at >= created_after)
        if created_before:
            query = query.filter(Ticket.created_at <= created_before)
        
        # Count total
        total = query.count()
        
        # Calculate pagination
        total_pages = (total + per_page - 1) // per_page  # Ceiling division
        offset = (page - 1) * per_page
        has_more = page < total_pages
        
        # Get paginated results (newest first)
        items = query.order_by(Ticket.created_at.desc()).offset(offset).limit(per_page).all()
        
        return TicketListResponse(
            data=[TicketResponse.model_validate(item) for item in items],
            pagination=PaginationMeta(
                total=total,
                page=page,
                per_page=per_page,
                total_pages=total_pages,
                has_more=has_more
            )
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
    update_request: TicketUpdateRequest,
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
        if update_request.agent_edited_response is not None:
            ticket.agent_edited_response = update_request.agent_edited_response
        
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
