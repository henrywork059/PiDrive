# video_stream.py
"""Provides MJPEG generator for Flask response and exposes FPS estimate."""

import time

_fps_info = {
    "last_frame_time": None,   # time of last frame sent
    "fps": 0.0,                # smoothed fps estimate
}


def mjpeg_generator(camera):
    """Yield MJPEG frames from the given camera and update FPS estimate."""
    global _fps_info

    while True:
        frame = camera.get_jpeg_frame()
        if frame is None:
            time.sleep(0.05)
            continue

        now = time.time()
        fi = _fps_info

        # FPS estimate:
        # The old implementation used a 1-second bucket counter.
        # That can look "wrong" on small screens / slow networks because
        # the bucket update is jumpy and depends on browser buffering.
        # Here we use an exponential moving average of instantaneous FPS.
        last = fi["last_frame_time"]
        fi["last_frame_time"] = now
        if last is not None:
            dt = now - last
            if dt > 1e-6:
                inst = 1.0 / dt
                alpha = 0.18  # smoothing factor (higher = more responsive)
                prev = fi["fps"]
                fi["fps"] = inst if prev <= 0.0 else (prev * (1.0 - alpha) + inst * alpha)

        yield (
            b"--frame\r\n"
            b"Content-Type: image/jpeg\r\n\r\n" +
            frame +
            b"\r\n"
        )


def get_fps():
    return _fps_info["fps"]
