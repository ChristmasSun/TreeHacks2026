"""
WebSocket client that connects to the Render RTMS service
to receive Zoom chatbot webhook events.

Architecture:
- Render receives Zoom webhooks and broadcasts via WebSocket
- This client connects TO Render and listens for 'chatbot_webhook' events
- When received, it triggers local quiz handling logic
"""
import os
import json
import asyncio
import logging
from typing import Callable, Optional

import websockets
from websockets.exceptions import ConnectionClosed

logger = logging.getLogger(__name__)

# Event handlers registered by other modules
_event_handlers: dict[str, list[Callable]] = {}


def on_event(event_type: str):
    """Decorator to register an event handler."""
    def decorator(func: Callable):
        if event_type not in _event_handlers:
            _event_handlers[event_type] = []
        _event_handlers[event_type].append(func)
        return func
    return decorator


def register_handler(event_type: str, handler: Callable):
    """Register an event handler programmatically."""
    if event_type not in _event_handlers:
        _event_handlers[event_type] = []
    _event_handlers[event_type].append(handler)
    logger.info(f"Registered handler for '{event_type}' events")


async def _dispatch_event(event_type: str, data: dict):
    """Dispatch an event to all registered handlers."""
    handlers = _event_handlers.get(event_type, [])
    for handler in handlers:
        try:
            if asyncio.iscoroutinefunction(handler):
                await handler(data)
            else:
                handler(data)
        except Exception as e:
            logger.error(f"Error in handler for '{event_type}': {e}")


class RenderWebSocketClient:
    """
    Persistent WebSocket client that connects to Render
    and dispatches received events to registered handlers.
    """

    def __init__(self, render_url: Optional[str] = None):
        self.render_url = render_url or os.getenv(
            "RENDER_WS_URL",
            "wss://rtms-webhook.onrender.com/ws"
        )
        self._ws: Optional[websockets.WebSocketClientProtocol] = None
        self._running = False
        self._reconnect_delay = 1  # Start with 1 second delay

    async def connect(self):
        """Establish WebSocket connection to Render."""
        logger.info(f"Connecting to Render WebSocket: {self.render_url}")
        try:
            self._ws = await websockets.connect(
                self.render_url,
                ping_interval=30,
                ping_timeout=10
            )
            logger.info("Connected to Render WebSocket")
            self._reconnect_delay = 1  # Reset on successful connection

            # Send client_ready message
            await self._ws.send(json.dumps({
                "type": "client_ready",
                "client": "python_backend"
            }))

            return True
        except Exception as e:
            logger.error(f"Failed to connect to Render: {e}")
            return False

    async def listen(self):
        """Listen for messages and dispatch to handlers."""
        if not self._ws:
            return

        try:
            async for raw_message in self._ws:
                try:
                    message = json.loads(raw_message)
                    msg_type = message.get("type")

                    logger.debug(f"Received message type: {msg_type}")

                    if msg_type == "ready":
                        logger.info("Render server ready")
                    elif msg_type == "chatbot_webhook":
                        # This is a Zoom chatbot event forwarded by Render
                        logger.info("Received chatbot webhook event")
                        await _dispatch_event("chatbot_webhook", message)
                    elif msg_type == "text":
                        await _dispatch_event("text", message)
                    elif msg_type == "audio":
                        await _dispatch_event("audio", message)
                    elif msg_type == "html":
                        await _dispatch_event("html", message)
                    elif msg_type == "video_frame":
                        # Video frame for expression analysis
                        await _dispatch_event("video_frame", message)
                    elif msg_type == "error":
                        logger.error(f"Error from Render: {message.get('data')}")
                    else:
                        logger.debug(f"Unhandled message type: {msg_type}")

                except json.JSONDecodeError:
                    logger.warning(f"Invalid JSON received: {raw_message[:100]}")

        except ConnectionClosed as e:
            logger.warning(f"WebSocket connection closed: {e}")
        except Exception as e:
            logger.error(f"Error in WebSocket listener: {e}")

    async def run_forever(self):
        """Run the client with automatic reconnection."""
        self._running = True

        while self._running:
            connected = await self.connect()

            if connected:
                await self.listen()

            if self._running:
                logger.info(f"Reconnecting in {self._reconnect_delay}s...")
                await asyncio.sleep(self._reconnect_delay)
                # Exponential backoff up to 30 seconds
                self._reconnect_delay = min(self._reconnect_delay * 2, 30)

    async def send(self, message: dict):
        """Send a message to Render."""
        if self._ws and self._ws.open:
            await self._ws.send(json.dumps(message))
        else:
            logger.warning("Cannot send: WebSocket not connected")

    async def close(self):
        """Close the WebSocket connection."""
        self._running = False
        if self._ws:
            await self._ws.close()


# Global client instance
_client: Optional[RenderWebSocketClient] = None


async def start_render_client(render_url: Optional[str] = None):
    """Start the global Render WebSocket client."""
    global _client
    _client = RenderWebSocketClient(render_url)
    await _client.run_forever()


async def send_to_render(message: dict):
    """Send a message to Render via the global client."""
    if _client:
        await _client.send(message)
    else:
        logger.warning("Render client not initialized")


def get_client() -> Optional[RenderWebSocketClient]:
    """Get the global client instance."""
    return _client
