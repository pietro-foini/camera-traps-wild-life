import logging
import os
from typing import Any

import cv2
import numpy as np
from ai_edge_litert.interpreter import Interpreter

from camera_traps.data import ClassifierClasses
from camera_traps.models.domain import Predictor
from camera_traps.models.schemas import Classification


class TFLiteImageClassifier(Predictor):
    """TFLite Image Classifier."""

    def __init__(self, img_size: tuple[int, int]) -> None:
        super().__init__()

        self.img_size = img_size
        self._class_names = tuple(ClassifierClasses)
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
        prediction_input = prediction_input.astype(np.float32)

        return np.expand_dims(prediction_input, axis=0)

    def predict(self, instance: np.ndarray, top: int = 1, **kwargs: Any) -> list[Classification]:
        """Run image classification."""

        prediction_input = self.preprocess(instance)

        self._model.set_tensor(self._input_details[0]["index"], prediction_input)
        self._model.invoke()

        results = self._model.get_tensor(self._output_details[0]["index"])[0]

        return [
            Classification(
                class_id=int(idx),
                class_name=self._class_names[int(idx)],
                confidence=results[idx],
            )
            for idx in np.argsort(results)[-top:][::-1]
        ]
