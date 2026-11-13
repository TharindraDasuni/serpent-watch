<div align="center">

# 🐍 SerpentWatch

**Offline, privacy-first snake detection for webcams and CCTV — with instant Telegram photo alerts.**

<sub>Created by <b>Tharindra Dasuni</b></sub>

![Python](https://img.shields.io/badge/python-3.9%2B-blue)
![YOLOv8](https://img.shields.io/badge/model-YOLOv8-orange)
![Runs offline](https://img.shields.io/badge/inference-100%25%20local-brightgreen)
![License](https://img.shields.io/badge/license-MIT-green)

</div>

SerpentWatch watches your camera feeds, runs a YOLOv8 model **on your own hardware**, and sends you a photo
the moment a snake shows up. No cloud AI, no subscriptions, no video leaving your network.
It is light enough for a Raspberry Pi or a mini PC thanks to configurable **frame skipping**.

> ⚠️ **Safety notice:** SerpentWatch is a convenience tool, not a safety system. Detection can miss snakes
> or raise false alarms. Never rely on it alone where venomous snakes are a danger.

## ✨ Features

- 🔒 **Local inference** – video is analysed on-device; nothing is uploaded for processing
- 📷 **Webcam + CCTV (RTSP)** – any number of cameras, configured in one YAML file
- ⚡ **Frame skipping** – analyse 1 of every *N* frames to cut CPU load
- 📲 **Telegram alerts** – annotated snapshot with camera name, confidence and time
- 🛡️ **Fewer false alarms** – multi-frame confirmation plus a per-camera cooldown
- 🔁 **Self-healing streams** – automatic reconnect when a camera drops
- 🖥️ **Headless mode** – runs happily on a Pi over SSH or as a system service

## 🔐 Privacy by design

| What | Where it happens |
|---|---|
| Video capture and AI detection | On your device only |
| Frames with no snake | Analysed in memory and discarded – never saved, never sent |
| Alert snapshot | Held in memory (not written to disk) and sent **only** to your own Telegram bot |
| Camera passwords and bot token | Stored in a local `.env` file that is Git-ignored |
| Logs | Camera credentials are masked; the bot token is never logged |

Be aware that Telegram bot chats are not end-to-end encrypted, so an alert photo is visible to Telegram.
If that matters for your setup, run in log-only mode (leave the Telegram variables empty) or fork the notifier.

## 🧩 How it works

```mermaid
flowchart LR
    A[Webcam / RTSP camera] --> B[Reader thread<br/>grab every frame,<br/>decode every Nth]
    B --> C[YOLOv8 detector<br/>local]
    C --> D{Snake in N<br/>consecutive checks?}
    D -- no --> B
    D -- yes, outside cooldown --> E[Annotated snapshot<br/>in memory]
    E --> F[Telegram Bot API]
```

## 🚀 Quick start

### 1. Install

```bash
git clone https://github.com/<your-username>/serpent-watch.git
cd serpent-watch

python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 2. ⚠️ Important setup step — download the model

> [!IMPORTANT]
> The model file **`snake_model.pt` is not included in this repository** because it is too large for the main repo.
> You must download it **before running the application**:
>
> 1. Open the project's [**Releases**](../../releases) page on GitHub.
> 2. Download **`snake_model.pt`** from the latest release.
> 3. Place it **directly inside the `models/` folder**, so the final path is `models/snake_model.pt`.

```text
serpent-watch/
└── models/
    └── snake_model.pt     <- put the downloaded file here
```

If the file is missing or in the wrong place, SerpentWatch will stop at startup with a "Model file not found" message.
The model is by **dheerajc8073** and is used under the MIT License – see [Credits](#-credits--acknowledgements).

### 3. Create a Telegram bot

1. In Telegram, chat with **@BotFather**, send `/newbot`, and copy the **token** it gives you.
2. Send any message to your new bot.
3. Open `https://api.telegram.org/bot<YOUR_TOKEN>/getUpdates` in a browser and find `"chat":{"id": ...}` – that number is your **chat id**.

### 4. Configure

```bash
cp .env.example .env               # Windows: copy .env.example .env
```

Edit `.env`:

```ini
TELEGRAM_BOT_TOKEN=123456:your-token
TELEGRAM_CHAT_ID=123456789
```

### 5. Run

```bash
python -m serpentwatch                      # uses ./config.yaml
python -m serpentwatch --no-preview         # headless
python -m serpentwatch -c /path/to/other.yaml
```

Press **q** in a preview window (or **Ctrl+C**) to stop.

## 📹 Connecting CCTV / IP cameras (RTSP)

Add cameras to `config.yaml`. Use `${NAME}` placeholders and keep the real values in `.env`:

```yaml
cameras:
  - name: front-garden
    source: "rtsp://${CCTV_USER}:${CCTV_PASSWORD}@192.168.1.64:554/Streaming/Channels/102"
  - name: webcam
    source: 0
```

```ini
# .env
CCTV_USER=viewer
CCTV_PASSWORD=my%40password      # URL-encode special characters: @ becomes %40
```

Typical RTSP paths (**these vary by model and firmware – check your camera's manual**):

| Brand | Example URL |
|---|---|
| Hikvision | `rtsp://user:pass@IP:554/Streaming/Channels/101` (`102` = sub-stream) |
| Dahua / Amcrest | `rtsp://user:pass@IP:554/cam/realmonitor?channel=1&subtype=1` |
| Reolink | `rtsp://user:pass@IP:554/h264Preview_01_sub` |
| TP-Link Tapo | `rtsp://user:pass@IP:554/stream2` |

**Tips:** use the camera's *sub-stream* (lower resolution) – it is far cheaper to decode and is plenty for
detection. Create a dedicated read-only camera user rather than your admin account. RTSP is forced over TCP for stability.

## ⚙️ Configuration reference

| Setting | Default | What it does |
|---|---|---|
| `detection.process_every_n_frames` | `5` | **Frame skipping.** Analyse 1 of every N frames. Raise it to save CPU |
| `detection.image_size` | `640` | Inference resolution. `320` is much lighter, at some cost in small-snake accuracy |
| `detection.confidence` | `0.15` | Minimum confidence. Raise it if you get false alarms |
| `detection.confirm_frames` | `2` | Consecutive *analysed* frames that must contain a snake before alerting |
| `detection.target_labels` | `[snake]` | Model class names that trigger alerts |
| `alerts.cooldown_seconds` | `60` | Minimum gap between alerts per camera |
| `display.preview` | `true` | Show live windows with detection boxes |

## 🍓 Running on a Raspberry Pi / mini PC

- Use a 64-bit OS and a recent Pi (4 or 5 recommended).
- Start with: `process_every_n_frames: 8`, `image_size: 320`, `preview: false`, and the camera **sub-stream**.
- Tune on your own hardware – raise skipping until CPU usage is comfortable, lower it if detections arrive too late.
- Optionally export the model to a lighter runtime (for example `yolo export model=models/snake_model.pt format=ncnn`)
  and point `model_path` at the exported folder.

Run on boot with systemd (`/etc/systemd/system/serpentwatch.service`):

```ini
[Unit]
Description=SerpentWatch
After=network-online.target

[Service]
User=pi
WorkingDirectory=/home/pi/serpent-watch
ExecStart=/home/pi/serpent-watch/.venv/bin/python -m serpentwatch --no-preview
Restart=on-failure

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl enable --now serpentwatch
```

## 🗂️ Project layout

```
serpent-watch/
├── serpentwatch/
│   ├── __main__.py     # CLI entry point
│   ├── app.py          # main loop
│   ├── config.py       # YAML + .env loading and validation
│   ├── stream.py       # threaded camera reader, frame skipping, reconnect
│   ├── detector.py     # YOLOv8 wrapper
│   ├── alerts.py       # confirmation + cooldown logic
│   └── notifier.py     # Telegram sender
├── tests/
├── models/             # put snake_model.pt here (not committed)
├── config.yaml
├── .env.example
└── requirements.txt
```

## 🛠️ Troubleshooting

| Problem | Try |
|---|---|
| `Cannot open ... retrying` for RTSP | Test the URL in VLC; check IP, port, path, and URL-encode the password |
| Grey or smeared frames | Lower the camera bitrate, or use a wired connection |
| High CPU | Raise `process_every_n_frames`, lower `image_size`, disable preview |
| Too many false alarms | Raise `confidence` or `confirm_frames` |
| No Telegram message | Message your bot first, then re-check token and chat id in `.env` |

## 🤝 Contributing

Issues and pull requests are welcome. Please run `pytest` before submitting.
Ideas: more notifiers (email, Matrix, ntfy), motion pre-filtering, ONNX/NCNN presets, a Docker image.

## 👤 Author

**Tharindra Dasuni** – creator and maintainer of SerpentWatch.

## 🙏 Credits & acknowledgements

SerpentWatch stands on the work of many others. Thank you to:

| Project / service | Used for | Licence |
|---|---|---|
| [Snake detection model](https://github.com/dheerajc8073/snake-detections-) by [dheerajc8073](https://github.com/dheerajc8073) | Trained `snake_model.pt` weights | MIT |
| [Ultralytics YOLOv8](https://github.com/ultralytics/ultralytics) | Object-detection model and training framework | AGPL-3.0 |
| [OpenCV](https://opencv.org) | Camera capture, RTSP decoding, image drawing | Apache-2.0 |
| [Requests](https://github.com/psf/requests) | Sending alerts over HTTPS | Apache-2.0 |
| [PyYAML](https://github.com/yaml/pyyaml) | Reading `config.yaml` | MIT |
| [python-dotenv](https://github.com/theskumar/python-dotenv) | Loading secrets from `.env` | BSD-3-Clause |
| [Telegram Bot API](https://core.telegram.org/bots/api) | Delivering photo alerts (subject to Telegram's terms) | Telegram service terms |
| [Shields.io](https://shields.io) | README badges | – |

**Model.** Snake detection model provided by [dheerajc8073](https://github.com/dheerajc8073)
under the MIT License – [snake-detections-](https://github.com/dheerajc8073/snake-detections-/tree/main).
Thank you for sharing your work. The model keeps its original MIT licence and copyright notice; if you redistribute
the weights, include the licence text from the original repository alongside them.

**Training data.** For details of the dataset and its licences, please see the model author's repository.

Licences of third-party packages are those of their respective owners; please review them when redistributing.

## 📄 License

Copyright © 2026 **Tharindra Dasuni**. SerpentWatch is released under the **MIT License** (see `LICENSE`).

Third-party components keep their own licences: the model weights are by dheerajc8073 (MIT), and Ultralytics YOLOv8 is
licensed under AGPL-3.0. Please review their terms before redistributing SerpentWatch or using it in a product or service.
