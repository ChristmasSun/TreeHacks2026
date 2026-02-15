"""
LLM Service for AI Tutoring
Uses Cerebras gpt-oss-120b with live RTMS transcript context
"""
import os
import logging
from typing import Optional
import httpx

logger = logging.getLogger(__name__)

# RTMS service URL for fetching live transcripts
RTMS_SERVICE_URL = os.getenv("RTMS_SERVICE_URL", "https://rtms-webhook.onrender.com")

# Store lecture context globally (in production, use database)
lecture_context: dict = {
    "topic": "",
    "key_points": "",
    "additional_notes": ""
}

# Store active meeting ID for context
active_meeting_id: Optional[str] = None


def set_lecture_context(topic: str, key_points: str, notes: str = ""):
    """Set the lecture context for tutoring sessions"""
    global lecture_context
    lecture_context = {
        "topic": topic,
        "key_points": key_points,
        "additional_notes": notes
    }
    logger.info(f"Lecture context updated: {topic}")


def get_lecture_context() -> dict:
    """Get current lecture context"""
    return lecture_context


def set_active_meeting(meeting_id: str):
    """Set the active meeting ID for transcript context"""
    global active_meeting_id
    active_meeting_id = meeting_id
    logger.info(f"Active meeting set: {meeting_id}")


def get_active_meeting() -> Optional[str]:
    """Get the active meeting ID"""
    return active_meeting_id


async def fetch_rtms_transcripts(meeting_id: Optional[str] = None) -> str:
    """
    Fetch live transcripts from RTMS service on Render

    Args:
        meeting_id: Specific meeting ID, or None to get most recent

    Returns:
        Formatted transcript context string
    """
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            # If no meeting_id, try to find one with transcripts
            if not meeting_id:
                # Check for active meetings
                meetings_response = await client.get(f"{RTMS_SERVICE_URL}/api/transcripts")
                if meetings_response.status_code == 200:
                    meetings_data = meetings_response.json()
                    meetings = meetings_data.get("meetings", [])
                    if meetings:
                        # Use the meeting with most recent transcripts
                        meeting_id = meetings[0].get("meetingId")

            if not meeting_id:
                return ""

            # Fetch transcripts for this meeting
            response = await client.get(f"{RTMS_SERVICE_URL}/api/transcripts/{meeting_id}")
            if response.status_code == 200:
                data = response.json()
                full_context = data.get("fullContext", "")
                count = data.get("count", 0)

                if full_context:
                    logger.info(f"Fetched {count} transcript entries for meeting {meeting_id}")
                    return full_context

            return ""
    except Exception as e:
        logger.warning(f"Failed to fetch RTMS transcripts: {e}")
        return ""


async def generate_tutoring_response(
    student_message: str,
    student_name: str,
    conversation_history: Optional[list] = None,
    meeting_id: Optional[str] = None,
    was_interrupted: bool = False
) -> str:
    """
    Generate a tutoring response using LLM with live meeting context

    Args:
        student_message: The student's question
        student_name: Name of the student
        conversation_history: Previous messages in the conversation
        meeting_id: Optional meeting ID for transcript context
        was_interrupted: Whether the student interrupted the avatar

    Returns:
        AI tutor response
    """
    # Fetch live transcript context from RTMS
    transcript_context = await fetch_rtms_transcripts(meeting_id or active_meeting_id)
    if transcript_context:
        logger.info(f"Using live transcript context ({len(transcript_context)} chars)")

    cerebras_key = os.getenv("CEREBRAS_API_KEY")

    if cerebras_key:
        try:
            response = await call_cerebras(
                student_message, student_name, conversation_history, transcript_context, was_interrupted
            )
            return response
        except Exception as e:
            logger.error(f"Cerebras error: {e}")

    # Fallback response if no LLM available
    logger.warning("No LLM API key available - using fallback response")
    return generate_fallback_response(student_message, student_name)


def build_system_prompt(student_name: str, transcript_context: str = "", was_interrupted: bool = False) -> str:
    """Build the system prompt with lecture and transcript context"""

    transcript_section = ""
    if transcript_context:
        # Only use last 2000 chars for speed
        transcript_section = f"""
LECTURE CONTEXT:
{transcript_context[-2000:]}
"""

    interrupt_note = "The student interrupted - briefly acknowledge and answer their new question." if was_interrupted else ""

    return f"""You are a friendly AI tutor helping {student_name} understand their lecture material.

{transcript_section}
RULES:
- 2-3 sentences MAX (spoken aloud)
- Reference the lecture when relevant
- Be warm and conversational
{interrupt_note}"""


async def call_cerebras(
    student_message: str,
    student_name: str,
    conversation_history: Optional[list] = None,
    transcript_context: str = "",
    was_interrupted: bool = False
) -> str:
    """Call Cerebras API for fast response"""
    api_key = os.getenv("CEREBRAS_API_KEY")

    system_prompt = build_system_prompt(student_name, transcript_context, was_interrupted)

    messages = [{"role": "system", "content": system_prompt}]

    # Add conversation history if provided
    if conversation_history:
        for msg in conversation_history[-6:]:  # Last 6 messages
            messages.append({
                "role": "user" if msg.get("role") == "student" else "assistant",
                "content": msg.get("text", "")
            })

    messages.append({"role": "user", "content": student_message})

    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.post(
            "https://api.cerebras.ai/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            },
            json={
                "model": "gpt-oss-120b",
                "messages": messages,
                "max_tokens": 100,  # Shorter for speed
                "temperature": 0.7
            }
        )
        response.raise_for_status()
        data = response.json()
        return data["choices"][0]["message"]["content"]


def generate_fallback_response(student_message: str, student_name: str) -> str:
    """Generate a simple response when LLM is unavailable"""
    message_lower = student_message.lower()
    
    # Basic pattern matching for common questions
    if any(word in message_lower for word in ["what", "explain", "how"]):
        return f"Great question, {student_name}! That's an important concept. Let me break it down for you in simpler terms."
    
    if any(word in message_lower for word in ["why", "reason"]):
        return f"Good thinking, {student_name}! Understanding the 'why' is crucial. The key reason is related to the fundamental principles we discussed."
    
    if any(word in message_lower for word in ["example", "show"]):
        return f"Sure, {student_name}! Examples help a lot. Think of it like this - it's similar to something you might encounter in everyday life."
    
    if any(word in message_lower for word in ["confused", "don't understand", "lost"]):
        return f"No worries, {student_name}! It's okay to feel confused - this is complex material. Let's take it step by step. What specific part is tripping you up?"
    
    if any(word in message_lower for word in ["thank", "thanks"]):
        return f"You're welcome, {student_name}! Keep asking questions - that's how we learn. What else would you like to explore?"
    
    # Default response
    return f"That's a thoughtful point, {student_name}. Let me address that and help clarify the concept for you."
