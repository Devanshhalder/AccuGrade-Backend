from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.sql import func

from database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)
    role = Column(String, nullable=False, default="evaluator")
    is_active = Column(Boolean, default=True)


class EvaluationBatch(Base):
    __tablename__ = "evaluation_batches"

    id = Column(Integer, primary_key=True, index=True)
    batch_name = Column(String, nullable=False)
    subject = Column(String, nullable=False)
    examination = Column(String, nullable=False)
    max_marks = Column(Float, nullable=False)
    status = Column(String, nullable=False, default="created")

    assisted_marking = Column(Boolean, default=True)
    unchecked_answers = Column(Boolean, default=True)
    marking_anomalies = Column(Boolean, default=True)
    unusual_scoring = Column(Boolean, default=True)

    created_at = Column(
        DateTime,
        server_default=func.now(),
        nullable=False
    )


class AnswerSheet(Base):
    __tablename__ = "answer_sheets"

    id = Column(Integer, primary_key=True, index=True)

    batch_id = Column(
        Integer,
        ForeignKey("evaluation_batches.id"),
        nullable=False,
        index=True
    )

    original_filename = Column(String, nullable=False)
    stored_filename = Column(String, nullable=False)
    file_path = Column(String, nullable=False)

    status = Column(
        String,
        nullable=False,
        default="uploaded"
    )

    student_identifier = Column(String, nullable=True)
    assigned_evaluator = Column(String, nullable=True)

    ai_status = Column(String, nullable=True)
    ai_marks = Column(Float, nullable=True)
    ai_confidence = Column(Float, nullable=True)
    ai_reason = Column(Text, nullable=True)

    created_at = Column(
        DateTime,
        server_default=func.now(),
        nullable=False
    )


class BatchEvaluator(Base):
    __tablename__ = "batch_evaluators"

    id = Column(Integer, primary_key=True, index=True)

    batch_id = Column(
        Integer,
        ForeignKey("evaluation_batches.id"),
        nullable=False,
        index=True
    )

    evaluator_name = Column(
        String,
        nullable=False
    )

    assigned_at = Column(
        DateTime,
        server_default=func.now(),
        nullable=False
    )