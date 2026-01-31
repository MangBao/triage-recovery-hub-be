"""SQLAlchemy ORM models for ticket management."""

from sqlalchemy import Column, Integer, String, Text, Enum, DateTime, CheckConstraint
from sqlalchemy.sql import func

from app.database import Base
from models.enums import TicketStatus, TicketCategory, UrgencyLevel


class Ticket(Base):
    """
    Customer support ticket with AI-powered triage.
    
    Workflow:
    1. Created with customer_complaint (status=pending)
    2. Background task processes with AI (status=processing)
    3. AI fills category, sentiment, urgency, draft_response (status=completed)
    4. Agent can edit draft and resolve ticket
    """
    __tablename__ = "tickets"
    __table_args__ = (
        CheckConstraint(
            'sentiment_score IS NULL OR (sentiment_score >= 1 AND sentiment_score <= 10)',
            name='valid_sentiment_score'
        ),
    )
    
    # Primary key
    id = Column(Integer, primary_key=True, index=True)
    
    # Customer input
    customer_complaint = Column(Text, nullable=False)
    status = Column(Enum(TicketStatus), default=TicketStatus.PENDING, index=True)
    
    # AI Processing Results
    category = Column(Enum(TicketCategory), nullable=True)
    sentiment_score = Column(Integer, nullable=True)  # 1-10 scale (validated by constraint)
    urgency = Column(Enum(UrgencyLevel), nullable=True, index=True)
    ai_draft_response = Column(Text, nullable=True)
    
    # Agent Actions
    agent_edited_response = Column(Text, nullable=True)
    resolved_at = Column(DateTime(timezone=True), nullable=True)
    agent_id = Column(String(255), nullable=True, index=True)  # Added index for filtering
    
    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)  # Added index for ORDER BY
    updated_at = Column(
        DateTime(timezone=True), 
        server_default=func.now(), 
        onupdate=func.now()
    )
    error_message = Column(Text, nullable=True)
    
    def __repr__(self):
        return f"<Ticket(id={self.id}, status={self.status}, urgency={self.urgency})>"
