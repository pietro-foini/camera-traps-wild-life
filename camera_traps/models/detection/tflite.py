import logging
import os
from typing import Any

import cv2
import numpy as np
from ai_edge_litert.interpreter import Interpreter

from camera_traps.data import DetectorClasses
from camera_traps.models.domain import Predictor
from camera_traps.models.schemas import BoundingBox, Detection


class TFLiteImageDetector(Predictor):
    """TFLite Image Detector."""

    def __init__(self, img_size: tuple[int, int]) -> None:
        super().__init__()

        self.img_size = img_size
        self._class_names = tuple(DetectorClasses)
        self._input_details = None
        self._output_details = None

    def load(self, artifact_uri: str) -> None:
        """Load model."""

        if not os.path.exists(artifact_uri):
            raise FileNotFoundError(f"Model not found: {artifact_uri}")

        self._model = Interpreter(model_path=artifact_uri, num_threads=4)
        self._model.allocate_tensors()

        self._input_details = self._model.get_input_details()
        self._output_details = self._model.get_output_details()

        logging.info("Loaded model: %s", artifact_uri)

    def preprocess(self, prediction_input: np.ndarray) -> np.ndarray:
        """Preprocess image."""

        prediction_input = cv2.resize(prediction_input, self.img_size)
        prediction_input = np.expand_dims(prediction_input, axis=0)
        prediction_input = prediction_input.astype(np.float32) / 255.0

        return np.transpose(prediction_input, (0, 3, 1, 2))

    def predict(self, instance: np.ndarray, **kwargs: Any) -> list[Detection]:
        """Run image classification."""

        prediction_input = self.preprocess(instance)

        self._model.set_tensor(self._input_details[0]["index"], prediction_input)
        self._model.invoke()

        results = self._model.get_tensor(self._output_details[0]["index"])[0]

        predictions = np.transpose(results, (1, 0))
        boxes = predictions[:, :4]
        scores = predictions[:, 4:]

        class_ids = np.argmax(scores, axis=1)
        confidences = np.max(scores, axis=1)

        mask = confidences > 0.25
        filtered_boxes = boxes[mask]
        filtered_confidences = confidences[mask]
        filtered_class_ids = class_ids[mask]

        boxes_xyxy = np.copy(filtered_boxes)
        boxes_xyxy[:, 0] = filtered_boxes[:, 0] - (filtered_boxes[:, 2] / 2)  # x1
        boxes_xyxy[:, 1] = filtered_boxes[:, 1] - (filtered_boxes[:, 3] / 2)  # y1
        boxes_xyxy[:, 2] = filtered_boxes[:, 0] + (filtered_boxes[:, 2] / 2)  # x2
        boxes_xyxy[:, 3] = filtered_boxes[:, 1] + (filtered_boxes[:, 3] / 2)  # y2

        boxes_xyxy[:, [0, 2]] *= instance.shape[1]
        boxes_xyxy[:, [1, 3]] *= instance.shape[0]

        boxes_nms = np.copy(boxes_xyxy)
        boxes_nms[:, 2] = boxes_xyxy[:, 2] - boxes_xyxy[:, 0]  # width
        boxes_nms[:, 3] = boxes_xyxy[:, 3] - boxes_xyxy[:, 1]  # height

        indices = cv2.dnn.NMSBoxes(
            boxes_nms.tolist(), filtered_confidences.tolist(), score_threshold=0.25, nms_threshold=0.45
        )

        if len(indices) == 0:
            return []

        return [
            Detection(
                class_id=int(filtered_class_ids[i]),
                class_name=self._class_names[int(filtered_class_ids[i])],
                box=BoundingBox(
                    xmin=float(boxes_xyxy[i][0]),
                    ymin=float(boxes_xyxy[i][1]),
                    xmax=float(boxes_xyxy[i][2]),
                    ymax=float(boxes_xyxy[i][3]),
                ),
                confidence=float(filtered_confidences[i]),
            )
            for i in np.array(indices).flatten()
        ]
