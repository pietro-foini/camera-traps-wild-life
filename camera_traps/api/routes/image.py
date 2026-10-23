from datetime import datetime, timezone
from typing import Annotated

import cv2
import numpy as np
from fastapi import Depends, HTTPException
from faststream.redis import StreamSub
from faststream.redis.fastapi import RedisRouter

from camera_traps.api.dependencies import get_classifier, get_db, get_storage
from camera_traps.api.schemas import InputMessage
from camera_traps.db.models import ImageInputModel, ImageOutputModel, ProcessingStatus
from camera_traps.db.postgres import PostgresHandler
from camera_traps.errors import StorageException
from camera_traps.models.domain import Predictor
from camera_traps.models.schemas import ImageClassificationResponse
from camera_traps.settings import S
from camera_traps.storage.s3 import S3Storage

image_router = RedisRouter(S.REDIS_URL)


@image_router.subscriber(stream=StreamSub("image-queue", group="group", consumer="consumer"))
@image_router.post(path="/predict-image", response_model=ImageClassificationResponse, status_code=200)
def predict_image(
    message: InputMessage,
    db: Annotated[PostgresHandler, Depends(get_db)],
    storage: Annotated[S3Storage, Depends(get_storage)],
    classifier: Annotated[Predictor, Depends(get_classifier)],
):
    """Predict an image"""

    db.update_record(
        ImageInputModel,
        record_id=message.id,
        status=ProcessingStatus.PROCESSING,
        processing_started_at=datetime.now(timezone.utc),
    )

    # Read image.
    try:
        img_bytes = storage.download(message.uri)
    except StorageException as e:
        raise HTTPException(status_code=400, detail=str(e))

    img_array = cv2.imdecode(np.frombuffer(img_bytes, np.uint8), cv2.IMREAD_COLOR)

    if img_array is None:
        raise HTTPException(status_code=400, detail="Uploaded file is not a valid image.")

    img_array = cv2.cvtColor(img_array, cv2.COLOR_BGR2RGB)

    # Predict.
    predictions = classifier.predict(img_array, top=5)
    response = ImageClassificationResponse(filename=message.uri, predictions=predictions)

    # Store output record on database.
    db.update_record(
        ImageInputModel,
        record_id=message.id,
        status=ProcessingStatus.COMPLETED,
        processing_ended_at=datetime.now(timezone.utc),
    )
    for pred in response.predictions:
        pred_record = ImageOutputModel(
            image_input_id=message.id,
            label=pred.class_name,
            confidence=float(pred.confidence),
        )
        db.add_record(pred_record)

    return response
