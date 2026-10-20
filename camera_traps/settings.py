from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Global Settings"""

    # Postgres.
    DB_USER: str
    """user"""
    DB_PASSWORD: str
    """passw"""
    DB_HOST: str
    """database host"""
    DB_PORT: str
    """database port"""
    DB_NAME: str
    """database name"""

    # Storage.
    S3_ENDPOINT_URL: str
    """endpoint url"""
    S3_ACCESS_KEY: str
    """access key"""
    S3_SECRET_KEY: str
    """secret key"""
    S3_BUCKET: str = "bucket-cameratraps"
    """bucket name"""

    # Models for detection and classification.
    CLASSIFIER_MODEL_PATH: str
    """path to the model used for image classification"""
    DETECTOR_MODEL_PATH: str
    """path to the model used for object detection"""
    CLASSIFIER_IMAGE_SIZE: tuple[int, int] = (224, 224)
    """image size used for image classification"""
    DETECTOR_IMAGE_SIZE: tuple[int, int] = (640, 640)
    """image size used for object detection"""

    # Thresholds filtering predictions.
    CLASSIFIER_THRESHOLD: float = 0.95
    """threshold for keeping classified images"""
    DETECTOR_THRESHOLD: float = 0.8
    """threshold for keeping detected objects"""

    # Video settings.
    FRAMES_PER_SECOND: int | None = None
    """frames per second"""


S = Settings()  # type: ignore
