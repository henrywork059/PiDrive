"""Matched mock-Picamera2 preview operations and bounded live-loop soak.

No hardware is opened; timings include software fixture copies and encoding,
not real sensor capture, ISP load, physical controls or energy.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import statistics
import sys
import threading
import time
from pathlib import Path
from unittest.mock import patch

import cv2
import numpy as np
import psutil
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "PiServer"))
from piserver.services import camera_service as cm


class FixtureCamera:
    def __init__(self, rgb, plane):
        self.image = Image.fromarray(rgb)
        self.plane = plane
        self.config = {}
        self.started = False
        self.closed = False
        self.requests = self.releases = self.active = self.peak_active = 0
        self.main_reads = self.lores_reads = 0

    def create_video_configuration(self, **kwargs):
        return kwargs

    def configure(self, config):
        self.config = config

    def stream_configuration(self, name):
        return {**self.config[name], "stride": self.plane.shape[1]}

    def start(self):
        self.started = True

    def stop(self):
        self.started = False

    def close(self):
        self.closed = True

    def set_controls(self, controls):
        pass

    def capture_request(self):
        if not self.started or self.active:
            raise RuntimeError("Overlapping or stopped mock request")
        self.requests += 1
        self.active += 1
        self.peak_active = max(self.peak_active, self.active)
        return FixtureRequest(self)


class FixtureRequest:
    def __init__(self, camera):
        self.camera = camera
        self.released = False

    def make_image(self, name):
        assert name == "main" and not self.released
        self.camera.main_reads += 1
        return self.camera.image.copy()

    def make_array(self, name):
        assert name == "lores" and not self.released
        self.camera.lores_reads += 1
        return self.camera.plane.copy()

    def release(self):
        assert not self.released
        self.released = True
        self.camera.active -= 1
        self.camera.releases += 1


def fixture():
    rgb = np.random.default_rng(27).integers(0, 256, (240, 426, 3), dtype=np.uint8)
    small = cv2.resize(rgb, (320, 180), interpolation=cv2.INTER_AREA)
    flat = cv2.cvtColor(small, cv2.COLOR_RGB2YUV_I420).ravel()
    ylen = 320 * 180
    clen = ylen // 4
    planes = (flat[:ylen].reshape(180, 320), flat[ylen:ylen+clen].reshape(90, 160),
              flat[ylen+clen:].reshape(90, 160))
    padded = np.concatenate([np.pad(p, ((0, 0), (0, s-p.shape[1])), constant_values=255).ravel()
                             for p, s in zip(planes, (384, 192, 192))]).reshape(270, 384)
    return rgb, padded


def start_service(source, rgb, plane):
    service = cm.CameraService(width=426, height=240, fps=20)
    service.apply_settings({"preview_source": source, "preview_stream_width": 320}, restart=False)
    service.set_processing_enabled(True)
    fake = FixtureCamera(rgb, plane)
    with patch.object(cm, "Picamera2", lambda: fake):
        ok, reason = service._open_picamera2_locked()
    assert ok, reason
    assert service.get_config()["preview_stream_active"] == source
    return service, fake


def assert_retired(fake):
    assert fake.requests == fake.releases and fake.active == 0
    assert fake.peak_active == 1 and fake.closed and not fake.started


def operations(source, rgb, plane, count):
    service, fake = start_service(source, rgb, plane)
    expected = np.ascontiguousarray(rgb[:, :, ::-1])
    cpu, wall, sizes = [], [], []
    try:
        for i in range(count + 10):
            c0, w0 = time.process_time_ns(), time.perf_counter_ns()
            raw, jpeg, live, error = service._capture_picamera_request(True, True)
            c1, w1 = time.process_time_ns(), time.perf_counter_ns()
            assert live and jpeg, error
            np.testing.assert_array_equal(raw, expected)
            if i >= 10:
                cpu.append((c1-c0)/1e6)
                wall.append((w1-w0)/1e6)
                sizes.append(len(jpeg))
        decoded = cv2.imdecode(np.frombuffer(jpeg, dtype=np.uint8), 1)
        assert decoded.shape == ((180, 320, 3) if source == "lores" else (240, 426, 3))
    finally:
        service.close()
    assert_retired(fake)
    return {"cpu_ms_per_request": statistics.mean(cpu), "wall_p95_ms": float(np.percentile(wall, 95)),
            "jpeg_bytes": statistics.median(sizes), "requests": fake.requests, "releases": fake.releases,
            "raw_sha256": hashlib.sha256(expected.tobytes()).hexdigest(), "preview_shape": list(decoded.shape),
            "main_reads": fake.main_reads, "lores_reads": fake.lores_reads}


def soak(source, rgb, plane, duration):
    service, fake = start_service(source, rgb, plane)
    expected = np.ascontiguousarray(rgb[:, :, ::-1])
    process = psutil.Process()
    samples, ages = [], []
    seq, received, verified = 0, 0, 0
    cpu0, wall0 = time.process_time(), time.monotonic()
    # This is the real capture loop with a mock backend, not a hardware start/lease.
    service._running = True
    service._thread = threading.Thread(target=service._loop, daemon=True)
    try:
        with patch.object(service, "_open_backend_locked", side_effect=AssertionError("Unexpected camera reopen")):
            service._thread.start()
            while time.monotonic()-wall0 < duration:
                jpeg, new_seq = service.wait_for_jpeg(seq, timeout=.5)
                if jpeg is not None and new_seq > seq:
                    received += 1
                    seq = new_seq
                    raw, captured = service.get_raw_frame_sample()
                    if raw is not None:
                        np.testing.assert_array_equal(raw, expected)
                        verified += 1
                    stats = service.get_preview_delivery_stats()
                    assert stats["max_pending_frames"] == 1
                    ages.append(stats["latest_age_s"])
                samples.append({"seconds": time.monotonic()-wall0, "rss_bytes": process.memory_info().rss})
                time.sleep(.2)  # Deliberately slower than preview production.
            assert service._thread.is_alive(), "Capture loop terminated during soak"
    finally:
        service.close()
    assert_retired(fake)
    stats = service.get_preview_delivery_stats()
    assert received > 0 and verified > 0 and stats["subscriber_skipped_frames"] > 0
    assert stats["scheduled_preview_attempts"] == stats["published_frames"] + stats["scheduled_preview_misses"]
    assert stats["scheduled_preview_misses"] == 0
    elapsed = time.monotonic()-wall0
    return {"duration_s": elapsed, "cpu_s": time.process_time()-cpu0, "requests": fake.requests,
            "releases": fake.releases, "received": received, "verified_raw_frames": verified,
            "preview_age_p95_ms": float(np.percentile(ages, 95))*1000,
            "peak_rss_bytes": max(s["rss_bytes"] for s in samples), "rss_samples": samples,
            "delivery": stats, "main_reads": fake.main_reads, "lores_reads": fake.lores_reads}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--seconds", type=float, default=60)
    p.add_argument("--rounds", type=int, default=5)
    p.add_argument("--requests", type=int, default=150)
    p.add_argument("--output", type=Path, required=True)
    args = p.parse_args()
    if not 5 <= args.seconds <= 3600 or not 5 <= args.rounds <= 20 or not 20 <= args.requests <= 10000:
        p.error("seconds 5..3600, rounds 5..20, requests 20..10000 required")
    rgb, plane = fixture()
    results = {"main": [], "lores": []}
    for i in range(args.rounds):
        for source in (("main", "lores") if i % 2 == 0 else ("lores", "main")):
            results[source].append(operations(source, rgb, plane, args.requests))
    assert len({row["raw_sha256"] for rows in results.values() for row in rows}) == 1
    report = {"scope": "mock request/software encode; optional preview dimensions differ, no hardware energy",
              "seed": 27, "numpy": np.__version__, "opencv": cv2.__version__, "operations": results,
              "summary": {key: {metric: statistics.median(row[metric] for row in rows)
                               for metric in ("cpu_ms_per_request", "wall_p95_ms", "jpeg_bytes")}
                          for key, rows in results.items()},
              "soak": {source: soak(source, rgb, plane, args.seconds) for source in ("main", "lores")},
              "physical_acceptance": False}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2)+"\n", encoding="utf-8")
    print(json.dumps(report["summary"], indent=2))


if __name__ == "__main__":
    main()
