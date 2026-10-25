from typing import Annotated

from fastapi import Depends, Response
from faststream.redis.fastapi import RedisRouter

from camera_traps.api.dependencies import get_db
from camera_traps.api.schemas import InputMessage, SeaweedWebhookEvent
from camera_traps.db.models import ImageInputModel, VideoInputModel
from camera_traps.db.postgres import PostgresHandler
from camera_traps.settings import S

webhook_router = RedisRouter(S.REDIS_URL)


@webhook_router.post(path="/webhook", status_code=200)
async def webhook_receiver(
    event: SeaweedWebhookEvent,
    db: Annotated[PostgresHandler, Depends(get_db)],
):
    """Send message to Redis server"""

    if event.message.new_entry.is_directory:
        return Response(status_code=200)

    mime = event.message.new_entry.attributes.mime
    if mime.startswith("image/"):
        # Store input record on database.
        image_record = ImageInputModel(filename=event.s3_uri, site="1")  # TODO: allow dynamic site
        saved_image = db.add_record(image_record)
        # Send message to queue.
        message = InputMessage(id=saved_image.id, uri=event.s3_uri, name=event.message.new_entry.name)
        await webhook_router.broker.publish(message.model_dump(), stream="image-queue")
    elif mime.startswith("video/"):
        # Store input record on database.
        video_record = VideoInputModel(filename=event.s3_uri, site="1")  # TODO: allow dynamic site
        saved_video = db.add_record(video_record)
        # Send message to queue.
        message = InputMessage(id=saved_video.id, uri=event.s3_uri, name=event.message.new_entry.name)
        await webhook_router.broker.publish(message.model_dump(), stream="video-queue")

    return Response(status_code=200)
