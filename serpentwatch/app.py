"""Main loop: read frames, detect, alert."""
from __future__ import annotations

import logging
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime

import cv2

from .alerts import AlertGate
from .config import Settings
from .detector import Detection, SnakeDetector
from .notifier import TelegramNotifier
from .stream import CameraStream

log = logging.getLogger(__name__)

_BOX_COLOUR = (0, 0, 255)  # BGR red


def _draw(frame, detections: list[Detection]):
    for det in detections:
        x1, y1, x2, y2 = det.box
        cv2.rectangle(frame, (x1, y1), (x2, y2), _BOX_COLOUR, 2)
        cv2.putText(frame, f"{det.label} {det.confidence:.0%}", (x1, max(y1 - 8, 16)),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, _BOX_COLOUR, 2)
    return frame


def _deliver(notifier: TelegramNotifier, jpeg: bytes, caption: str, camera: str) -> None:
    if notifier.send_photo(jpeg, caption):
        log.info("[%s] alert delivered", camera)
    else:
        log.warning("[%s] alert NOT delivered", camera)


def run(settings: Settings) -> None:
    det_cfg = settings.detection
    detector = SnakeDetector(det_cfg.model_path, det_cfg.target_labels,
                             det_cfg.confidence, det_cfg.image_size)
    notifier = TelegramNotifier(settings.telegram_token, settings.telegram_chat_id)
    if not notifier.enabled:
        log.warning("Telegram is not configured (see .env) - detections will only be logged")

    streams = {
        cam.name: CameraStream(cam.name, cam.source, det_cfg.process_every_n_frames).start()
        for cam in settings.cameras
    }
    gates = {
        name: AlertGate(det_cfg.confirm_frames, settings.alerts.cooldown_seconds)
        for name in streams
    }
    sender = ThreadPoolExecutor(max_workers=1, thread_name_prefix="telegram")

    log.info("Watching %d camera(s), analysing 1 of every %d frames. %s",
             len(streams), det_cfg.process_every_n_frames,
             "Press 'q' in a preview window to quit." if settings.show_preview else "Ctrl+C to quit.")

    try:
        while True:
            busy = False
            for name, stream in streams.items():
                frame = stream.next_frame()
                if frame is None:
                    continue
                busy = True

                detections = detector.detect(frame)
                if gates[name].update(bool(detections), time.monotonic()):
                    best = max(detections, key=lambda d: d.confidence)
                    log.warning("[%s] %s detected (%.0f%%)", name, best.label, best.confidence * 100)
                    ok, jpeg = cv2.imencode(".jpg", _draw(frame.copy(), detections),
                                            [cv2.IMWRITE_JPEG_QUALITY, 85])
                    if ok:
                        caption = (f"{settings.alerts.caption}\n"
                                   f"Camera: {name}\n"
                                   f"Confidence: {best.confidence:.0%}\n"
                                   f"Time: {datetime.now():%Y-%m-%d %H:%M:%S}")
                        sender.submit(_deliver, notifier, jpeg.tobytes(), caption, name)

                if settings.show_preview:
                    cv2.imshow(f"SerpentWatch - {name}", _draw(frame, detections))

            if settings.show_preview:
                if cv2.waitKey(1) & 0xFF == ord("q"):
                    break
            if not busy:
                time.sleep(0.01)
    except KeyboardInterrupt:
        pass
    finally:
        log.info("Shutting down...")
        for stream in streams.values():
            stream.stop()
        sender.shutdown(wait=True)
        cv2.destroyAllWindows()
