import io
from collections import defaultdict

import av
import numpy as np
import supervision as sv
from tqdm import tqdm
from trackers.core.base import BaseTracker

from camera_traps.data import ClassifierClasses
from camera_traps.models.domain import Predictor
from camera_traps.models.models import BoundingBox, Detection, VideoDetectionResponse


def process(
    filename: str,
    video_bytes: bytes,
    detector: Predictor,
    classifier: Predictor,
    tracker: BaseTracker,
    detector_threshold: float = 0.5,
) -> VideoDetectionResponse:
    """
    Process video stream by running object detection, tracking, and crop classification frame by frame.

    :param filename: name of the video file
    :param video_bytes: raw bytes of the video file
    :param detector: object detector model instance
    :param classifier: crop classifier model instance
    :param tracker: object tracker instance
    :param detector_threshold: minimum confidence threshold for object detection
    :return: response payload containing frame-by-frame object detections and tracking results
    """

    # Open video file.
    container = av.open(io.BytesIO(video_bytes))

    # Initialize prediction object.
    response = VideoDetectionResponse(filename=filename)

    try:
        stream = container.decode(video=0)

        for frame_id, frame in enumerate(tqdm(stream, total=container.streams.video[0].frames, unit="frame")):
            frame_np = frame.to_ndarray(format="rgb24")

            # Run detector.
            predictions = detector.predict(frame_np)

            if predictions:
                detections = sv.Detections(
                    xyxy=np.array([d.box.to_xyxy() for d in predictions]),
                    confidence=np.array([d.confidence for d in predictions]),
                    class_id=np.array([d.class_id for d in predictions]),
                )
            else:
                detections = sv.Detections.empty()

            # Run tracker.
            detections = tracker.update(detections)

            # Store detection and tracking results.
            if detections.tracker_id is not None and len(detections.tracker_id) > 0:
                for xyxy, confidence, class_id, tracker_id in zip(
                    detections.xyxy,
                    detections.confidence,
                    detections.class_id,
                    detections.tracker_id,
                ):
                    if tracker_id == -1 or confidence < detector_threshold:
                        continue

                    xmin, ymin, xmax, ymax = map(int, xyxy)

                    if xmax <= xmin or ymax <= ymin:
                        continue

                    crop = frame_np[ymin:ymax, xmin:xmax]

                    if crop.size == 0:
                        continue

                    # Run classifier.
                    predictions = classifier.predict(crop, top=1)

                    if not predictions:
                        continue

                    response.predictions.append(
                        Detection(
                            class_name=predictions[0].class_name,
                            box=BoundingBox(xmin=xmin, ymin=ymin, xmax=xmax, ymax=ymax),
                            confidence=predictions[0].confidence,
                            tracking_id=tracker_id,
                            frame_id=frame_id,
                        )
                    )
    finally:
        container.close()

    return response


def smooth(response: VideoDetectionResponse, threshold: float) -> VideoDetectionResponse:
    """
    Consolidate tracking labels by selecting the most confident class per track.

    :param response: input containing video predictions
    :param threshold: minimum confidence threshold for score aggregation
    :return: processed video predictions with consolidated labels and re-indexed tracking IDs
    """

    if not response.predictions:
        return response

    tracker_scores = defaultdict(lambda: defaultdict(float))
    for det in response.predictions:
        if det.tracking_id is not None and det.confidence >= threshold:
            tracker_scores[det.tracking_id][det.class_name] += det.confidence

    best_labels = {}
    for tid, class_counts in tracker_scores.items():
        if class_counts:
            best_labels[tid] = max(class_counts, key=class_counts.get)

    filtered_preds = []
    for det in response.predictions:
        if det.tracking_id in best_labels:
            assigned_label = best_labels[det.tracking_id]
            if assigned_label != ClassifierClasses.none_of_the_above:
                filtered_preds.append(det.model_copy(update={"class_name": assigned_label}))

    if not filtered_preds:
        return VideoDetectionResponse(filename=response.filename, predictions=[])

    tracker_map = {}
    for det in filtered_preds:
        if det.tracking_id not in tracker_map:
            tracker_map[det.tracking_id] = len(tracker_map)

    smoothed_predictions = [
        det.model_copy(update={"tracking_id": tracker_map[det.tracking_id]}) for det in filtered_preds
    ]

    return VideoDetectionResponse(filename=response.filename, predictions=smoothed_predictions)


def annotate(video_bytes: bytes, response: VideoDetectionResponse) -> bytes:
    """
    Annotate video frames with bounding boxes and labels entirely in memory.

    :param video_bytes: raw bytes of the input video file
    :param response: video predictions containing detections and tracking IDs
    :return: raw bytes of the annotated MP4 video
    """

    in_container = av.open(io.BytesIO(video_bytes))
    in_stream = in_container.streams.video[0]

    out_buffer = io.BytesIO()
    out_container = av.open(out_buffer, mode="w", format="mp4")

    out_stream = out_container.add_stream("libx264", rate=in_stream.average_rate or 30)
    out_stream.width = in_stream.codec_context.width
    out_stream.height = in_stream.codec_context.height
    out_stream.pix_fmt = "yuv420p"
    out_stream.options = {"preset": "ultrafast", "movflags": "+faststart"}

    box_annotator = sv.BoxAnnotator(thickness=2, color_lookup=sv.ColorLookup.TRACK)
    label_annotator = sv.LabelAnnotator(
        text_scale=0.6,
        text_thickness=1,
        color_lookup=sv.ColorLookup.TRACK,
    )

    predictions_by_frame = defaultdict(list)
    for pred in response.predictions:
        predictions_by_frame[pred.frame_id].append(pred)

    try:
        for frame_id, frame in enumerate(
            tqdm(in_container.decode(video=0), total=in_container.streams.video[0].frames, unit="frame")
        ):
            frame_bgr = frame.to_ndarray(format="bgr24")
            frame_predictions = predictions_by_frame.get(frame_id, [])

            if frame_predictions:
                labels = [f"{p.class_name} #{p.tracking_id}" for p in frame_predictions]
                detections_sv = sv.Detections(
                    xyxy=np.array([[p.box.xmin, p.box.ymin, p.box.xmax, p.box.ymax] for p in frame_predictions]),
                    tracker_id=np.array([p.tracking_id for p in frame_predictions]),
                )
                frame_bgr = box_annotator.annotate(scene=frame_bgr, detections=detections_sv)
                frame_bgr = label_annotator.annotate(scene=frame_bgr, detections=detections_sv, labels=labels)

            out_frame = av.VideoFrame.from_ndarray(frame_bgr, format="bgr24")
            for packet in out_stream.encode(out_frame):
                out_container.mux(packet)

        for packet in out_stream.encode():
            out_container.mux(packet)
    finally:
        in_container.close()
        out_container.close()

    return out_buffer.getvalue()
