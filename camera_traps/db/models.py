from datetime import datetime, timezone
from enum import StrEnum

from sqlalchemy import Boolean, Column, DateTime, Enum, Float, ForeignKey, Integer, String
from sqlalchemy.orm import DeclarativeBase, relationship


class ProcessingStatus(StrEnum):
    """Enum for processing status of inference pipeline"""

    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class Base(DeclarativeBase):
    """Base declarative class for all SQLAlchemy ORM (Object-Relational Mapping) models"""

    pass


class ImageInputModel(Base):
    """Stores metadata for uploaded image files processed by the inference pipeline."""

    __tablename__ = "image_inputs"

    id = Column(Integer, primary_key=True, index=True)
    site = Column(String, nullable=False)
    filename = Column(String, nullable=False)
    status = Column(Enum(ProcessingStatus), default=ProcessingStatus.PENDING, nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    processing_started_at = Column(DateTime(timezone=True), nullable=True)
    processing_ended_at = Column(DateTime(timezone=True), nullable=True)

    predictions = relationship("ImageOutputModel", back_populates="image", cascade="all, delete-orphan")
    validations = relationship("ImageValidationModel", back_populates="image", cascade="all, delete-orphan")


class ImageOutputModel(Base):
    """Stores classification results associated with an input image."""

    __tablename__ = "image_outputs"

    id = Column(Integer, primary_key=True, index=True)
    image_input_id = Column(Integer, ForeignKey("image_inputs.id"), nullable=False)
    label = Column(String, nullable=False)
    confidence = Column(Float, nullable=False)

    image = relationship("ImageInputModel", back_populates="predictions")


class ImageValidationModel(Base):
    """Stores human validation at the tracker/individual level for a image."""

    __tablename__ = "image_validations"

    id = Column(Integer, primary_key=True, index=True)
    image_input_id = Column(Integer, ForeignKey("image_inputs.id", ondelete="CASCADE"), nullable=False, index=True)
    label = Column(String, nullable=False)
    comments = Column(String, nullable=True)
    is_modified = Column(Boolean, default=False, nullable=False)
    validated_by = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    image = relationship("ImageInputModel", back_populates="validations")


class VideoInputModel(Base):
    """Stores metadata for uploaded video files processed by the inference pipeline."""

    __tablename__ = "video_inputs"

    id = Column(Integer, primary_key=True, index=True)
    site = Column(String, nullable=False)
    filename = Column(String, nullable=False)
    duration = Column(Float, nullable=False)
    status = Column(Enum(ProcessingStatus), default=ProcessingStatus.PENDING, nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    processing_started_at = Column(DateTime(timezone=True), nullable=True)
    processing_ended_at = Column(DateTime(timezone=True), nullable=True)

    detections = relationship("VideoOutputModel", back_populates="video", cascade="all, delete-orphan")
    validations = relationship("VideoValidationModel", back_populates="video", cascade="all, delete-orphan")


class VideoOutputModel(Base):
    """Stores object detection, classification, and tracking bounding box coordinates per video frame."""

    __tablename__ = "video_outputs"

    id = Column(Integer, primary_key=True, index=True)
    video_input_id = Column(Integer, ForeignKey("video_inputs.id"), nullable=False)
    frame_id = Column(Integer, nullable=False)
    tracker_id = Column(Integer, nullable=False)
    label = Column(String, nullable=False)
    confidence = Column(Float, nullable=False)
    x_min = Column(Float, nullable=False)
    y_min = Column(Float, nullable=False)
    x_max = Column(Float, nullable=False)
    y_max = Column(Float, nullable=False)

    video = relationship("VideoInputModel", back_populates="detections")


class VideoValidationModel(Base):
    """Stores human validation at the tracker/individual level for a video."""

    __tablename__ = "video_validations"

    id = Column(Integer, primary_key=True, index=True)
    video_input_id = Column(Integer, ForeignKey("video_inputs.id", ondelete="CASCADE"), nullable=False, index=True)
    tracker_id = Column(Integer, nullable=True)
    label = Column(String, nullable=False)
    comments = Column(String, nullable=True)
    is_modified = Column(Boolean, default=False, nullable=False)
    validated_by = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    video = relationship("VideoInputModel", back_populates="validations")
