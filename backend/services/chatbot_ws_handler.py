"""
Chatbot WebSocket Handler
Processes Zoom chatbot webhook events received via WebSocket from Render.
"""
import os
import json
import logging
from typing import Optional

from .render_ws_client import register_handler, send_to_render
from .zoom_chatbot_service import (
    generate_url_validation_response,
    parse_answer_value,
    send_text_message,
    send_quiz_intro,
)
from .quiz_session_manager import (
    get_session,
    create_session,
    start_quiz,
    handle_answer,
    video_finished,
)
from .quiz_generator import load_quiz_from_json

logger = logging.getLogger(__name__)

# Path to quiz data
QUIZ_DATA_DIR = os.getenv("QUIZ_DATA_DIR", "outputs/think-fast-talk-smart")


async def handle_chatbot_webhook(event: dict):
    """
    Handle a chatbot webhook event received via WebSocket.

    Args:
        event: The WebSocket message with type='chatbot_webhook'
    """
    data = event.get("data", {})
    event_type = data.get("event")
    payload = data.get("payload", {})

    logger.info(f"Processing chatbot webhook: {event_type}")

    # Handle URL validation (Zoom sends this to verify the endpoint)
    if event_type == "endpoint.url_validation":
        plain_token = payload.get("plainToken")
        if plain_token:
            response = generate_url_validation_response(plain_token)
            logger.info(f"URL validation response: {response}")
            # Note: For URL validation, Zoom expects a direct HTTP response
            # This is handled by Render before it broadcasts to WebSocket
            return

    # Handle bot_notification events (slash commands)
    if event_type == "bot_notification":
        await handle_bot_notification(payload)
        return

    # Handle interactive_message_actions events (button clicks)
    if event_type == "interactive_message_actions":
        await handle_bot_notification(payload)  # Same handler works for both
        return

    logger.warning(f"Unhandled chatbot event type: {event_type}")


async def handle_bot_notification(payload: dict):
    """
    Handle a bot_notification event (slash commands and interactive responses).

    Args:
        payload: The event payload from Zoom
    """
    import json
    logger.info(f"Full payload: {json.dumps(payload, indent=2)}")

    account_id = payload.get("accountId", "")
    channel_name = payload.get("channelName", "")
    cmd = payload.get("cmd", "").lower()
    robot_jid = payload.get("robotJid", "")
    to_jid = payload.get("toJid", "")  # The conversation/channel JID
    user_id = payload.get("userId", "")
    user_jid = payload.get("userJid", "")  # The user's JID
    user_name = payload.get("userName", "")
    action_item = payload.get("actionItem", {})

    # For DMs, use toJid; it's the 1-on-1 chat channel
    # userJid is the user themselves (needed for API calls)
    student_jid = to_jid

    logger.info(f"Bot notification: toJid={to_jid}, userJid={user_jid}, cmd={cmd}")

    # Handle slash commands
    if cmd == "/makequiz":
        await handle_makequiz_command(student_jid, account_id, user_name, user_jid)
        return

    # Handle interactive button clicks
    if action_item:
        action_value = action_item.get("value", "")
        await handle_button_click(student_jid, account_id, action_value, user_jid)
        return

    # Unknown command
    if cmd:
        await send_text_message(
            to_jid=student_jid,
            account_id=account_id,
            text=f"Unknown command: {cmd}\n\nAvailable commands:\n/makequiz - Start a quiz"
        )


async def handle_makequiz_command(student_jid: str, account_id: str, user_name: str, user_jid: str):
    """
    Handle the /makequiz slash command.
    Loads quiz data and sends the intro message.
    """
    logger.info(f"Starting quiz for {user_name} ({student_jid}), user_jid={user_jid}")

    # First, try a simple text message to test API
    try:
        await send_text_message(
            to_jid=student_jid,
            account_id=account_id,
            text=f"Hello {user_name}! Loading quiz...",
            user_jid=user_jid
        )
        logger.info("Simple text message sent successfully!")
    except Exception as e:
        logger.error(f"Failed to send simple text: {e}")
        return

    # Check if user already has an active session
    existing_session = get_session(student_jid)
    if existing_session and existing_session.status.value != "completed":
        await send_text_message(
            to_jid=student_jid,
            account_id=account_id,
            text="You already have an active quiz! Please complete it first.",
            user_jid=user_jid
        )
        return

    # Try to load quiz data
    quiz_file = os.path.join(QUIZ_DATA_DIR, "quiz_questions.json")

    try:
        quiz = load_quiz_from_json(quiz_file)
    except FileNotFoundError:
        logger.error(f"Quiz file not found: {quiz_file}")
        await send_text_message(
            to_jid=student_jid,
            account_id=account_id,
            text="No quiz available at the moment. Please try again later.",
            user_jid=user_jid
        )
        return
    except Exception as e:
        logger.error(f"Error loading quiz: {e}")
        await send_text_message(
            to_jid=student_jid,
            account_id=account_id,
            text=f"Error loading quiz: {e}",
            user_jid=user_jid
        )
        return

    # Create quiz session
    create_session(
        student_jid=student_jid,
        account_id=account_id,
        quiz=quiz,
        user_jid=user_jid,
        on_play_video=trigger_video_playback
    )

    # Send quiz intro
    await send_quiz_intro(
        to_jid=student_jid,
        account_id=account_id,
        topic=quiz.topic,
        num_questions=len(quiz.questions),
        user_jid=user_jid
    )

    logger.info(f"Sent quiz intro to {student_jid}: {len(quiz.questions)} questions")


async def handle_button_click(student_jid: str, account_id: str, action_value: str, user_jid: str):
    """
    Handle interactive button clicks (start quiz, answers, etc).
    """
    logger.info(f"Button click from {student_jid}: {action_value}")

    if action_value == "start_quiz":
        success = await start_quiz(student_jid)
        if not success:
            await send_text_message(
                to_jid=student_jid,
                account_id=account_id,
                text="Failed to start quiz. Please try /makequiz again.",
                user_jid=user_jid
            )
        return

    if action_value == "cancel_quiz":
        from .quiz_session_manager import delete_session
        delete_session(student_jid)
        await send_text_message(
            to_jid=student_jid,
            account_id=account_id,
            text="Quiz cancelled. Type /makequiz to start a new one.",
            user_jid=user_jid
        )
        return

    if action_value == "continue_quiz" or action_value == "video_done":
        # After watching video, continue to next question
        await video_finished(student_jid)
        return

    # Check if it's an answer button
    answer_letter, question_id = parse_answer_value(action_value)
    if answer_letter and question_id:
        result = await handle_answer(student_jid, question_id, answer_letter)
        logger.info(f"Answer result: {result}")
        return

    logger.warning(f"Unknown action value: {action_value}")


async def trigger_video_playback(student_jid: str, concept: str, video_path: str):
    """
    Callback to trigger video playback in the Electron app via WebSocket.

    This sends a message to Render, which broadcasts to all connected clients
    including the Electron dashboard.
    """
    logger.info(f"Triggering video playback for {student_jid}: {concept}")

    await send_to_render({
        "type": "play_video",
        "data": {
            "student_jid": student_jid,
            "concept": concept,
            "video_path": video_path
        }
    })


def setup_chatbot_handlers():
    """Register chatbot webhook handler with the WebSocket client."""
    register_handler("chatbot_webhook", handle_chatbot_webhook)
    logger.info("Chatbot WebSocket handlers registered")
