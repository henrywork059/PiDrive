# piCar_0_1_13

Base: piCar_0_1_11

Changes:
- Replaced camera.py with a more robust implementation that:
  - Tries /dev/video0–/dev/video3 using both CAP_V4L2 and default backend.
  - Keeps the latest frame in a background thread.
  - Exposes get_latest_frame() and get_jpeg_frame() for the web UI and autopilot.
- Designed for Raspberry Pi OS Bookworm with OV5647 + libcamera V4L2 bridge.

Notes:
- If you still see `[CAMERA] ERROR: No usable video device found (idx 0–3).`
  at runtime, ensure the rpicam-v4l2 service is enabled and running on the Pi.
