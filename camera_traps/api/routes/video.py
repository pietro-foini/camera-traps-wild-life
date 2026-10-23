from datetime import datetime, timezone
from typing import Annotated

from fastapi import Depends, HTTPException
from faststream.redis import StreamSub
from faststream.redis.fastapi import RedisRouter
from trackers import SORTTracker

from camera_traps.api.dependencies import get_classifier, get_db, get_detector, get_storage, get_tracker
from camera_traps.api.schemas import InputMessage
from camera_traps.db.models import ProcessingStatus, VideoInputModel, VideoOutputModel
from camera_traps.db.postgres import PostgresHandler
from camera_traps.errors import StorageException
from camera_traps.models.domain import Predictor
from camera_traps.models.schemas import VideoDetectionResponse
from camera_traps.services.video import annotate, process, smooth
from camera_traps.settings import S
from camera_traps.storage.s3 import S3Storage

video_router = RedisRouter(S.REDIS_URL)


@video_router.subscriber(stream=StreamSub("video-queue", group="group", consumer="consumer"))
@video_router.post(path="/predict-video", response_model=VideoDetectionResponse, status_code=200)
def predict_video(
    message: InputMessage,
    db: Annotated[PostgresHandler, Depends(get_db)],
    detector: Annotated[Predictor, Depends(get_detector)],
    classifier: Annotated[Predictor, Depends(get_classifier)],
    storage: Annotated[S3Storage, Depends(get_storage)],
    tracker: Annotated[SORTTracker, Depends(get_tracker)],
):
    """Predict a video"""

    db.update_record(
        VideoInputModel,
        record_id=message.id,
        status=ProcessingStatus.PROCESSING,
        processing_started_at=datetime.now(timezone.utc),
    )

    # Read video file.
    try:
        video_bytes = storage.download(message.uri)
    except StorageException as e:
        raise HTTPException(status_code=400, detail=str(e))

    # Get the predictions.
    response = process(
        filename=message.uri,
        video_bytes=video_bytes,
        detector=detector,
        classifier=classifier,
        tracker=tracker,
        detector_threshold=S.DETECTOR_THRESHOLD,
        target_fps=S.FRAMES_PER_SECOND,
    )

    # Consolidate predictions.
    response = smooth(response=response, threshold=S.CLASSIFIER_THRESHOLD)

    # Store record on database.
    db.update_record(
        VideoInputModel,
        record_id=message.id,
        status=ProcessingStatus.COMPLETED,
        processing_ended_at=datetime.now(timezone.utc),
    )
    for pred in response.predictions:
        detection_record = VideoOutputModel(
            video_input_id=message.id,
            frame_id=pred.frame_id,
            tracker_id=pred.tracking_id,
            label=pred.class_name,
            confidence=pred.confidence,
            x_min=pred.box.xmin,
            y_min=pred.box.ymin,
            x_max=pred.box.xmax,
            y_max=pred.box.ymax,
        )
        db.add_record(detection_record)

    # Render annotated video.
    video_bytes_output = annotate(video_bytes=video_bytes, response=response, target_fps=S.FRAMES_PER_SECOND)

    storage.upload(
        key=f"output/{message.name}",
        data=video_bytes_output,
        bucket=S.S3_BUCKET,
        content_type="video/mp4",
    )

    return response
