import io
from unittest.mock import MagicMock, patch
import av
import numpy as np
from fastapi import FastAPI
from fastapi.testclient import TestClient
from trackers import SORTTracker

from tests.config import *
from camera_traps.api.schemas import (
    SeaweedEntry,
    SeaweedFileAttributes,
    SeaweedNotificationMessage,
    SeaweedWebhookEvent,
)
from camera_traps.models.models import Classification, Detection, BoundingBox


def create_dummy_video_bytes():
    output = io.BytesIO()

    container = av.open(output, mode="w", format="mp4")
    stream = container.add_stream("mpeg4", rate=30)
    stream.width = 100
    stream.height = 100
    stream.pix_fmt = "yuv420p"

    for i in range(4):
        array = np.zeros((10, 10, 3), dtype=np.uint8)
        frame = av.VideoFrame.from_ndarray(array, format="rgb24")
        for packet in stream.encode(frame):
            container.mux(packet)

    for packet in stream.encode():
        container.mux(packet)

    container.close()

    return output.getvalue()


def create_webhook_payload(
    key="/buckets/my-bucket/test.mp4",
    name="test.mp4",
    event_type="create",
    is_directory=False,
    mime="video/mp4",
):
    event = SeaweedWebhookEvent(
        key=key,
        event_type=event_type,
        message=SeaweedNotificationMessage(
            new_entry=SeaweedEntry(
                name=name,
                is_directory=is_directory,
                attributes=SeaweedFileAttributes(mime=mime),
            )
        ),
    )

    return event.model_dump()


@patch("camera_traps.api.routes.video.annotate", return_value=b"fake_annotated_bytes")
def test_predict_video_success(mock_annotate):
    from camera_traps.api.routes import video_router

    mock_detector = MagicMock()
    mock_detector.predict.side_effect = [
        [
            Detection(
                class_id=0,
                class_name="animal",
                confidence=0.90,
                box=BoundingBox(xmin=10.0, ymin=10.0, xmax=50.0, ymax=50.0),
            )
        ],
        [
            Detection(
                class_id=1,
                class_name="animal",
                confidence=0.95,
                box=BoundingBox(xmin=11.0, ymin=11.0, xmax=50.0, ymax=50.0),
            )
        ],
        [
            Detection(
                class_id=0,
                class_name="animal",
                confidence=0.90,
                box=BoundingBox(xmin=12.0, ymin=12.0, xmax=50.0, ymax=50.0),
            )
        ],
        [
            Detection(
                class_id=1,
                class_name="animal",
                confidence=0.95,
                box=BoundingBox(xmin=13.0, ymin=13.0, xmax=50.0, ymax=50.0),
            )
        ],
    ]

    mock_classifier = MagicMock()
    mock_classifier.predict.side_effect = [
        [Classification(class_id=1, class_name="fox", confidence=0.95)],
        [Classification(class_id=1, class_name="fox", confidence=0.98)],
    ]

    app = FastAPI()
    app.include_router(video_router)
    client = TestClient(app)

    mock_db = MagicMock()
    mock_saved_video = MagicMock()
    mock_saved_video.id = 1
    mock_db.add_record.return_value = mock_saved_video

    mock_storage = MagicMock()
    mock_storage.download.return_value = create_dummy_video_bytes()

    app.state.classifier = mock_classifier
    app.state.detector = mock_detector
    app.state.db = mock_db
    app.state.storage = mock_storage
    app.state.tracker = SORTTracker()

    payload = create_webhook_payload()
    response = client.post(
        "/predict-video",
        json=payload,
    )

    assert response.status_code == 200
    assert "test.mp4" in response.text
    mock_storage.download.assert_called_once_with("s3://my-bucket/test.mp4")
    mock_storage.upload.assert_called_once()
    assert mock_detector.predict.call_count == 4
    assert mock_classifier.predict.call_count == 2
    assert mock_db.add_record.call_count >= 1

    app.dependency_overrides.clear()


def test_predict_video_invalid_content_type():
    from camera_traps.api.routes import video_router

    app = FastAPI()
    app.include_router(video_router)
    client = TestClient(app)

    app.state.classifier = MagicMock()
    app.state.detector = MagicMock()
    app.state.db = MagicMock()
    app.state.storage = MagicMock()
    app.state.tracker = MagicMock()

    payload = create_webhook_payload(
        key="/buckets/my-bucket/test.txt",
        name="test.txt",
        mime="text/plain",
    )
    response = client.post(
        "/predict-video",
        json=payload,
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Uploaded file is not a valid video."

    app.dependency_overrides.clear()


def test_predict_video_no_detections():
    from camera_traps.api.routes import video_router

    mock_detector = MagicMock()
    mock_detector.predict.return_value = []

    mock_classifier = MagicMock()

    app = FastAPI()
    app.include_router(video_router)
    client = TestClient(app)

    mock_db = MagicMock()
    mock_saved_video = MagicMock()
    mock_saved_video.id = 1
    mock_db.add_record.return_value = mock_saved_video

    mock_storage = MagicMock()
    mock_storage.download.return_value = create_dummy_video_bytes()

    app.state.classifier = mock_classifier
    app.state.detector = mock_detector
    app.state.db = mock_db
    app.state.storage = mock_storage
    app.state.tracker = MagicMock()

    payload = create_webhook_payload(
        key="/buckets/my-bucket/empty.mp4",
        name="empty.mp4",
    )
    response = client.post(
        "/predict-video",
        json=payload,
    )

    assert response.status_code == 200
    assert "empty.mp4" in response.text
    mock_classifier.predict.assert_not_called()
    mock_storage.upload.assert_not_called()

    app.dependency_overrides.clear()
