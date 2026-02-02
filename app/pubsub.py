"""Redis Pub/Sub utilities for real-time ticket updates.

This module enables cross-process communication between:
- Huey Worker (publishes ticket updates after AI processing)
- FastAPI Backend (subscribes and forwards to WebSocket clients)

Channel: ticket:updated
"""

import json
import logging
import logging
import redis
import redis.asyncio as redis_async
from typing import Callable, Any, Awaitable

from app.config import settings

logger = logging.getLogger(__name__)

# Channel name for ticket updates
TICKET_UPDATE_CHANNEL = "ticket:updated"


def get_redis_client() -> redis.Redis:
    """Get synchronous Redis client for publishing."""
    return redis.from_url(settings.REDIS_URL, decode_responses=True)


def publish_ticket_update(ticket_id: int, ticket_data: dict) -> bool:
    """
    Publish ticket update event to Redis.
    
    Called by Huey Worker after AI processing completes.
    
    Args:
        ticket_id: The ticket ID that was updated
        ticket_data: Dictionary containing ticket fields
        
    Returns:
        True if published successfully, False otherwise
    """
    try:
        client = get_redis_client()
        
        message = json.dumps({
            "event": "ticket_updated",
            "ticket_id": ticket_id,
            "data": ticket_data
        }, default=str)  # default=str handles datetime serialization
        
        # Publish to channel
        subscribers = client.publish(TICKET_UPDATE_CHANNEL, message)
        
        logger.info(f"📡 Published ticket update: ticket_id={ticket_id}, subscribers={subscribers}")
        return True
        
    except Exception as e:
        logger.error(f"❌ Failed to publish ticket update: {e}")
        return False
    finally:
        client.close()


def get_pubsub() -> redis.client.PubSub:
    """
    Get Redis PubSub instance for subscribing.
    
    Used by FastAPI to listen for ticket updates.
    
    Returns:
        Redis PubSub instance subscribed to ticket update channel
    """
    client = get_redis_client()
    pubsub = client.pubsub()
    pubsub.subscribe(TICKET_UPDATE_CHANNEL)
    return pubsub


def subscribe_ticket_updates(callback: Callable[[dict], Any]) -> None:
    """
    Subscribe to ticket updates and call callback for each message.
    
    This is a blocking function - should be run in a background thread.
    
    Args:
        callback: Function to call with each ticket update message
    """
    pubsub = get_pubsub()
    
    logger.info(f"🔔 Subscribed to channel: {TICKET_UPDATE_CHANNEL}")
    
    try:
        for message in pubsub.listen():
            if message["type"] == "message":
                try:
                    data = json.loads(message["data"])
                    callback(data)
                except json.JSONDecodeError as e:
                    logger.error(f"❌ Invalid JSON in pubsub message: {e}")
    except Exception as e:
        logger.error(f"❌ PubSub subscription error: {e}")
    finally:
        pubsub.close()


async def subscribe_ticket_updates_async(callback: Callable[[dict], Awaitable[Any]]) -> None:
    """
    Async subscribe to ticket updates (non-blocking).
    
    Args:
        callback: Async function to call with each ticket update message
    """
    client = redis_async.from_url(settings.REDIS_URL, decode_responses=True)
    pubsub = client.pubsub()
    
    try:
        await pubsub.subscribe(TICKET_UPDATE_CHANNEL)
        logger.info(f"🔔 Async Subscribed to channel: {TICKET_UPDATE_CHANNEL}")
        
        async for message in pubsub.listen():
            if message["type"] == "message":
                try:
                    data = json.loads(message["data"])
                    await callback(data)
                except json.JSONDecodeError as e:
                    logger.error(f"❌ Invalid JSON in pubsub message: {e}")
                    
    except Exception as e:
        logger.error(f"❌ Async PubSub error: {e}")
    finally:
        await pubsub.close()
        await client.close()
