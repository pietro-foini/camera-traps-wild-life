from unittest.mock import ANY, MagicMock
import cv2
import numpy as np
from fastapi import FastAPI
from fastapi.testclient import TestClient

from tests.config import *
from camera_traps.api.schemas import InputMessage
from camera_traps.models.schemas import Classification


def create_dummy_image_bytes():
    """Generate image bytes."""

    img = np.zeros((10, 10, 3), dtype=np.uint8)
    _, encoded_img = cv2.imencode(".jpg", img)

    return encoded_img.tobytes()


def test_predict_image_success():
    """Successful image prediction."""

    from camera_traps.api.routes import image_router

    # Setup Classifier Mock.
    mock_predictor = MagicMock()
    mock_predictor.predict.return_value = [
        Classification(class_id=1, class_name="fox", confidence=0.85),
        Classification(class_id=2, class_name="deer", confidence=0.10),
        Classification(class_id=3, class_name="bear", confidence=0.03),
        Classification(class_id=4, class_name="rabbit", confidence=0.01),
        Classification(class_id=5, class_name="wolf", confidence=0.01),
    ]

    # Setup DB Mock.
    mock_db = MagicMock()
    mock_saved_image = MagicMock()
    mock_saved_image.id = 123
    mock_db.add_record.return_value = mock_saved_image

    # Setup Storage Mock.
    mock_storage = MagicMock()
    mock_storage.download.return_value = create_dummy_image_bytes()

    # Application.
    app = FastAPI()
    app.include_router(image_router)
    client = TestClient(app)
    app.state.classifier = mock_predictor
    app.state.db = mock_db
    app.state.storage = mock_storage

    # Send request.
    payload = InputMessage(uri="s3://my-bucket/test.jpg", name="test.jpg").model_dump()
    response = client.post(
        "/predict-image",
        json=payload,
    )

    assert response.status_code == 200

    data = response.json()
    assert data["predictions"][0]["class_name"] == "fox"
    mock_storage.download.assert_called_once_with("s3://my-bucket/test.jpg")
    mock_predictor.predict.assert_called_once_with(ANY, top=5)
    assert mock_db.add_record.call_count == 6

    app.dependency_overrides.clear()


def test_predict_image_corrupt_bytes():
    """Corrupt bytes."""

    from camera_traps.api.routes import image_router

    mock_storage = MagicMock()
    mock_storage.download.return_value = b"corrupted data"

    app = FastAPI()
    app.include_router(image_router)
    client = TestClient(app)

    app.state.classifier = MagicMock()
    app.state.db = MagicMock()
    app.state.storage = mock_storage

    payload = InputMessage(uri="s3://my-bucket/test.jpg", name="test.jpg").model_dump()
    response = client.post(
        "/predict-image",
        json=payload,
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Uploaded file is not a valid image."

    app.dependency_overrides.clear()
