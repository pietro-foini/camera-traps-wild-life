from datetime import datetime

from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.orm import DeclarativeBase, relationship


class Base(DeclarativeBase):
    """Base declarative class for all SQLAlchemy ORM (Object-Relational Mapping) models"""

    pass


class ImageInputModel(Base):
    """Stores metadata for uploaded image files processed by the inference pipeline."""

    __tablename__ = "image_inputs"

    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    predictions = relationship("ImageOutputModel", back_populates="image", cascade="all, delete-orphan")


class ImageOutputModel(Base):
    """Stores classification results associated with an input image."""

    __tablename__ = "image_outputs"

    id = Column(Integer, primary_key=True, index=True)
    image_input_id = Column(Integer, ForeignKey("image_inputs.id"), nullable=False)
    label = Column(String, nullable=False)
    confidence = Column(Float, nullable=False)

    image = relationship("ImageInputModel", back_populates="predictions")


class VideoInputModel(Base):
    """Stores metadata for uploaded video files processed by the inference pipeline."""

    __tablename__ = "video_inputs"

    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    detections = relationship("VideoOutputModel", back_populates="video", cascade="all, delete-orphan")


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
