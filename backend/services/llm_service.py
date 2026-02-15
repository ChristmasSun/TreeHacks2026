"""
LLM Service for AI Tutoring
Uses OpenAI GPT-4 or falls back to a simple response
"""
import os
import logging
from typing import Optional
import httpx

logger = logging.getLogger(__name__)

# Store lecture context globally (in production, use database)
lecture_context: dict = {
    "topic": "",
    "key_points": "",
    "additional_notes": ""
}


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


async def generate_tutoring_response(
    student_message: str,
    student_name: str,
    conversation_history: Optional[list] = None
) -> str:
    """
    Generate a tutoring response using LLM
    
    Args:
        student_message: The student's question
        student_name: Name of the student
        conversation_history: Previous messages in the conversation
    
    Returns:
        AI tutor response
    """
    api_key = os.getenv("OPENAI_API_KEY")
    
    if not api_key:
        # Fallback response if no API key
        logger.warning("No OpenAI API key - using fallback response")
        return generate_fallback_response(student_message, student_name)
    
    try:
        response = await call_openai(student_message, student_name, conversation_history)
        return response
    except Exception as e:
        logger.error(f"LLM error: {e}")
        return generate_fallback_response(student_message, student_name)


async def call_openai(
    student_message: str,
    student_name: str,
    conversation_history: Optional[list] = None
) -> str:
    """Call OpenAI API for response"""
    api_key = os.getenv("OPENAI_API_KEY")
    
    system_prompt = f"""You are a friendly, encouraging AI tutor helping a student understand course material.

LECTURE CONTEXT:
Topic: {lecture_context.get('topic', 'General tutoring')}
Key Points: {lecture_context.get('key_points', 'Help the student with their questions')}
Additional Notes: {lecture_context.get('additional_notes', '')}

GUIDELINES:
- Be warm and encouraging - address the student by name ({student_name})
- Give clear, concise explanations (2-3 sentences max for spoken responses)
- Use simple language and analogies
- If the student seems confused, break it down further
- Ask follow-up questions to check understanding
- Stay focused on the lecture topic when relevant
- If asked something off-topic, gently redirect to the material

Remember: Your response will be spoken aloud by an avatar, so keep it conversational and natural."""

    messages = [{"role": "system", "content": system_prompt}]
    
    # Add conversation history if provided
    if conversation_history:
        for msg in conversation_history[-10:]:  # Last 10 messages
            messages.append({
                "role": "user" if msg.get("role") == "student" else "assistant",
                "content": msg.get("text", "")
            })
    
    messages.append({"role": "user", "content": student_message})
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            "https://api.openai.com/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            },
            json={
                "model": "gpt-4-turbo-preview",
                "messages": messages,
                "max_tokens": 200,
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
