"""In-memory face tracking and class-wide emotion aggregation."""

import math
import time
from dataclasses import dataclass, field


@dataclass
class TrackedFace:
    face_id: str
    cx: float
    cy: float
    region: dict
    current_emotion: str = "neutral"
    emotion_scores: dict = field(default_factory=dict)
    confidence: float = 0.0
    last_seen: float = field(default_factory=time.time)
    history: list = field(default_factory=list)

    def update(self, emotion: str, scores: dict, region: dict, confidence: float):
        self.current_emotion = emotion
        self.emotion_scores = scores
        self.region = region
        self.confidence = confidence
        self.cx = region.get("x", 0) + region.get("w", 0) / 2
        self.cy = region.get("y", 0) + region.get("h", 0) / 2
        self.last_seen = time.time()
        self.history.append(
            {"emotion": emotion, "scores": scores, "timestamp": self.last_seen}
        )
        if len(self.history) > 100:
            self.history = self.history[-100:]

    def to_dict(self) -> dict:
        return {
            "face_id": self.face_id,
            "current_emotion": self.current_emotion,
            "emotion_scores": self.emotion_scores,
            "region": self.region,
            "confidence": self.confidence,
            "last_seen": self.last_seen,
        }


class EmotionStateManager:
    PROXIMITY_THRESHOLD = 50  # pixels

    def __init__(self):
        self.tracked_faces: list[TrackedFace] = []
        self._next_id = 1

    def _find_nearest(self, cx: float, cy: float) -> TrackedFace | None:
        best = None
        best_dist = float("inf")
        for face in self.tracked_faces:
            dist = math.hypot(face.cx - cx, face.cy - cy)
            if dist < best_dist:
                best_dist = dist
                best = face
        if best and best_dist <= self.PROXIMITY_THRESHOLD:
            return best
        return None

    def update_from_frame(self, faces: list[dict]):
        """Match detected faces to tracked faces by position, update emotions."""
        matched_ids: set[str] = set()

        for f in faces:
            region = f.get("region", {})
            cx = region.get("x", 0) + region.get("w", 0) / 2
            cy = region.get("y", 0) + region.get("h", 0) / 2

            tracked = self._find_nearest(cx, cy)
            if tracked and tracked.face_id not in matched_ids:
                tracked.update(
                    f.get("dominant_emotion", "neutral"),
                    f.get("emotion", {}),
                    region,
                    f.get("confidence", 0),
                )
                matched_ids.add(tracked.face_id)
            else:
                new_face = TrackedFace(
                    face_id=f"Face {self._next_id}",
                    cx=cx,
                    cy=cy,
                    region=region,
                    current_emotion=f.get("dominant_emotion", "neutral"),
                    emotion_scores=f.get("emotion", {}),
                    confidence=f.get("confidence", 0),
                )
                self._next_id += 1
                self.tracked_faces.append(new_face)
                matched_ids.add(new_face.face_id)

        # Prune faces not seen for >30 seconds
        now = time.time()
        self.tracked_faces = [
            face
            for face in self.tracked_faces
            if now - face.last_seen < 30 or face.face_id in matched_ids
        ]

    def get_all_faces(self) -> list[dict]:
        return [f.to_dict() for f in self.tracked_faces]

    def get_class_summary(self) -> dict:
        if not self.tracked_faces:
            return {
                "total_faces": 0,
                "emotion_distribution": {},
                "dominant_class_emotion": "neutral",
                "engagement_score": 0,
            }

        all_emotions = [
            "angry",
            "disgust",
            "fear",
            "happy",
            "sad",
            "surprise",
            "neutral",
        ]
        totals = {e: 0.0 for e in all_emotions}

        for face in self.tracked_faces:
            for e in all_emotions:
                totals[e] += face.emotion_scores.get(e, 0)

        n = len(self.tracked_faces)
        distribution = {e: round(totals[e] / n, 2) for e in all_emotions}
        dominant = max(distribution, key=distribution.get)

        engaged = distribution.get("happy", 0) + distribution.get("surprise", 0)
        disengaged = (
            distribution.get("sad", 0)
            + distribution.get("angry", 0)
            + distribution.get("fear", 0)
        )
        total = engaged + disengaged
        engagement = round(engaged / total * 100, 1) if total > 0 else 50.0

        return {
            "total_faces": n,
            "emotion_distribution": distribution,
            "dominant_class_emotion": dominant,
            "engagement_score": engagement,
        }
