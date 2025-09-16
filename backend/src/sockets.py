"""
Socket.IO support for AlphaStack 4.1 real-time streaming.
Provides WebSocket endpoint at /v1/stream with CORS support.
"""

import socketio
from datetime import datetime
import json
import os
import logging

# Configure logging
logger = logging.getLogger(__name__)

# Create Socket.IO server with CORS
sio = socketio.AsyncServer(
    cors_allowed_origins=[
        "https://amc-frontend.onrender.com",
        "http://localhost:5173",
        "http://localhost:3000",
        "https://localhost:5173",  # HTTPS dev
        "*"  # Allow all origins for now - can be restricted later
    ],
    logger=True,
    engineio_logger=True
)

# Create ASGI app
sockets_app = socketio.ASGIApp(sio, socketio_path="/")

@sio.event
async def connect(sid, environ):
    """Handle client connection."""
    logger.info(f"AlphaStack WebSocket client connected: {sid}")

    # Send initial connection confirmation
    await sio.emit('connected', {
        'status': 'connected',
        'schema_version': '4.1',
        'ts': datetime.now().isoformat()
    }, room=sid)

@sio.event
async def disconnect(sid):
    """Handle client disconnection."""
    logger.info(f"AlphaStack WebSocket client disconnected: {sid}")

@sio.event
async def subscribe(sid, data):
    """Handle subscription to specific events."""
    try:
        event_types = data.get('events', ['candidate', 'explosive', 'telemetry'])
        logger.info(f"Client {sid} subscribed to events: {event_types}")

        # Join rooms for specific event types
        for event_type in event_types:
            await sio.enter_room(sid, f"subscribe_{event_type}")

        await sio.emit('subscribed', {
            'events': event_types,
            'ts': datetime.now().isoformat()
        }, room=sid)

    except Exception as e:
        logger.error(f"Subscription error for {sid}: {e}")
        await sio.emit('error', {
            'message': 'Subscription failed',
            'ts': datetime.now().isoformat()
        }, room=sid)

# Event emission functions for external use
async def emit_candidate_update():
    """Emit candidate update event to all connected clients."""
    try:
        await sio.emit('candidate', {
            'type': 'candidate_update',
            'ts': datetime.now().isoformat()
        })
        logger.info("Emitted candidate update event")
    except Exception as e:
        logger.error(f"Failed to emit candidate update: {e}")

async def emit_explosive_update():
    """Emit explosive update event to all connected clients."""
    try:
        await sio.emit('explosive', {
            'type': 'explosive_update',
            'ts': datetime.now().isoformat()
        })
        logger.info("Emitted explosive update event")
    except Exception as e:
        logger.error(f"Failed to emit explosive update: {e}")

async def emit_telemetry_update():
    """Emit telemetry update event to all connected clients."""
    try:
        await sio.emit('telemetry', {
            'type': 'telemetry_update',
            'ts': datetime.now().isoformat()
        })
        logger.info("Emitted telemetry update event")
    except Exception as e:
        logger.error(f"Failed to emit telemetry update: {e}")

# Redis pub/sub integration (if available)
async def setup_redis_pubsub():
    """Setup Redis pub/sub listener for real-time events."""
    try:
        import redis.asyncio as redis

        redis_url = os.getenv("REDIS_URL")
        if not redis_url:
            logger.warning("Redis URL not configured, real-time events disabled")
            return

        r = redis.from_url(redis_url)
        pubsub = r.pubsub()

        # Subscribe to AlphaStack channels
        await pubsub.subscribe('alphastack:candidate', 'alphastack:explosive', 'alphastack:telemetry')

        logger.info("Redis pub/sub setup complete for AlphaStack events")

        # Listen for messages in background
        async for message in pubsub.listen():
            if message['type'] == 'message':
                channel = message['channel'].decode('utf-8')

                if 'candidate' in channel:
                    await emit_candidate_update()
                elif 'explosive' in channel:
                    await emit_explosive_update()
                elif 'telemetry' in channel:
                    await emit_telemetry_update()

    except ImportError:
        logger.warning("Redis not available, real-time events disabled")
    except Exception as e:
        logger.error(f"Redis pub/sub setup failed: {e}")

# Manual event triggers for testing
async def trigger_test_events():
    """Trigger test events for development/testing."""
    await emit_candidate_update()
    await emit_explosive_update()
    await emit_telemetry_update()