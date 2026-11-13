"""SerpentWatch - offline, privacy-first snake detection for webcams and CCTV."""
import os

# Force RTSP over TCP: avoids the smeared/grey frames UDP produces on lossy Wi-Fi.
# Must be set before OpenCV opens its first capture, hence it lives here.
os.environ.setdefault("OPENCV_FFMPEG_CAPTURE_OPTIONS", "rtsp_transport;tcp")

__version__ = "1.0.0"
__author__ = "Tharindra Dasuni"
