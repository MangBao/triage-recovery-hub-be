"""WebSocket endpoint for real-time ticket updates."""

import logging
import asyncio
import json
from collections import defaultdict
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from typing import List, Dict, Set

from app.pubsub import subscribe_ticket_updates_async
from fastapi.concurrency import run_in_threadpool

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

    async def disconnect(self, websocket: WebSocket):
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
        
        # Cleanup Redis task if no connections left
        if not self.all_connections and self.redis_task:
            logger.info("🛑 No active connections. Stopping Redis Subscriber Task...")
            self.redis_task.cancel()
            try:
                await self.redis_task
            except asyncio.CancelledError:
                logger.info("✅ Redis Subscriber Task cancelled successfully")
            self.redis_task = None

    async def shutdown(self):
        """Cleanup resources on application shutdown."""
        if self.redis_task:
            logger.info("🛑 Application Shutdown: Stopping Redis Subscriber Task...")
            self.redis_task.cancel()
            try:
                await self.redis_task
            except asyncio.CancelledError:
                pass
            self.redis_task = None
            
        # Optional: Close all websockets if they are still open (though FastAPI usually handles this)
        # for ws in list(self.all_connections):
        #     await ws.close()

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
            try:
                data = await websocket.receive_json()
            except json.JSONDecodeError:
                await websocket.send_json({
                    "type": "error",
                    "message": "Invalid JSON format"
                })
                continue
            except WebSocketDisconnect:
                # Re-raise to be handled by outer block
                raise
                
            action = data.get("action")
            
            if action == "subscribe":
                raw_ids = data.get("ticket_ids", [])
                
                # Validate input is a list
                if not isinstance(raw_ids, list):
                    await websocket.send_json({
                        "type": "error",
                        "message": "ticket_ids must be a list of integers"
                    })
                    continue
                
                # Validate and convert all IDs to integers
                try:
                    ticket_ids = [int(x) for x in raw_ids]
                except (ValueError, TypeError):
                    await websocket.send_json({
                        "type": "error",
                        "message": "All ticket_ids must be valid integers"
                    })
                    continue

                await manager.subscribe(websocket, ticket_ids)
                # Ack subscription
                await websocket.send_json({
                    "type": "subscribed",
                    "ticket_ids": ticket_ids
                })

                # Snapshot Strategy: Send current state immediately to avoid race conditions
                # This guarantees the client has the latest state even if they missed the "Processing" broadcast
                try:
                    snapshots = await run_in_threadpool(fetch_ticket_snapshots, ticket_ids)
                    if snapshots:
                        logger.info(f"📸 Sending initial snapshots for {len(snapshots)} tickets")
                        for snapshot in snapshots:
                            await websocket.send_json({
                                "type": "ticket_updated",
                                "data": snapshot
                            })
                except Exception as e:
                    logger.error(f"⚠️ Failed to send snapshots: {e}")
                    
            elif action == "unsubscribe":
                raw_ids = data.get("ticket_ids", [])
                if isinstance(raw_ids, list):
                     # Best effort unsubscribe, safe to ignore invalid ints here usually allowing partials,
                     # but for consistency we can filter valid ones
                    ticket_ids = []
                    for x in raw_ids:
                        try:
                            ticket_ids.append(int(x))
                        except (ValueError, TypeError):
                            pass
                    await manager.unsubscribe(websocket, ticket_ids)
            
            elif action == "ping":
                await websocket.send_json({"type": "pong"})
                
            else:
                await websocket.send_json({
                    "type": "error", 
                    "message": f"Unknown action: {action}"
                })
                
    except WebSocketDisconnect:
        await manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"❌ WebSocket error: {e}")
        await manager.disconnect(websocket)


def fetch_ticket_snapshots(ticket_ids: List[int]) -> List[dict]:
    """Helper to fetch current ticket states synchronously."""
    from app.database import SessionLocal
    from models.ticket import Ticket
    from models.schemas import TicketResponse
    
    results = []
    try:
        with SessionLocal() as db:
            tickets = db.query(Ticket).filter(Ticket.id.in_(ticket_ids)).all()
            for ticket in tickets:
                # Serialize using Pydantic model
                data = json.loads(TicketResponse.model_validate(ticket).model_dump_json())
                results.append(data)
    except Exception as e:
        logger.error(f"Snapshot fetch error: {e}")
    return results
