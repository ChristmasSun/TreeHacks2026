"""
Demeanor Analysis Service
Receives H.264 video frames from RTMS, provides a clean hook for
facial expression / engagement analysis. Tracks per-student metrics
and session-level aggregation.

The actual analysis model (FER, DeepFace, MediaPipe, LLM vision)
is pluggable via set_analyzer().
"""
import logging
import time
from collections import deque
from dataclasses import dataclass, field
from typing import Callable, Optional, Awaitable

logger = logging.getLogger(__name__)


@dataclass
class DemeanorMetrics:
    """Per-frame analysis result."""
    engagement_score: float = 0.5  # 0.0 (disengaged) to 1.0 (fully engaged)
    attention: str = "unknown"     # "focused", "distracted", "away"
    expression: str = "neutral"    # "neutral", "confused", "smiling", "bored"
    timestamp: float = 0.0


@dataclass
class StudentDemeanor:
    """Rolling metrics for a single student."""
    user_id: str = ""
    user_name: str = ""
    scores: deque = field(default_factory=lambda: deque(maxlen=30))
    latest: DemeanorMetrics = field(default_factory=DemeanorMetrics)
    frame_count: int = 0

    @property
    def avg_score(self) -> float:
        if not self.scores:
            return 0.5
        return sum(self.scores) / len(self.scores)


# Type for the pluggable analyzer function
AnalyzerFn = Callable[[str, str, bytes], Awaitable[DemeanorMetrics]]


async def _stub_analyzer(user_id: str, user_name: str, frame_data: bytes) -> DemeanorMetrics:
    """Stub analyzer — returns placeholder metrics. Replace with real model."""
    import random
    return DemeanorMetrics(
        engagement_score=round(random.uniform(0.4, 0.95), 2),
        attention=random.choice(["focused", "focused", "focused", "distracted"]),
        expression=random.choice(["neutral", "neutral", "smiling", "confused"]),
        timestamp=time.time(),
    )


class DemeanorService:
    """
    Manages per-student engagement metrics from RTMS video frames.

    Usage:
        service = DemeanorService()
        # Optionally plug in a real analyzer:
        # service.set_analyzer(my_face_analysis_fn)
        metrics = await service.analyze_frame(user_id, user_name, frame_bytes)
    """

    def __init__(self):
        self._students: dict[str, StudentDemeanor] = {}
        self._analyzer: AnalyzerFn = _stub_analyzer
        self._session_start: float = time.time()

    def set_analyzer(self, fn: AnalyzerFn):
        """Plug in a real analysis function. Signature: async (user_id, user_name, h264_bytes) -> DemeanorMetrics"""
        self._analyzer = fn
        logger.info("Demeanor analyzer updated")

    async def analyze_frame(self, user_id: str, user_name: str, frame_data: bytes) -> DemeanorMetrics:
        """Analyze a single video frame and update student metrics."""
        # Get or create student record
        if user_id not in self._students:
            self._students[user_id] = StudentDemeanor(user_id=user_id, user_name=user_name)

        student = self._students[user_id]
        student.frame_count += 1

        # Run analysis
        try:
            metrics = await self._analyzer(user_id, user_name, frame_data)
        except Exception as e:
            logger.warning(f"Demeanor analysis failed for {user_name}: {e}")
            metrics = DemeanorMetrics(timestamp=time.time())

        # Update rolling scores
        student.scores.append(metrics.engagement_score)
        student.latest = metrics

        return metrics

    def get_student_metrics(self, user_id: str) -> Optional[dict]:
        """Get current metrics for a student."""
        student = self._students.get(user_id)
        if not student:
            return None
        return {
            "user_id": student.user_id,
            "user_name": student.user_name,
            "engagement_score": round(student.avg_score, 2),
            "attention": student.latest.attention,
            "expression": student.latest.expression,
            "frame_count": student.frame_count,
            "timestamp": student.latest.timestamp,
        }

    def get_all_metrics(self) -> dict:
        """Get metrics for all tracked students."""
        return {
            uid: self.get_student_metrics(uid)
            for uid in self._students
        }

    def get_session_summary(self) -> dict:
        """Get session-level aggregated analytics."""
        students = list(self._students.values())
        if not students:
            return {
                "total_students": 0,
                "avg_engagement": 0,
                "session_duration_s": round(time.time() - self._session_start),
            }

        avg_engagement = sum(s.avg_score for s in students) / len(students)

        attention_counts = {"focused": 0, "distracted": 0, "away": 0, "unknown": 0}
        for s in students:
            att = s.latest.attention
            if att in attention_counts:
                attention_counts[att] += 1

        return {
            "total_students": len(students),
            "avg_engagement": round(avg_engagement, 2),
            "attention_distribution": attention_counts,
            "total_frames_analyzed": sum(s.frame_count for s in students),
            "session_duration_s": round(time.time() - self._session_start),
            "per_student": [
                {
                    "user_name": s.user_name,
                    "engagement": round(s.avg_score, 2),
                    "attention": s.latest.attention,
                    "expression": s.latest.expression,
                }
                for s in students
            ],
        }

    def reset(self):
        """Clear all tracked data."""
        self._students.clear()
        self._session_start = time.time()
