"""
SQLAlchemy models for the breakout room system
"""
from sqlalchemy import Column, Integer, String, DateTime, Float, Text, ForeignKey, JSON
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from .database import Base


class Professor(Base):
    """Professor model with HeyGen avatar configuration"""
    __tablename__ = "professors"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String(255), nullable=False)
    email = Column(String(255), unique=True, nullable=False, index=True)
    zoom_user_id = Column(String(255))
    heygen_avatar_id = Column(String(255))
    context_documents = Column(JSON)  # Array of {file_path, embedding_id, type}
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    sessions = relationship("Session", back_populates="professor")
    documents = relationship("ContextDocument", back_populates="professor")


class Student(Base):
    """Student model"""
    __tablename__ = "students"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String(255), nullable=False)
    email = Column(String(255), unique=True, nullable=False, index=True)
    zoom_user_id = Column(String(255))
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    breakout_rooms = relationship("BreakoutRoom", back_populates="student")
    progress_records = relationship("StudentProgress", back_populates="student")


class Session(Base):
    """Breakout session model"""
    __tablename__ = "sessions"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    professor_id = Column(Integer, ForeignKey("professors.id"), nullable=False)
    meeting_id = Column(String(255), nullable=False, index=True)
    start_time = Column(DateTime(timezone=True), server_default=func.now())
    end_time = Column(DateTime(timezone=True), nullable=True)
    status = Column(String(50), nullable=False, default="scheduled")  # scheduled, active, completed, failed
    configuration = Column(JSON)  # {duration, topic, student_ids, context_files}
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    professor = relationship("Professor", back_populates="sessions")
    breakout_rooms = relationship("BreakoutRoom", back_populates="session", cascade="all, delete-orphan")
    analytics = relationship("SessionAnalytics", back_populates="session", uselist=False)


class BreakoutRoom(Base):
    """Breakout room model with avatar assignment"""
    __tablename__ = "breakout_rooms"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    session_id = Column(Integer, ForeignKey("sessions.id"), nullable=False)
    zoom_room_id = Column(String(255), nullable=False)
    avatar_session_id = Column(String(255))  # HeyGen session ID
    student_id = Column(Integer, ForeignKey("students.id"), nullable=False)
    status = Column(String(50), nullable=False, default="pending")  # pending, active, completed, error
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    session = relationship("Session", back_populates="breakout_rooms")
    student = relationship("Student", back_populates="breakout_rooms")
    transcripts = relationship("Transcript", back_populates="room", cascade="all, delete-orphan")


class Transcript(Base):
    """Transcript model for student-bot conversations"""
    __tablename__ = "transcripts"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    room_id = Column(Integer, ForeignKey("breakout_rooms.id"), nullable=False)
    speaker = Column(String(20), nullable=False)  # student or bot
    text = Column(Text, nullable=False)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())
    confidence = Column(Float)  # Transcription confidence score
    metadata = Column(JSON)  # {keywords, sentiment, intent}

    # Relationships
    room = relationship("BreakoutRoom", back_populates="transcripts")


class StudentProgress(Base):
    """Student progress tracking per session"""
    __tablename__ = "student_progress"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    student_id = Column(Integer, ForeignKey("students.id"), nullable=False)
    session_id = Column(Integer, ForeignKey("sessions.id"), nullable=False)
    topics_covered = Column(JSON)  # [{topic: "recursion", depth: 3, timestamp: "..."}]
    questions_asked = Column(JSON)  # [{"question": "...", "timestamp": "...", "answered": true}]
    confusion_points = Column(JSON)  # [{"topic": "base case", "frequency": 3, "resolved": false}]
    engagement_score = Column(Float)  # 0.0-1.0 based on interaction quality
    total_speaking_time = Column(Integer)  # seconds
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    student = relationship("Student", back_populates="progress_records")


class ContextDocument(Base):
    """Course materials and documents for RAG"""
    __tablename__ = "context_documents"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    professor_id = Column(Integer, ForeignKey("professors.id"), nullable=False)
    file_path = Column(String(512), nullable=False)
    file_type = Column(String(50))  # pdf, pptx, md, txt
    content = Column(Text)  # Extracted text content
    embeddings_id = Column(String(255))  # Reference to vector DB collection
    metadata = Column(JSON)  # {topic_tags, course_id, lecture_number}
    uploaded_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    professor = relationship("Professor", back_populates="documents")


class SessionAnalytics(Base):
    """Computed analytics per session"""
    __tablename__ = "session_analytics"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    session_id = Column(Integer, ForeignKey("sessions.id"), nullable=False, unique=True)
    total_students = Column(Integer)
    avg_engagement_score = Column(Float)
    common_confusion_points = Column(JSON)  # [{topic, student_count, avg_resolution_time}]
    topic_coverage_matrix = Column(JSON)  # {topic: student_count}
    summary_text = Column(Text)
    generated_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    session = relationship("Session", back_populates="analytics")
