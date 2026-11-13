"""Load and validate settings from config.yaml plus the .env file."""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

import yaml
from dotenv import load_dotenv


class ConfigError(ValueError):
    """Raised when the configuration is missing or invalid."""


@dataclass(frozen=True)
class CameraSpec:
    name: str
    source: str | int  # int = local webcam index, str = RTSP/HTTP URL or file path


@dataclass(frozen=True)
class DetectionSpec:
    model_path: Path
    target_labels: tuple[str, ...]
    confidence: float
    image_size: int
    process_every_n_frames: int
    confirm_frames: int


@dataclass(frozen=True)
class AlertSpec:
    cooldown_seconds: float
    caption: str


@dataclass(frozen=True)
class Settings:
    cameras: tuple[CameraSpec, ...]
    detection: DetectionSpec
    alerts: AlertSpec
    show_preview: bool
    telegram_token: str
    telegram_chat_id: str


def load_settings(config_path: str | Path = "config.yaml") -> Settings:
    path = Path(config_path)
    if not path.is_file():
        raise ConfigError(f"Config file not found: {path}")

    base_dir = path.resolve().parent
    load_dotenv(base_dir / ".env")  # secrets live next to config.yaml

    with path.open(encoding="utf-8") as handle:
        raw = yaml.safe_load(handle) or {}
    if not isinstance(raw, dict):
        raise ConfigError("config.yaml must contain a mapping at the top level")

    det = raw.get("detection") or {}
    alerts = raw.get("alerts") or {}
    display = raw.get("display") or {}

    model_path = (base_dir / str(det.get("model_path", "models/snake_model.pt"))).resolve()
    if not model_path.is_file():
        raise ConfigError(
            f"Model file not found: {model_path}\n"
            "Download snake_model.pt (see README) and place it in the models/ folder."
        )

    labels = det.get("target_labels", ["snake"])
    if not isinstance(labels, list) or not labels:
        raise ConfigError("'target_labels' must be a non-empty list")

    confidence = det.get("confidence", 0.15)
    if not isinstance(confidence, (int, float)) or not 0 < confidence < 1:
        raise ConfigError(f"'confidence' must be between 0 and 1 (got {confidence!r})")

    return Settings(
        cameras=_parse_cameras(raw.get("cameras")),
        detection=DetectionSpec(
            model_path=model_path,
            target_labels=tuple(str(label).strip().lower() for label in labels),
            confidence=float(confidence),
            image_size=_whole_number(det, "image_size", 640, minimum=32),
            process_every_n_frames=_whole_number(det, "process_every_n_frames", 5),
            confirm_frames=_whole_number(det, "confirm_frames", 2),
        ),
        alerts=AlertSpec(
            cooldown_seconds=float(alerts.get("cooldown_seconds", 60)),
            caption=str(alerts.get("caption", "Snake detected!")),
        ),
        show_preview=bool(display.get("preview", True)),
        telegram_token=os.getenv("TELEGRAM_BOT_TOKEN", "").strip(),
        telegram_chat_id=os.getenv("TELEGRAM_CHAT_ID", "").strip(),
    )


def _whole_number(section: dict, key: str, default: int, minimum: int = 1) -> int:
    value = section.get(key, default)
    if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
        raise ConfigError(f"'{key}' must be a whole number >= {minimum} (got {value!r})")
    return value


def _parse_cameras(entries) -> tuple[CameraSpec, ...]:
    if not isinstance(entries, list) or not entries:
        raise ConfigError("Define at least one camera under 'cameras:' in config.yaml")

    cameras: list[CameraSpec] = []
    used_names: set[str] = set()
    for index, entry in enumerate(entries, start=1):
        if not isinstance(entry, dict) or "source" not in entry:
            raise ConfigError(f"Camera #{index} needs a 'source' value")
        name = str(entry.get("name") or f"camera-{index}")
        if name in used_names:
            raise ConfigError(f"Duplicate camera name: {name!r}")
        used_names.add(name)
        cameras.append(CameraSpec(name=name, source=_resolve_source(entry["source"], name)))
    return tuple(cameras)


def _resolve_source(value, camera_name: str) -> str | int:
    """Expand ${ENV_VARS} so camera passwords can stay in .env."""
    if isinstance(value, int) and not isinstance(value, bool):
        return value
    text = os.path.expandvars(str(value).strip())
    if "${" in text:
        raise ConfigError(
            f"Camera {camera_name!r}: an environment variable used in 'source' is not set. "
            "Add it to your .env file."
        )
    return int(text) if text.isdigit() else text
