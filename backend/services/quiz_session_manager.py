"""
Quiz Session Manager
Tracks quiz state per student, handles scoring, and coordinates video playback.
"""
import logging
from typing import Optional, Callable, Awaitable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

from .quiz_generator import Quiz, QuizQuestion, generate_follow_up_question
from .zoom_chatbot_service import (
    send_quiz_question,
    send_correct_feedback,
    send_incorrect_feedback,
    send_quiz_complete,
    send_text_message,
)

logger = logging.getLogger(__name__)


class SessionStatus(str, Enum):
    """Quiz session status"""
    WAITING_START = "waiting_start"
    IN_PROGRESS = "in_progress"
    WATCHING_VIDEO = "watching_video"
    AWAITING_FOLLOW_UP = "awaiting_follow_up"
    COMPLETED = "completed"


@dataclass
class StudentAnswer:
    """Record of a student's answer"""
    question_id: str
    answer: str
    correct: bool
    timestamp: datetime = field(default_factory=datetime.utcnow)


@dataclass
class QuizSession:
    """Active quiz session for a student"""
    student_jid: str
    account_id: str
    quiz: Quiz
    current_question_idx: int = 0
    answers: list[StudentAnswer] = field(default_factory=list)
    wrong_concepts: list[str] = field(default_factory=list)
    status: SessionStatus = SessionStatus.WAITING_START
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    pending_follow_up: Optional[QuizQuestion] = None
    # Callback to trigger video playback in Electron
    on_play_video: Optional[Callable[[str, str, str], Awaitable[None]]] = None


# Global session storage (in production, use Redis or database)
quiz_sessions: dict[str, QuizSession] = {}


def get_session(student_jid: str) -> Optional[QuizSession]:
    """Get quiz session for a student."""
    return quiz_sessions.get(student_jid)


def create_session(
    student_jid: str,
    account_id: str,
    quiz: Quiz,
    on_play_video: Optional[Callable[[str, str, str], Awaitable[None]]] = None
) -> QuizSession:
    """Create a new quiz session for a student."""
    session = QuizSession(
        student_jid=student_jid,
        account_id=account_id,
        quiz=quiz,
        on_play_video=on_play_video
    )
    quiz_sessions[student_jid] = session
    logger.info(f"Created quiz session for {student_jid}: {quiz.id}")
    return session


def delete_session(student_jid: str):
    """Delete a quiz session."""
    if student_jid in quiz_sessions:
        del quiz_sessions[student_jid]
        logger.info(f"Deleted quiz session for {student_jid}")


async def start_quiz(student_jid: str) -> bool:
    """
    Start the quiz by sending the first question.

    Returns:
        True if quiz started successfully
    """
    session = get_session(student_jid)
    if not session:
        logger.error(f"No session found for {student_jid}")
        return False

    if session.status != SessionStatus.WAITING_START:
        logger.warning(f"Cannot start quiz - status is {session.status}")
        return False

    session.status = SessionStatus.IN_PROGRESS
    session.started_at = datetime.utcnow()
    session.current_question_idx = 0

    await send_current_question(session)
    return True


async def send_current_question(session: QuizSession):
    """Send the current question to the student."""
    if session.current_question_idx >= len(session.quiz.questions):
        await complete_quiz(session)
        return

    question = session.quiz.questions[session.current_question_idx]

    await send_quiz_question(
        to_jid=session.student_jid,
        account_id=session.account_id,
        question=question,
        question_number=session.current_question_idx + 1,
        total_questions=len(session.quiz.questions)
    )

    logger.info(
        f"Sent question {session.current_question_idx + 1}/{len(session.quiz.questions)} "
        f"to {session.student_jid}"
    )


