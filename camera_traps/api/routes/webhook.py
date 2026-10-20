from fastapi import Response
from faststream.redis.fastapi import RedisRouter

from camera_traps.api.schemas import InputMessage, SeaweedWebhookEvent
from camera_traps.settings import S

webhook_router = RedisRouter(S.REDIS_URL)


@webhook_router.post(path="/webhook", status_code=200)
async def webhook_receiver(event: SeaweedWebhookEvent):
    """Send message to Redis server"""

    if event.message.new_entry.is_directory:
        return Response(status_code=200)

    mime = event.message.new_entry.attributes.mime
    if mime.startswith("image/"):
        message = InputMessage(uri=event.s3_uri, name=event.message.new_entry.name)
        await webhook_router.broker.publish(message.model_dump(), stream="image-queue")
    elif mime.startswith("video/"):
        message = InputMessage(uri=event.s3_uri, name=event.message.new_entry.name)
        await webhook_router.broker.publish(message.model_dump(), stream="video-queue")

    return Response(status_code=200)
