"""
Zoom Team Chat Chatbot Service
Sends quiz questions with interactive buttons and handles responses via webhooks.
100% REST API based - no browser automation.
"""
import os
import hmac
import hashlib
import logging
from typing import Optional
from dataclasses import dataclass
import httpx

logger = logging.getLogger(__name__)

# Zoom API endpoints
ZOOM_OAUTH_URL = "https://zoom.us/zoom-oauth/token"
ZOOM_CHATBOT_URL = "https://api.zoom.us/v2/im/chat/messages"

# Cached token
_cached_token: Optional[str] = None
_token_expires_at: float = 0


@dataclass
class QuizQuestion:
    """A single quiz question with options"""
    id: str
    concept: str  # Links to video
    question_text: str
    options: list[str]  # ["A) ...", "B) ...", "C) ...", "D) ..."]
    correct_answer: str  # "A", "B", "C", or "D"
    explanation: str
    video_path: Optional[str] = None  # Path to Manim explainer video


async def get_chatbot_token() -> str:
    """
    Get chatbot access token using client_credentials flow.
    Caches token for reuse.
    """
    global _cached_token, _token_expires_at
    import time

    # Check if we have a valid cached token
    if _cached_token and time.time() < _token_expires_at - 60:
        return _cached_token

    client_id = os.getenv("ZOOM_CHATBOT_CLIENT_ID")
    client_secret = os.getenv("ZOOM_CHATBOT_CLIENT_SECRET")

    if not client_id or not client_secret:
        raise ValueError("Missing ZOOM_CHATBOT_CLIENT_ID or ZOOM_CHATBOT_CLIENT_SECRET")

    # Create Basic auth header
    import base64
    credentials = base64.b64encode(f"{client_id}:{client_secret}".encode()).decode()

    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.post(
            ZOOM_OAUTH_URL,
            headers={
                "Authorization": f"Basic {credentials}",
                "Content-Type": "application/x-www-form-urlencoded"
            },
            data="grant_type=client_credentials"
        )
        response.raise_for_status()
        data = response.json()

        _cached_token = data["access_token"]
        _token_expires_at = time.time() + data.get("expires_in", 3600)

        logger.info("Obtained new Zoom chatbot token")
        return _cached_token


async def get_user_jid(email: str) -> Optional[str]:
    """
    Get a user's JID (Jabber ID) from their email address.
    The JID is needed to send chatbot messages to a specific user.

    Args:
        email: User's email address

    Returns:
        User's JID or None if not found
    """
    token = await get_chatbot_token()

    async with httpx.AsyncClient(timeout=10.0) as client:
        # First try to get user info
        response = await client.get(
            f"https://api.zoom.us/v2/users/{email}",
            headers={"Authorization": f"Bearer {token}"}
        )

        if response.status_code == 200:
            data = response.json()
            # The JID is typically the user's ID + @xmpp.zoom.us
            user_id = data.get("id")
            if user_id:
                jid = f"{user_id}@xmpp.zoom.us"
                logger.info(f"Got JID for {email}: {jid}")
                return jid

        # Try chat users endpoint as fallback
        response = await client.get(
            f"https://api.zoom.us/v2/chat/users/{email}",
            headers={"Authorization": f"Bearer {token}"}
        )

        if response.status_code == 200:
            data = response.json()
            jid = data.get("jid")
            if jid:
                logger.info(f"Got JID from chat API for {email}: {jid}")
                return jid

        logger.warning(f"Could not get JID for {email}")
        return None


def verify_webhook_signature(
    body: bytes,
    signature: str,
    timestamp: str
) -> bool:
    """
    Verify Zoom webhook signature.

    Args:
        body: Raw request body bytes
        signature: x-zm-signature header value
        timestamp: x-zm-request-timestamp header value

    Returns:
        True if signature is valid
    """
    secret_token = os.getenv("ZOOM_CHATBOT_VERIFICATION_TOKEN")
    if not secret_token:
        logger.error("Missing ZOOM_CHATBOT_VERIFICATION_TOKEN")
        return False

    # Construct message: v0:{timestamp}:{body}
    message = f"v0:{timestamp}:{body.decode('utf-8')}"

    # Calculate expected signature
    expected_hash = hmac.new(
        secret_token.encode(),
        message.encode(),
        hashlib.sha256
    ).hexdigest()

    expected_signature = f"v0={expected_hash}"

    return hmac.compare_digest(signature, expected_signature)


def generate_url_validation_response(plain_token: str) -> dict:
    """
    Generate response for endpoint.url_validation event.

    Args:
        plain_token: The plainToken from Zoom's validation request

    Returns:
        Response dict with plainToken and encryptedToken
    """
    secret_token = os.getenv("ZOOM_CHATBOT_VERIFICATION_TOKEN")
    if not secret_token:
        raise ValueError("Missing ZOOM_CHATBOT_VERIFICATION_TOKEN")

    encrypted_token = hmac.new(
        secret_token.encode(),
        plain_token.encode(),
        hashlib.sha256
    ).hexdigest()

    return {
        "plainToken": plain_token,
        "encryptedToken": encrypted_token
    }


async def send_chatbot_message(
    to_jid: str,
    account_id: str,
    content: dict
) -> dict:
    """
    Send a chatbot message to a user.

    Args:
        to_jid: Recipient's JID (from webhook payload)
        account_id: Account ID (from webhook payload)
        content: Message content with head/body structure

    Returns:
        API response
    """
    bot_jid = os.getenv("ZOOM_BOT_JID")
    if not bot_jid:
        raise ValueError("Missing ZOOM_BOT_JID")

    token = await get_chatbot_token()

    body = {
        "robot_jid": bot_jid,
        "to_jid": to_jid,
        "account_id": account_id,
        "content": content
    }

    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.post(
            ZOOM_CHATBOT_URL,
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json"
            },
            json=body
        )

        if not response.is_success:
            error_text = response.text
            logger.error(f"Failed to send chatbot message: {response.status_code} - {error_text}")
            response.raise_for_status()

        logger.info(f"Sent chatbot message to {to_jid}")
        return response.json()


