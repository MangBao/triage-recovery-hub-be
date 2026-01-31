"""Tests for API endpoints."""

import pytest
from models.ticket import Ticket, TicketStatus


class TestTicketAPI:
    """Test ticket API endpoints."""
    
    def test_health_check(self, client):
        """Test health check endpoint."""
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "ok", "service": "triage-recovery-hub"}
    
    def test_create_ticket(self, client, sample_complaint):
        """Test creating a new ticket."""
        response = client.post(
            "/api/tickets",
            json={"customer_complaint": sample_complaint}
        )
        
        assert response.status_code == 201
        data = response.json()
        assert data["customer_complaint"] == sample_complaint
        assert data["status"] == "pending"
        assert data["id"] is not None
        assert data["category"] is None  # AI hasn't processed yet
    
    def test_create_ticket_validation_error(self, client):
        """Test creating ticket with invalid data."""
        # Too short
        response = client.post(
            "/api/tickets",
            json={"customer_complaint": "short"}
        )
        assert response.status_code == 422
        
        # Empty
        response = client.post(
            "/api/tickets",
            json={"customer_complaint": ""}
        )
        assert response.status_code == 422
    
    def test_list_tickets(self, client, db_session, sample_complaint):
        """Test listing tickets."""
        # Create test tickets
        ticket1 = Ticket(customer_complaint=sample_complaint)
        ticket2 = Ticket(customer_complaint="Another complaint")
        db_session.add_all([ticket1, ticket2])
        db_session.commit()
        
        response = client.get("/api/tickets")
        assert response.status_code == 200
        
        data = response.json()
        assert data["total"] == 2
        assert len(data["items"]) == 2
    
    def test_list_tickets_with_filters(self, client, db_session):
        """Test listing tickets with status filter."""
        ticket1 = Ticket(customer_complaint="Test 1", status=TicketStatus.PENDING)
        ticket2 = Ticket(customer_complaint="Test 2", status=TicketStatus.COMPLETED)
        db_session.add_all([ticket1, ticket2])
        db_session.commit()
        
        # Filter by pending
        response = client.get("/api/tickets?status=pending")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["items"][0]["status"] == "pending"
    
    def test_get_ticket(self, client, db_session, sample_complaint):
        """Test getting a single ticket."""
        ticket = Ticket(customer_complaint=sample_complaint)
        db_session.add(ticket)
        db_session.commit()
        db_session.refresh(ticket)
        
        response = client.get(f"/api/tickets/{ticket.id}")
        assert response.status_code == 200
        
        data = response.json()
        assert data["id"] == ticket.id
        assert data["customer_complaint"] == sample_complaint
    
    def test_get_ticket_not_found(self, client):
        """Test getting non-existent ticket."""
        response = client.get("/api/tickets/999")
        assert response.status_code == 404
    
    def test_update_ticket(self, client, db_session, sample_complaint):
        """Test updating ticket (agent edit)."""
        ticket = Ticket(customer_complaint=sample_complaint)
        db_session.add(ticket)
        db_session.commit()
        db_session.refresh(ticket)
        
        edited_response = "We've resolved this issue for you."
        response = client.patch(
            f"/api/tickets/{ticket.id}",
            json={"agent_edited_response": edited_response}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["agent_edited_response"] == edited_response
    
    def test_resolve_ticket(self, client, db_session, sample_complaint):
        """Test resolving a ticket."""
        ticket = Ticket(customer_complaint=sample_complaint)
        db_session.add(ticket)
        db_session.commit()
        db_session.refresh(ticket)
        
        agent_id = "agent_001"
        response = client.post(f"/api/tickets/{ticket.id}/resolve?agent_id={agent_id}")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "completed"
        assert data["agent_id"] == agent_id
        assert data["resolved_at"] is not None
