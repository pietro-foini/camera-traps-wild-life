import logging
import os
from typing import Any

import cv2
import numpy as np
import tensorflow as tf

from camera_traps.data import ClassifierClasses
from camera_traps.models.domain import Predictor
from camera_traps.models.schemas import Classification


class TFImageClassifier(Predictor):
    """TensorFlow Image Classifier."""

    def __init__(self, img_size: tuple[int, int]) -> None:
        super().__init__()

        self._class_names = tuple(ClassifierClasses)
        self.img_size = img_size

    def load(self, artifact_uri: str) -> None:
        """Load model."""

        if not os.path.exists(artifact_uri):
            raise FileNotFoundError(f"Model not found: {artifact_uri}")

        gpus = tf.config.list_physical_devices("GPU")
        if gpus:
            logging.info("GPUs detected: %s", gpus)
        else:
            logging.warning("No GPU found!")

        self._model = tf.keras.models.load_model(artifact_uri)

        logging.info("Loaded model: %s", artifact_uri)

    def preprocess(self, prediction_input: np.ndarray) -> np.ndarray:
        """Preprocess image."""

        prediction_input = cv2.resize(prediction_input, self.img_size)
        prediction_input = prediction_input.astype(np.float32)

        return np.expand_dims(prediction_input, axis=0)

    def predict(self, instance: np.ndarray, top: int = 1, **kwargs: Any) -> list[Classification]:
        """Run image classification."""

        prediction_input = self.preprocess(instance)

        results = self._model.predict(prediction_input, verbose=False)[0]

        return [
            Classification(
                class_id=int(idx),
                class_name=self._class_names[int(idx)],
                confidence=results[idx],
            )
            for idx in np.argsort(results)[-top:][::-1]
        ]