async def handle_answer(
    student_jid: str,
    question_id: str,
    answer: str
) -> dict:
    """
    Handle a student's answer to a quiz question.

    Args:
        student_jid: Student's JID
        question_id: Question ID from button value
        answer: Answer letter (A, B, C, or D)

    Returns:
        Result dict with {correct, explanation, video_path?, next_action}
    """
    session = get_session(student_jid)
    if not session:
        return {"error": "No active quiz session"}

    # Handle follow-up question answer
    if session.status == SessionStatus.AWAITING_FOLLOW_UP and session.pending_follow_up:
        return await handle_follow_up_answer(session, answer)

    if session.status != SessionStatus.IN_PROGRESS:
        return {"error": f"Quiz not in progress (status: {session.status})"}

    if session.current_question_idx >= len(session.quiz.questions):
        return {"error": "Quiz already completed"}

    question = session.quiz.questions[session.current_question_idx]

    # Verify question ID matches
    if question.id != question_id:
        logger.warning(f"Question ID mismatch: expected {question.id}, got {question_id}")
        # Continue anyway - user might be answering current question

    # Check answer
    is_correct = answer.upper() == question.correct_answer.upper()

    # Record answer
    session.answers.append(StudentAnswer(
        question_id=question.id,
        answer=answer,
        correct=is_correct
    ))

    result = {
        "correct": is_correct,
        "correct_answer": question.correct_answer,
        "explanation": question.explanation,
        "concept": question.concept
    }

    if is_correct:
        # Correct answer - send feedback and move to next question
        await send_correct_feedback(
            to_jid=session.student_jid,
            account_id=session.account_id,
            explanation=question.explanation
        )

        session.current_question_idx += 1

        if session.current_question_idx >= len(session.quiz.questions):
            await complete_quiz(session)
            result["next_action"] = "quiz_complete"
        else:
            await send_current_question(session)
            result["next_action"] = "next_question"

    else:
        # Wrong answer - record concept, send feedback, trigger video
        session.wrong_concepts.append(question.concept)

        will_play_video = question.video_path is not None and session.on_play_video is not None

        await send_incorrect_feedback(
            to_jid=session.student_jid,
            account_id=session.account_id,
            correct_answer=question.correct_answer,
            explanation=question.explanation,
            will_play_video=will_play_video
        )

        if will_play_video:
            # Trigger video playback
            session.status = SessionStatus.WATCHING_VIDEO

            # Store the question for follow-up generation
            session.pending_follow_up = question

            # Call the video playback callback
            await session.on_play_video(
                session.student_jid,
                question.concept,
                question.video_path
            )

            result["next_action"] = "watch_video"
            result["video_path"] = question.video_path
        else:
            # No video - just move to next question
            session.current_question_idx += 1

            if session.current_question_idx >= len(session.quiz.questions):
                await complete_quiz(session)
                result["next_action"] = "quiz_complete"
            else:
                await send_current_question(session)
                result["next_action"] = "next_question"

    return result


async def handle_video_completed(student_jid: str) -> dict:
    """
    Handle notification that student finished watching video.
    Generates and sends a follow-up question.

    Args:
        student_jid: Student's JID

    Returns:
        Result dict
    """
    session = get_session(student_jid)
    if not session:
        return {"error": "No active quiz session"}

    if session.status != SessionStatus.WATCHING_VIDEO:
        return {"error": f"Not watching video (status: {session.status})"}

    original_question = session.pending_follow_up
    if not original_question:
        # No pending follow-up, just continue to next question
        session.status = SessionStatus.IN_PROGRESS
        session.current_question_idx += 1

        if session.current_question_idx >= len(session.quiz.questions):
            await complete_quiz(session)
            return {"next_action": "quiz_complete"}
        else:
            await send_current_question(session)
            return {"next_action": "next_question"}

    # Generate follow-up question
    try:
        await send_text_message(
            to_jid=session.student_jid,
            account_id=session.account_id,
            text="Great, you watched the video! Let me check if you got it now..."
        )

        follow_up = await generate_follow_up_question(
            concept=original_question.concept,
            description=original_question.explanation,
            previous_question=original_question.question_text,
            video_path=original_question.video_path
        )

        session.pending_follow_up = follow_up
        session.status = SessionStatus.AWAITING_FOLLOW_UP

        # Send follow-up question
        await send_quiz_question(
            to_jid=session.student_jid,
            account_id=session.account_id,
            question=follow_up,
            question_number=session.current_question_idx + 1,
            total_questions=len(session.quiz.questions)
        )

        return {"next_action": "follow_up_question"}

    except Exception as e:
        logger.error(f"Failed to generate follow-up question: {e}")

        # Skip follow-up, continue to next question
        session.status = SessionStatus.IN_PROGRESS
        session.pending_follow_up = None
        session.current_question_idx += 1

        if session.current_question_idx >= len(session.quiz.questions):
            await complete_quiz(session)
            return {"next_action": "quiz_complete"}
        else:
            await send_current_question(session)
            return {"next_action": "next_question"}


