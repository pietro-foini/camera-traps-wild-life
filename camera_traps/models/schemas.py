from pydantic import BaseModel, Field


class BoundingBox(BaseModel):
    """Bounding box spatial coordinates."""

    xmin: float
    ymin: float
    xmax: float
    ymax: float

    def to_xyxy(self) -> list[float]:
        return [self.xmin, self.ymin, self.xmax, self.ymax]


class Detection(BaseModel):
    """Object detection result."""

    class_id: int | None = None
    class_name: str
    confidence: float | int = Field(ge=0.0, le=1.0)
    box: BoundingBox
    tracking_id: int | None = None
    frame_id: int | None = None


class Classification(BaseModel):
    """Image classification result."""

    class_id: int
    class_name: str
    confidence: float | int = Field(ge=0.0, le=1.0)


class ImageClassificationResponse(BaseModel):
    """Response payload containing image classification predictions."""

    filename: str
    predictions: list[Classification] = Field(default_factory=list)


class VideoDetectionResponse(BaseModel):
    """Response payload containing object detections for a video."""

    filename: str
    predictions: list[Detection] = Field(default_factory=list)
