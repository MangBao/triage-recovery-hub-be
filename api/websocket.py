"""WebSocket endpoint for real-time ticket updates."""

import logging
import asyncio
import json
from collections import defaultdict
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from typing import List, Dict, Set

from app.pubsub import subscribe_ticket_updates_async

logger = logging.getLogger(__name__)
router = APIRouter()


class ConnectionManager:
    """Manages WebSocket connections and broadcasts status updates."""
    
    def __init__(self):
        # ticket_id -> set of websockets
        self.active_connections: Dict[int, Set[WebSocket]] = defaultdict(set)
        # Keep track of anonymous/general connections if needed (future use)
        self.all_connections: Set[WebSocket] = set()
        # Background task for Redis subscription
        self.redis_task = None
        
    async def connect(self, websocket: WebSocket):
        """Accept connection and start Redis listener if needed."""
        await websocket.accept()
        self.all_connections.add(websocket)
        logger.info(f"🔌 WebSocket connected. Total: {len(self.all_connections)}")
        
        # Start Redis listener lazily on first connection
        if not self.redis_task:
            logger.info("🚀 Starting Redis Subscriber Task")
            self.redis_task = asyncio.create_task(
                subscribe_ticket_updates_async(self.broadcast_ticket_update)
            )

    def disconnect(self, websocket: WebSocket):
        """Remove connection from all tracking sets."""
        self.all_connections.discard(websocket)
        
        # Remove from ticket subscriptions
        # Efficient enough for small scale; optimize map if needed
        for ticket_id in list(self.active_connections.keys()):
            if websocket in self.active_connections[ticket_id]:
                self.active_connections[ticket_id].discard(websocket)
                if not self.active_connections[ticket_id]:
                    del self.active_connections[ticket_id]
        
        logger.info(f"🔌 WebSocket disconnected. Total: {len(self.all_connections)}")

    async def subscribe(self, websocket: WebSocket, ticket_ids: List[int]):
        """Subscribe socket to specific ticket IDs."""
        for tid in ticket_ids:
            self.active_connections[tid].add(websocket)
        logger.info(f"📝 Socket subscribed to tickets: {ticket_ids}")
        
    async def unsubscribe(self, websocket: WebSocket, ticket_ids: List[int]):
        """Unsubscribe socket from specific ticket IDs."""
        for tid in ticket_ids:
            if tid in self.active_connections:
                self.active_connections[tid].discard(websocket)
        logger.info(f"📝 Socket unsubscribed from tickets: {ticket_ids}")

    async def broadcast_ticket_update(self, data: dict):
        """
        Callback triggered by Redis Pub/Sub.
        Broadcasts update to clients subscribed to this ticket_id.
        """
        ticket_id = data.get("ticket_id")
        if not ticket_id:
            return
            
        if ticket_id in self.active_connections:
            message = {
                "type": "ticket_updated",
                "data": data["data"]
            }
            
            # Broadcast to all interested connections
            # Clone set to safe iterate in case of disconnect during send
            subscribers = list(self.active_connections[ticket_id])
            if subscribers:
                logger.info(f"📢 Broadcasting update for ticket {ticket_id} to {len(subscribers)} clients")
                for connection in subscribers:
                    try:
                        await connection.send_json(message)
                    except Exception as e:
                        logger.error(f"❌ Error sending to socket: {e}")
                        # Cleanup handled by disconnect() usually, but safe to ignore here


manager = ConnectionManager()


@router.websocket("/ws/tickets")
async def websocket_endpoint(websocket: WebSocket):
    """
    WebSocket endpoint for ticket updates.
    
    Protocol:
    - Client sends: {"action": "subscribe", "ticket_ids": [1, 2]}
    - Client sends: {"action": "ping"}
    - Server sends: {"type": "ticket_updated", "data": {...}}
    - Server sends: {"type": "pong"}
    """
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_json()
            action = data.get("action")
            
            if action == "subscribe":
                ticket_ids = data.get("ticket_ids", [])
                if isinstance(ticket_ids, list):
                    await manager.subscribe(websocket, ticket_ids)
                    # Ack subscription
                    await websocket.send_json({
                        "type": "subscribed",
                        "ticket_ids": ticket_ids
                    })
                    
            elif action == "unsubscribe":
                ticket_ids = data.get("ticket_ids", [])
                if isinstance(ticket_ids, list):
                    await manager.unsubscribe(websocket, ticket_ids)
            
            elif action == "ping":
                await websocket.send_json({"type": "pong"})
                
            else:
                await websocket.send_json({
                    "type": "error", 
                    "message": f"Unknown action: {action}"
                })
                
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"❌ WebSocket error: {e}")
        manager.disconnect(websocket)
