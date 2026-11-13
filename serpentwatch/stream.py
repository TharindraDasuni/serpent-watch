"""Background camera reader with built-in frame skipping and auto-reconnect."""
from __future__ import annotations

import logging
import threading

import cv2

log = logging.getLogger(__name__)


def describe_source(source: str | int) -> str:
    """Printable form of a source with any URL credentials hidden."""
    if isinstance(source, int):
        return f"webcam #{source}"
    if "@" in source and "://" in source:
        scheme, rest = source.split("://", 1)
        return f"{scheme}://***@{rest.rsplit('@', 1)[1]}"
    return source


class CameraStream:
    """Continuously drains a camera on its own thread.

    Frame skipping happens here: every frame is *grabbed* (which keeps RTSP
    buffers empty so the picture never lags), but only every Nth frame is
    *retrieved* (decoded to a BGR array) and offered to the detector.
    """

    def __init__(self, name: str, source: str | int, keep_every: int, retry_seconds: float = 5.0):
        self.name = name
        self._source = source
        self._keep_every = max(1, keep_every)
        self._retry_seconds = retry_seconds

        self._lock = threading.Lock()
        self._frame = None
        self._version = 0
        self._consumed = 0
        self._halt = threading.Event()
        self._worker = threading.Thread(target=self._loop, name=f"reader-{name}", daemon=True)

    def start(self) -> "CameraStream":
        self._worker.start()
        return self

    def stop(self) -> None:
        self._halt.set()
        self._worker.join(timeout=3)

    def next_frame(self):
        """Return the newest unprocessed frame, or None if nothing new arrived."""
        with self._lock:
            if self._version == self._consumed:
                return None
            self._consumed = self._version
            return self._frame

    def _connect(self):
        capture = cv2.VideoCapture(self._source)
        if not capture.isOpened():
            capture.release()
            return None
        capture.set(cv2.CAP_PROP_BUFFERSIZE, 1)  # honoured by some backends only
        return capture

    def _loop(self) -> None:
        capture = None
        seen = 0
        while not self._halt.is_set():
            if capture is None:
                capture = self._connect()
                if capture is None:
                    log.warning("[%s] cannot open %s - retrying in %.0fs",
                                self.name, describe_source(self._source), self._retry_seconds)
                    self._halt.wait(self._retry_seconds)
                    continue
                log.info("[%s] connected to %s", self.name, describe_source(self._source))
                seen = 0

            if not capture.grab():
                log.warning("[%s] stream lost - reconnecting", self.name)
                capture.release()
                capture = None
                self._halt.wait(self._retry_seconds)
                continue

            seen += 1
            if seen % self._keep_every:
                continue  # skipped frame: no decode, no inference

            ok, frame = capture.retrieve()
            if ok:
                with self._lock:
                    self._frame = frame
                    self._version += 1

        if capture is not None:
            capture.release()
