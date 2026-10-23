from typing import Literal

from pydantic import BaseModel, Field


class SeaweedFileAttributes(BaseModel):
    """Metadata attributes of the file stored in SeaweedFS"""

    file_size: int = 0
    mtime: int = 0
    mime: str = ""


class SeaweedEntry(BaseModel):
    """File or directory entry representation in SeaweedFS"""

    name: str
    is_directory: bool = False
    attributes: SeaweedFileAttributes = Field(default_factory=SeaweedFileAttributes)


class SeaweedNotificationMessage(BaseModel):
    """Payload containing old and new entry states"""

    old_entry: SeaweedEntry | None = None
    new_entry: SeaweedEntry
    delete_chunks: bool = False
    new_parent_path: str = ""


class SeaweedWebhookEvent(BaseModel):
    """Top-level webhook event sent by SeaweedFS Filer notifications"""

    key: str
    event_type: Literal["create", "delete", "update", "rename"]
    message: SeaweedNotificationMessage

    @property
    def s3_uri(self) -> str:
        """Convert SeaweedFS filer key to S3 URI"""

        return self.key.replace("/buckets/", "s3://", 1)


class InputMessage(BaseModel):
    """Input message"""

    id: int
    uri: str
    name: str
