from typing import Annotated

import cv2
import numpy as np
from fastapi import APIRouter, Depends, HTTPException

from camera_traps.api.dependencies import get_classifier, get_db, get_storage
from camera_traps.api.schemas import SeaweedWebhookEvent
from camera_traps.db.models import ImageInputModel, ImageOutputModel
from camera_traps.db.postgres import PostgresHandler
from camera_traps.errors import StorageException
from camera_traps.models.domain import Predictor
from camera_traps.models.models import ImageClassificationResponse
from camera_traps.storage.s3 import S3Storage

image_router = APIRouter()


@image_router.post(path="/predict-image", response_model=ImageClassificationResponse, status_code=200)
def predict_image(
    message: SeaweedWebhookEvent,
    db: Annotated[PostgresHandler, Depends(get_db)],
    storage: Annotated[S3Storage, Depends(get_storage)],
    classifier: Annotated[Predictor, Depends(get_classifier)],
):

    if (
        message.event_type != "create"
        or message.message.new_entry.is_directory
        or not message.message.new_entry.attributes.mime.startswith("image/")
    ):
        raise HTTPException(status_code=400, detail="Uploaded file is not a valid image.")

    # Store input record on database.
    image_record = ImageInputModel(filename=message.s3_uri)
    saved_image = db.add_record(image_record)

    # Read image.
    try:
        img_bytes = storage.download(message.s3_uri)
    except StorageException as e:
        raise HTTPException(status_code=400, detail=str(e))

    img_array = cv2.imdecode(np.frombuffer(img_bytes, np.uint8), cv2.IMREAD_COLOR)

    if img_array is None:
        raise HTTPException(status_code=400, detail="Uploaded file is not a valid image.")

    img_array = cv2.cvtColor(img_array, cv2.COLOR_BGR2RGB)

    # Predict.
    predictions = classifier.predict(img_array, top=5)
    response = ImageClassificationResponse(filename=message.s3_uri, predictions=predictions)

    # Store output record on database.
    for pred in response.predictions:
        pred_record = ImageOutputModel(
            image_input_id=saved_image.id,
            label=pred.class_name,
            confidence=float(pred.confidence),
        )
        db.add_record(pred_record)

    return response
