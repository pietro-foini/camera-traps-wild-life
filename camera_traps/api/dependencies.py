from fastapi import Request
from trackers import SORTTracker

from camera_traps.db.postgres import PostgresHandler
from camera_traps.models.domain import Predictor
from camera_traps.storage.s3 import S3Storage


def get_db(request: Request) -> PostgresHandler:
    """Retrieve the PostgreSQL database handler instance from the application state"""

    return request.app.state.db


def get_detector(request: Request) -> Predictor:
    """Retrieve the initialized object detector model from the application state"""

    return request.app.state.detector


def get_classifier(request: Request) -> Predictor:
    """Retrieve the initialized image classifier model from the application state"""

    return request.app.state.classifier


def get_tracker(request: Request) -> SORTTracker:
    """Retrieve the SORT tracker instance from the application state"""

    return request.app.state.tracker


def get_storage(request: Request) -> S3Storage:
    """Retrieve the S3 storage client from the application state"""

    return request.app.state.storage
