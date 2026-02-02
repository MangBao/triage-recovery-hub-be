import asyncio
import json
import logging

try:
    import websockets
except ImportError:
    print("❌ websockets library not installed inside container. Please add 'websockets' to requirements.txt")
    exit(1)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ws_test")

async def test():
    uri = "ws://localhost:8000/ws/tickets"
    logger.info(f"Connecting to {uri}...")
    
    try:
        async with websockets.connect(uri) as websocket:
            logger.info("✅ Connected!")
            
            # Subscribe to ticket 17
            msg = {"action": "subscribe", "ticket_ids": [17]}
            await websocket.send(json.dumps(msg))
            logger.info(f"➡️ Sent: {msg}")
            
            response = await websocket.recv()
            logger.info(f"⬅️ Received: {response}")
            
            # Ping
            await websocket.send(json.dumps({"action": "ping"}))
            response = await websocket.recv()
            logger.info(f"⬅️ Received(ping): {response}")

            print("\nListening for 20 seconds. Please trigger an update using API within 20s...")
            try:
                msg = await asyncio.wait_for(websocket.recv(), timeout=20)
                logger.info(f"🔥 EVENT RECEIVED: {msg}")
            except asyncio.TimeoutError:
                logger.warning("⏰ Timeout waiting for event")
                
    except Exception as e:
        logger.error(f"❌ Connection error: {e}")

if __name__ == "__main__":
    asyncio.run(test())
