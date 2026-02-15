#!/usr/bin/env python3
"""
Run the chatbot WebSocket client that connects to Render.

This script:
1. Connects to the Render WebSocket server
2. Receives Zoom chatbot webhook events
3. Processes quiz commands locally
"""
import asyncio
import logging
import os
import sys

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

# Load environment variables from .env file
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), '.env'))

from backend.services.render_ws_client import start_render_client
from backend.services.chatbot_ws_handler import setup_chatbot_handlers
from backend.services.expression_service import init_expression_service

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s'
)

logger = logging.getLogger(__name__)


async def main():
    """Main entry point."""
    render_url = os.getenv("RENDER_WS_URL", "wss://rtms-webhook.onrender.com/ws")

    logger.info(f"Starting chatbot WebSocket client")
    logger.info(f"Connecting to: {render_url}")

    # Register chatbot handlers
    setup_chatbot_handlers()

    # Register expression analysis handlers
    init_expression_service()

    # Start the WebSocket client (runs forever with reconnection)
    await start_render_client(render_url)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Shutting down...")
