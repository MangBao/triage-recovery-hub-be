"""Initial database schema for Triage & Recovery Hub.

Revision ID: 001_initial_schema
Revises: 
Create Date: 2026-01-31

Creates the complete tickets table with all columns, indexes, and constraints.
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '001_initial_schema'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    """Create tickets table with all columns, indexes, and constraints."""
    op.create_table(
        'tickets',
        # Primary key
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        
        # Customer input
        sa.Column('customer_complaint', sa.Text(), nullable=False),
        sa.Column('status', sa.Enum('pending', 'processing', 'completed', 'failed', 
                                    name='ticketstatus'), 
                  nullable=False, server_default='pending'),
        
        # AI Processing Results
        sa.Column('category', sa.Enum('Billing', 'Technical', 'Feature Request', 
                                       name='ticketcategory'), 
                  nullable=True),
        sa.Column('sentiment_score', sa.Integer(), nullable=True),
        sa.Column('urgency', sa.Enum('High', 'Medium', 'Low', name='urgencylevel'), 
                  nullable=True),
        sa.Column('ai_draft_response', sa.Text(), nullable=True),
        sa.Column('ai_status', sa.Enum('success', 'fallback', 'error', name='aistatus'), 
                  nullable=True),
        
        # Agent Actions
        sa.Column('agent_edited_response', sa.Text(), nullable=True),
        sa.Column('resolved_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('agent_id', sa.String(255), nullable=True),
        
        # Metadata
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), 
                  nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), 
                  onupdate=sa.func.now(), nullable=False),
        sa.Column('error_message', sa.Text(), nullable=True),
        
        # Constraints
        sa.CheckConstraint(
            'sentiment_score IS NULL OR (sentiment_score >= 1 AND sentiment_score <= 10)',
            name='valid_sentiment_score'
        ),
    )
    
    # Create indexes for common query patterns
    op.create_index('ix_tickets_id', 'tickets', ['id'], unique=True)
    op.create_index('ix_tickets_status', 'tickets', ['status'], unique=False)
    op.create_index('ix_tickets_urgency', 'tickets', ['urgency'], unique=False)
    op.create_index('ix_tickets_created_at', 'tickets', ['created_at'], unique=False)
    op.create_index('ix_tickets_agent_id', 'tickets', ['agent_id'], unique=False)


def downgrade():
    """Drop tickets table and all related objects."""
    # Drop indexes first
    op.drop_index('ix_tickets_agent_id', 'tickets')
    op.drop_index('ix_tickets_created_at', 'tickets')
    op.drop_index('ix_tickets_urgency', 'tickets')
    op.drop_index('ix_tickets_status', 'tickets')
    op.drop_index('ix_tickets_id', 'tickets')
    
    # Drop table (this also drops constraints)
    op.drop_table('tickets')
    
    # Drop enum types (PostgreSQL specific)
    op.execute('DROP TYPE IF EXISTS ticketstatus')
    op.execute('DROP TYPE IF EXISTS ticketcategory')
    op.execute('DROP TYPE IF EXISTS urgencylevel')
    op.execute('DROP TYPE IF EXISTS aistatus')
