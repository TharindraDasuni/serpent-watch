"""Thin wrapper around the YOLOv8 model."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from ultralytics import YOLO


@dataclass(frozen=True)
class Detection:
    label: str
    confidence: float
    box: tuple[int, int, int, int]  # x1, y1, x2, y2 in pixels


class SnakeDetector:
    def __init__(self, model_path: Path, labels: tuple[str, ...], confidence: float, image_size: int):
        self._model = YOLO(str(model_path))
        self._labels = {label.lower() for label in labels}
        self._confidence = confidence
        self._image_size = image_size

    def detect(self, frame) -> list[Detection]:
        """Run inference on one BGR frame and return only the target classes."""
        result = self._model.predict(
            frame, conf=self._confidence, imgsz=self._image_size, verbose=False
        )[0]

        hits: list[Detection] = []
        for box in result.boxes:
            label = str(result.names[int(box.cls[0])]).strip().lower()
            if label not in self._labels:
                continue
            x1, y1, x2, y2 = (int(v) for v in box.xyxy[0].tolist())
            hits.append(Detection(label, float(box.conf[0]), (x1, y1, x2, y2)))
        return hits
