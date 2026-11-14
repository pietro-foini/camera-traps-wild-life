import base64
from typing import Literal

from pydantic import BaseModel, Field, field_validator


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
    extended: dict[str, str] = Field(default_factory=dict)

    @field_validator("extended", mode="before")
    @classmethod
    def decode_extended(cls, v: dict[str, str] | None) -> dict[str, str]:
        if not v:
            return {}
        decoded = {}
        for key, val in v.items():
            try:
                decoded[key] = base64.b64decode(val).decode("utf-8")
            except (UnicodeDecodeError, TypeError):
                decoded[key] = val
        return decoded

    def _get_float(self, key: str) -> float | None:
        if not self.extended:
            return None
        val = self.extended.get(key)
        if val is None or val == "":
            return None
        try:
            return float(val)
        except (ValueError, TypeError):
            return None

    @property
    def site(self) -> str:
        if not self.extended:
            return "-1"
        return self.extended.get("Seaweed-Site", "-1")

    @property
    def latitude(self) -> float | None:
        return self._get_float("Seaweed-Latitude")

    @property
    def longitude(self) -> float | None:
        return self._get_float("Seaweed-Longitude")

    @property
    def duration(self) -> float | None:
        return self._get_float("Seaweed-Duration")


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