async def handle_follow_up_answer(session: QuizSession, answer: str) -> dict:
    """Handle answer to a follow-up question."""
    follow_up = session.pending_follow_up
    if not follow_up:
        return {"error": "No pending follow-up question"}

    is_correct = answer.upper() == follow_up.correct_answer.upper()

    result = {
        "correct": is_correct,
        "correct_answer": follow_up.correct_answer,
        "explanation": follow_up.explanation,
        "is_follow_up": True
    }

    if is_correct:
        await send_correct_feedback(
            to_jid=session.student_jid,
            account_id=session.account_id,
            explanation="You got it now! Let's continue."
        )
    else:
        await send_incorrect_feedback(
            to_jid=session.student_jid,
            account_id=session.account_id,
            correct_answer=follow_up.correct_answer,
            explanation=follow_up.explanation,
            will_play_video=False
        )

    # Clear follow-up and continue to next question
    session.pending_follow_up = None
    session.status = SessionStatus.IN_PROGRESS
    session.current_question_idx += 1

    if session.current_question_idx >= len(session.quiz.questions):
        await complete_quiz(session)
        result["next_action"] = "quiz_complete"
    else:
        await send_current_question(session)
        result["next_action"] = "next_question"

    return result


async def complete_quiz(session: QuizSession):
    """Mark quiz as complete and send summary."""
    session.status = SessionStatus.COMPLETED
    session.completed_at = datetime.utcnow()

    # Calculate score
    correct_count = sum(1 for a in session.answers if a.correct)
    total = len(session.quiz.questions)

    await send_quiz_complete(
        to_jid=session.student_jid,
        account_id=session.account_id,
        score=correct_count,
        total=total,
        wrong_concepts=list(set(session.wrong_concepts))  # Unique concepts
    )

    logger.info(
        f"Quiz completed for {session.student_jid}: "
        f"{correct_count}/{total} correct"
    )


async def cancel_quiz(student_jid: str) -> bool:
    """Cancel an active quiz session."""
    session = get_session(student_jid)
    if not session:
        return False

    await send_text_message(
        to_jid=session.student_jid,
        account_id=session.account_id,
        text="Quiz cancelled. Type /quiz to start a new one!"
    )

    delete_session(student_jid)
    return True


def get_session_stats(student_jid: str) -> Optional[dict]:
    """Get statistics for a quiz session."""
    session = get_session(student_jid)
    if not session:
        return None

    correct_count = sum(1 for a in session.answers if a.correct)

    return {
        "quiz_id": session.quiz.id,
        "topic": session.quiz.topic,
        "status": session.status.value,
        "current_question": session.current_question_idx + 1,
        "total_questions": len(session.quiz.questions),
        "correct_answers": correct_count,
        "wrong_concepts": session.wrong_concepts,
        "started_at": session.started_at.isoformat() if session.started_at else None,
        "completed_at": session.completed_at.isoformat() if session.completed_at else None
    }