async def send_text_message(
    to_jid: str,
    account_id: str,
    text: str
) -> dict:
    """Send a simple text message."""
    content = {
        "body": [
            {"type": "message", "text": text[:4096]}  # Zoom limit
        ]
    }
    return await send_chatbot_message(to_jid, account_id, content)


async def send_quiz_question(
    to_jid: str,
    account_id: str,
    question: QuizQuestion,
    question_number: int,
    total_questions: int
) -> dict:
    """
    Send a quiz question with A/B/C/D buttons.

    Args:
        to_jid: Recipient's JID
        account_id: Account ID
        question: The quiz question to send
        question_number: Current question number (1-indexed)
        total_questions: Total questions in quiz

    Returns:
        API response
    """
    # Build button items for each option
    button_items = []
    for i, option in enumerate(question.options[:4]):  # Max 4 options
        letter = chr(65 + i)  # A, B, C, D
        button_items.append({
            "text": f"{letter}",
            "value": f"answer_{letter}_{question.id}",
            "style": "Default"
        })

    content = {
        "head": {
            "text": f"Question {question_number}/{total_questions}",
            "sub_head": {"text": question.concept}
        },
        "body": [
            {
                "type": "message",
                "text": question.question_text
            },
            {
                "type": "fields",
                "items": [
                    {"key": chr(65 + i), "value": opt.lstrip("ABCD) ")}
                    for i, opt in enumerate(question.options[:4])
                ]
            },
            {
                "type": "actions",
                "items": button_items
            }
        ]
    }

    return await send_chatbot_message(to_jid, account_id, content)


async def send_correct_feedback(
    to_jid: str,
    account_id: str,
    explanation: str
) -> dict:
    """Send feedback for a correct answer."""
    content = {
        "body": [
            {
                "type": "section",
                "sidebar_color": "#10b981",  # Green
                "sections": [
                    {"type": "message", "text": "Correct!"}
                ]
            },
            {
                "type": "message",
                "text": explanation[:4096]
            }
        ]
    }
    return await send_chatbot_message(to_jid, account_id, content)


async def send_incorrect_feedback(
    to_jid: str,
    account_id: str,
    correct_answer: str,
    explanation: str,
    will_play_video: bool = True
) -> dict:
    """Send feedback for an incorrect answer."""
    video_note = "\n\nWatch the explainer video to learn more!" if will_play_video else ""

    content = {
        "body": [
            {
                "type": "section",
                "sidebar_color": "#ef4444",  # Red
                "sections": [
                    {"type": "message", "text": f"Not quite. The correct answer is {correct_answer}."}
                ]
            },
            {
                "type": "message",
                "text": f"{explanation}{video_note}"[:4096]
            }
        ]
    }
    return await send_chatbot_message(to_jid, account_id, content)


async def send_quiz_complete(
    to_jid: str,
    account_id: str,
    score: int,
    total: int,
    wrong_concepts: list[str]
) -> dict:
    """Send quiz completion summary."""
    percentage = (score / total * 100) if total > 0 else 0

    # Determine color based on score
    if percentage >= 80:
        color = "#10b981"  # Green
        emoji = "Excellent!"
    elif percentage >= 60:
        color = "#f59e0b"  # Orange
        emoji = "Good effort!"
    else:
        color = "#ef4444"  # Red
        emoji = "Keep practicing!"

    body_items = [
        {
            "type": "section",
            "sidebar_color": color,
            "sections": [
                {"type": "message", "text": f"{emoji} You scored {score}/{total} ({percentage:.0f}%)"}
            ]
        }
    ]

    if wrong_concepts:
        body_items.append({
            "type": "fields",
            "items": [
                {"key": "Review these topics", "value": ", ".join(wrong_concepts[:5])}
            ]
        })

    content = {
        "head": {
            "text": "Quiz Complete!"
        },
        "body": body_items
    }

    return await send_chatbot_message(to_jid, account_id, content)


async def send_quiz_intro(
    to_jid: str,
    account_id: str,
    topic: str,
    num_questions: int
) -> dict:
    """Send quiz introduction message."""
    content = {
        "head": {
            "text": f"Quiz: {topic}",
            "sub_head": {"text": f"{num_questions} questions"}
        },
        "body": [
            {
                "type": "message",
                "text": "Let's test your understanding! Click the letter buttons to answer each question. If you get one wrong, I'll show you an explainer video."
            },
            {
                "type": "actions",
                "items": [
                    {"text": "Start Quiz", "value": "start_quiz", "style": "Primary"},
                    {"text": "Cancel", "value": "cancel_quiz", "style": "Default"}
                ]
            }
        ]
    }
    return await send_chatbot_message(to_jid, account_id, content)


def parse_answer_value(action_value: str) -> tuple[Optional[str], Optional[str]]:
    """
    Parse answer button value to extract answer letter and question ID.

    Args:
        action_value: Button value like "answer_A_q1"

    Returns:
        Tuple of (answer_letter, question_id) or (None, None) if invalid
    """
    if not action_value.startswith("answer_"):
        return None, None

    parts = action_value.split("_")
    if len(parts) >= 3:
        answer_letter = parts[1]
        question_id = "_".join(parts[2:])
        return answer_letter, question_id

    return None, None
