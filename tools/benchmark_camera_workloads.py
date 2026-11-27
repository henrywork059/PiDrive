#!/usr/bin/env python3
"""Matched, hardware-free camera workloads against trusted full Git revisions.

Real camera service threads, recording writers, preview multipart generators,
settings reads, frame freshness and inference preprocessing/dispatch. PiSD uses
its simulation camera; PiServer uses a deterministic fake Picamera2 request
device (no real device or motor). A copying fake TFLite interpreter isolates
runtime dispatch from model execution. Actual TCP loopback carries multipart
body bytes, not HTTP headers or packet overhead. No user configuration or
recording is accessed. Run on Linux with declared test dependencies.
"""
from __future__ import annotations

import argparse
import ast
import collections
import json
import math
import os
import platform
import re
import resource
import socket
import statistics
import subprocess
import sys
import tempfile
import threading
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CASES = {
    "idle": (0, False, False),
    "one_viewer": (1, False, False),
    "two_viewers": (2, False, False),
    "record": (0, True, False),
    "inference": (0, False, True),
    "concurrent": (2, True, True),
    "reconnect": (1, False, False),
}
SIZE = (426, 240)
FPS = 20
RECORD_FPS = 8
INFERENCE_FPS = 12


def git(*args):
    return subprocess.check_output(["git", "-C", str(ROOT), *args], text=True).strip()


def trusted(ref):
    if not re.fullmatch("[0-9a-f]{40}", ref) or git("rev-parse", ref + "^{commit}") != ref:
        raise ValueError("Use a trusted full commit SHA")
    return ref


def p95(values):
    return sorted(values)[max(0, math.ceil(.95 * len(values)) - 1)] if values else None


def extract_generator(checkout, component, camera, settings):
    # Use actual generator bodies without invoking create_app (which can open
    # hardware, start control services or touch repository-local user data).
    path = checkout / ("PiSD/pisd/app.py" if component == "PiSD" else "PiServer/piserver/app.py")
    tree = ast.parse(path.read_text(encoding="utf-8"))
    scope = {"time": time, "camera_service": camera, "settings_manager": settings}
    if component == "PiSD":
        endpoint = next(n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name == "video_feed")
        nodes = [n for n in endpoint.body if isinstance(n, ast.FunctionDef)
                 and n.name in ("_live_preview_interval", "generate")]
        assert len(nodes) == 2
        name = "generate"
    else:
        nodes = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "mjpeg_generator"]
        assert len(nodes) == 1
        name = "mjpeg_generator"
    exec(compile(ast.Module(body=nodes, type_ignores=[]), str(path), "exec"), scope)
    return scope[name] if component == "PiSD" else lambda: scope[name](camera)


def tcp_pair():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as listener:
        listener.bind(("127.0.0.1", 0))
        listener.listen(1)
        tx = socket.create_connection(listener.getsockname(), timeout=3)
        rx, _ = listener.accept()
    tx.settimeout(3)
    rx.settimeout(3)
    return tx, rx


def run_case(checkout, component, case, duration):
    import cv2
    import numpy as np
    import psutil
    from PIL import Image
    views, recording, inference = CASES[case]
    counters = collections.Counter()
    pub = {}
    local = threading.local()
    errors = []
    stop = threading.Event()
    reconnect = threading.Event()
    viewer_results = []
    infer_ages, infer_times = [], []
    rss = []
    process = psutil.Process()
    lock = threading.Lock()

    def count(name, amount=1):
        with lock:
            counters[name] += amount

    def wrap(obj, method, counter, bytes_counter=None):
        original = getattr(obj, method)
        def counted(*a, **kw):
            count(counter)
            result = original(*a, **kw)
            if bytes_counter and result is not None:
                count(bytes_counter, len(result))
            return result
        setattr(obj, method, counted)

    class MotorFixture:
        def status(self):
            return {"last_command": {"steering": .17, "throttle": .3, "steer_mix": .8},
                    "last_left": .2, "last_right": .3}
        def update(self, *args, **kwargs):
            raise AssertionError("No motor output permitted")
        def stop(self):
            raise AssertionError("No motor output permitted")

    class Interpreter:
        # Preserve the production set_tensor ownership/copy contract.
        def set_tensor(self, index, x):
            assert index == 0 and x.shape == (1, 120, 160, 3) and x.dtype == np.float32
            self.x = x.copy()
        def invoke(self):
            count("inference_invocations")
            self.y = np.array([[float(self.x.mean()) * .1, .25]], dtype=np.float32)
        def get_tensor(self, index):
            assert index == 1
            return self.y.copy()

    with tempfile.TemporaryDirectory(prefix="pidrive-camera-workload-") as tmp:
        root = Path(tmp)
        details = {"index": 0, "dtype": np.float32, "quantization": (0., 0)}
        output = {"index": 1, "dtype": np.float32, "quantization": (0., 0), "name": "steering_throttle"}
        motor = MotorFixture()
        if component == "PiSD":
            from pisd.services.camera_service import CameraService
            from pisd.services.recording_service import RecordingService
            from pisd.services.ai_drive_service import AIDriveService
            from pisd.core.settings_manager import SettingsManager
            camera = CameraService({"width": SIZE[0], "height": SIZE[1], "fps": FPS,
                                    "live_preview_fps": 60, "preview_quality": 60}, hardware_enabled=False)
            settings = SettingsManager(root / "runtime_settings.json")
            assert settings.save({"camera": {"live_preview_fps": 60}})[0]
            wrap(camera, "_make_simulated_frame", "capture_requests")
            wrap(camera, "_encode_jpeg", "preview_encode_calls", "preview_encoded_bytes")
            publish = camera._publish_frame
            def published(frame, jpeg, loop_ms):
                seq = camera.frame_seq + 1
                pub[seq] = time.monotonic()
                publish(frame, jpeg, loop_ms)
                count("preview_publications")
            camera._publish_frame = published
            wait = camera.wait_for_jpeg_frame
            def observed_wait(*a, **kw):
                result = wait(*a, **kw)
                local.seq = result[1]
                return result
            camera.wait_for_jpeg_frame = observed_wait
            recorder = RecordingService(root) if recording else None
            model = AIDriveService(root) if inference else None
            if model:
                model._backend, model._model = "tflite", Interpreter()
                model._input_details, model._output_details = [details], [output]
                model._output_names, model._input_size = [output["name"]], (160, 120)
                model._model_loaded = model._model_ready = True
        else:
            from piserver.services import camera_service as cm
            from piserver.services.recorder_service import RecorderService
            from piserver.services.model_service import ModelService
            camera = cm.CameraService(*SIZE, fps=FPS)
            # Refuse real device discovery. Only our fake request device is used.
            cm.Picamera2 = None
            cm.GPIO_AVAILABLE = False
            assert not Path("/proc/device-tree/model").exists()
            # Same seeded image across revisions. Frame identity is publication
            # sequence/timestamp, not an invented change in visual content.
            rng = np.random.default_rng(17)
            source = Image.fromarray(rng.integers(0, 256, (SIZE[1], SIZE[0], 3), dtype=np.uint8))
            class Request:
                def make_image(self, stream):
                    assert stream == "main"
                    count("request_image_extractions")
                    return source.copy()
                def release(self):
                    count("request_releases")
            class Device:
                def capture_request(self):
                    count("capture_requests")
                    return Request()
                def stop(self):
                    pass
                def close(self):
                    pass
            def open_fixture():
                camera._release_backends_locked()
                camera._picam2 = Device()
                camera.backend = "fixture_picamera2"
                camera.backend_format = "RGB"
                camera._capture_failures = 0
                camera._last_open_attempt = time.time()
            camera._open_backend_locked = open_fixture
            camera.preview_fps = 60
            camera.preview_quality = 60
            camera.set_preview_enabled(views > 0)
            camera.set_processing_enabled(recording or inference)
            settings = None
            wrap(camera, "_placeholder_frame", "placeholder_builds")
            wrap(camera, "_jpeg_from_pil", "preview_encode_calls", "preview_encoded_bytes")
            wrap(camera, "_encode_preview_jpeg_cv", "preview_encode_calls", "preview_encoded_bytes")
            publish = camera._publish_jpeg
            def published(jpeg):
                if jpeg is not None:
                    pub[camera._jpeg_seq + 1] = time.monotonic()
                publish(jpeg)
                if jpeg is not None:
                    count("preview_publications")
            camera._publish_jpeg = published
            wait = camera.wait_for_jpeg
            def observed_wait(*a, **kw):
                result = wait(*a, **kw)
                local.seq = result[1]
                return result
            camera.wait_for_jpeg = observed_wait
            recorder = RecorderService(root / "records") if recording else None
            model = ModelService(root / "models") if inference else None
            if model:
                model.interpreter = Interpreter()
                model._input_details, model._output_details = details, output
                model._input_size = (160, 120)

        generate = extract_generator(checkout, component, camera, settings)

        def viewer():
            ages, sizes, seqs = [], [], []
            duplicates, reconnects = 0, 0
            stream = generate()
            tx, rx = tcp_pair()
            try:
                while not stop.is_set():
                    if reconnect.is_set() and not reconnects:
                        stream.close()
                        stream = generate()
                        reconnects += 1
                        # Treat the first snapshot of a new connection separately.
                        previous = None
                    else:
                        previous = seqs[-1] if seqs else None
                    payload = next(stream)
                    seq = local.seq
                    assert payload.startswith(b"--frame\r\n") and b"\xff\xd8" in payload and payload.endswith(b"\xff\xd9\r\n")
                    tx.sendall(payload)
                    remaining = len(payload)
                    while remaining:
                        data = rx.recv(min(remaining, 65536))
                        if not data:
                            raise RuntimeError("TCP transfer truncated")
                        remaining -= len(data)
                    sizes.append(len(payload))
                    if previous == seq:
                        duplicates += 1
                    seqs.append(seq)
                    if seq in pub:
                        ages.append((time.monotonic() - pub[seq]) * 1000)
                    # A bounded client read cadence keeps the stopped-camera
                    # baseline's duplicate retransmits from flooding the runner.
                    stop.wait(.01)
            except Exception as exc:
                errors.append(repr(exc))
            finally:
                stream.close()
                tx.close()
                rx.close()
                viewer_results.append({"frames": len(seqs), "body_bytes": sum(sizes), "duplicate_sequences": duplicates,
                                       "reconnects": reconnects, "unique_sequences": len(set(seqs)),
                                       "freshness_p50_ms": statistics.median(ages) if ages else None,
                                       "freshness_p95_ms": p95(ages), "max_age_ms": max(ages) if ages else None})

        def consumers():
            next_record = 0.
            last_raw = None
            try:
                while not stop.is_set():
                    started = time.monotonic()
                    if component == "PiSD":
                        if model:
                            reply = model.predict_once(camera, drive=False)
                            assert reply["ok"], reply.get("message")
                            assert 0 <= reply["raw_prediction"]["steering"] <= .1
                            seq = model._last_frame_seq
                            if seq in pub:
                                infer_ages.append((time.monotonic() - pub[seq]) * 1000)
                            count("inference_requests")
                            infer_times.append((time.monotonic() - started) * 1000)
                    else:
                        frame, stamp = camera.get_raw_frame_sample()
                        if frame is not None and stamp is not None:
                            age = time.monotonic() - stamp
                            assert 0 <= age <= .75
                            if model:
                                pred = model.predict_uv_from_frame(frame)
                                assert pred is not None and 0 <= pred[0] <= .1 and pred[1] == .25
                                count("inference_requests")
                                infer_ages.append(age * 1000)
                                infer_times.append((time.monotonic() - started) * 1000)
                            if recorder and stamp != last_raw and started >= next_record:
                                recorder.maybe_record(frame, {"applied_steering": .17, "applied_throttle": .3,
                                                             "camera_width": SIZE[0], "camera_height": SIZE[1]})
                                last_raw = stamp
                                next_record = started + 1 / RECORD_FPS
                    stop.wait(max(0., 1 / INFERENCE_FPS - (time.monotonic() - started)))
            except Exception as exc:
                errors.append(repr(exc))

        # All measured work is in this process. Capture/consumer threads are
        # joined before reading CPU; no process-wide CPU percentage extrapolation.
        camera.start()
        try:
            deadline = time.monotonic() + 3
            while not counters["capture_requests"] and time.monotonic() < deadline:
                time.sleep(.005)
            assert counters["capture_requests"] > 0
            # Allow the first publication to complete before workload starts.
            time.sleep(.10)
            before = counters.copy()
            rss.append(process.memory_info().rss)
            cpu0, wall0 = time.process_time(), time.monotonic()
            if recorder:
                if component == "PiSD":
                    result = recorder.start(camera, motor, fps=RECORD_FPS)
                    assert result["ok"], result.get("message")
                else:
                    recorder.start()
                    recorder.min_interval = 1 / RECORD_FPS
            threads = [threading.Thread(target=viewer, daemon=True) for _ in range(views)]
            if model or (recorder and component == "PiServer"):
                threads.append(threading.Thread(target=consumers, daemon=True))
            for t in threads:
                t.start()
            did_reconnect = False
            while time.monotonic() - wall0 < duration:
                if case == "reconnect" and not did_reconnect and time.monotonic() - wall0 >= duration * .3:
                    camera.stop()
                    time.sleep(.18)
                    camera.start()
                    reconnect.set()
                    did_reconnect = True
                rss.append(process.memory_info().rss)
                time.sleep(.025)
            stop.set()
            for t in threads:
                t.join(3)
                assert not t.is_alive(), "consumer failed to retire"
            if recorder:
                result = recorder.stop()
                if component == "PiSD":
                    assert result["ok"], result.get("message")
            wall, cpu = time.monotonic() - wall0, time.process_time() - cpu0
            rss.append(process.memory_info().rss)
            after = counters.copy()
            assert not errors, errors
        finally:
            stop.set()
            camera.stop()
            if component == "PiSD" and model:
                model.close()

        counts = {k: after[k] - before[k] for k in set(after) | set(before)}
        counts["capture_requests"] = counts.get("capture_requests", 0)
        assert counts["capture_requests"] > 0, (component, case, counts)
        records = []
        if recorder:
            for path in root.rglob("records.jsonl"):
                records.extend(json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip())
            assert len(records) >= 2, (component, case, len(records))
            assert all(r["steering"] == .17 and r["throttle"] == .3 for r in records)
            if component == "PiSD":
                sequences = [r["source_frame_seq"] for r in records]
                assert all(a < b for a, b in zip(sequences, sequences[1:]))
                labels = sum(len(p.read_text().splitlines()) for p in root.rglob("labels.jsonl"))
                assert labels == len(records)
            jpgs = list(root.rglob("*.jpg"))
            assert len(jpgs) == len(records)
            assert all(cv2.imread(str(p)) is not None for p in jpgs)
            counts["recorded_jpeg_bytes"] = sum(p.stat().st_size for p in jpgs)
        counts["recorded_frames"] = len(records)
        counts["recording_encode_calls"] = len(records) if component == "PiServer" else 0
        if views:
            assert len(viewer_results) == views and all(v["frames"] >= 2 for v in viewer_results)
        if inference:
            assert counts.get("inference_invocations", 0) >= 2
        if component == "PiServer":
            assert counts.get("request_releases", 0) <= counts["capture_requests"] + 1
            if not views:
                assert counts.get("preview_encode_calls", 0) == 0
        if case != "reconnect" and views:
            assert counts.get("preview_encode_calls", 0) <= counts["capture_requests"] + 1
        return {"wall_s": wall, "cpu_s": cpu, "cpu_s_per_wall_s": cpu / wall,
                "cpu_ms_per_capture": 1000 * cpu / counts["capture_requests"],
                "rss_sampled_peak_bytes": max(rss), "rss_sampled_median_bytes": statistics.median(rss),
                "process_high_water_rss_bytes": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024,
                "counts": counts, "viewers": viewer_results,
                "multipart_tcp_body_bytes": sum(v["body_bytes"] for v in viewer_results),
                "inference_freshness_p50_ms": statistics.median(infer_ages) if infer_ages else None,
                "inference_freshness_p95_ms": p95(infer_ages), "inference_p95_ms": p95(infer_times)}


def worker(args):
    import contextlib
    import cv2
    import numpy
    import psutil
    import PIL
    cv2.setNumThreads(1)  # matched fixture only, not a production default change
    checkout = Path(args.checkout).resolve()
    assert git("rev-parse", args.revision + "^{commit}") == args.revision
    assert subprocess.check_output(["git", "-C", str(checkout), "rev-parse", "HEAD"], text=True).strip() == args.revision
    sys.path.insert(0, str(checkout / args.component))
    with contextlib.redirect_stdout(sys.stderr):
        cases = {case: run_case(checkout, args.component, case, args.duration) for case in CASES}
    print(json.dumps({"revision": args.revision, "component": args.component, "cases": cases,
                      "peak_process_rss_bytes": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024,
                      "versions": {"python": sys.version.split()[0], "numpy": numpy.__version__,
                                   "opencv": cv2.__version__, "pillow": PIL.__version__, "psutil": psutil.__version__}}))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base")
    parser.add_argument("--candidate")
    parser.add_argument("--rounds", type=int, default=5)
    parser.add_argument("--duration", type=float, default=1.0)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--worker", action="store_true")
    parser.add_argument("--checkout")
    parser.add_argument("--revision")
    parser.add_argument("--component", choices=["PiSD", "PiServer"])
    args = parser.parse_args()
    if args.worker:
        worker(args)
        return
    if args.rounds < 5 or args.duration < .9 or not args.output:
        parser.error("At least five paired rounds, .9 seconds per case, and --output required")
    refs = [trusted(args.base), trusted(args.candidate)]
    all_runs = {"PiSD": [[], []], "PiServer": [[], []]}
    with tempfile.TemporaryDirectory(prefix="pidrive-workload-checkouts-") as tmp:
        checkouts = [Path(tmp) / "base", Path(tmp) / "candidate"]
        try:
            for ref, checkout in zip(refs, checkouts):
                git("worktree", "add", "--detach", str(checkout), ref)
            for round_no in range(args.rounds):
                for component in all_runs:
                    for i in ((0, 1) if round_no % 2 == 0 else (1, 0)):
                        cmd = [sys.executable, str(Path(__file__).resolve()), "--worker",
                               "--checkout", str(checkouts[i]), "--revision", refs[i], "--component", component,
                               "--duration", str(args.duration)]
                        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120,
                                                env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"})
                        if result.returncode:
                            raise RuntimeError(f"Worker failed: {component} {refs[i]}\n{result.stdout}\n{result.stderr}")
                        run = json.loads(result.stdout)
                        all_runs[component][i].append(run)
                        print(f"{component} pair {round_no+1}/{args.rounds} revision {refs[i][:7]} finished", flush=True)
        finally:
            for checkout in checkouts:
                if checkout.exists():
                    git("worktree", "remove", "--force", str(checkout))
    summary = {}
    for component, pairs in all_runs.items():
        summary[component] = {}
        for case in CASES:
            summary[component][case] = {}
            for label, runs in zip(("before", "after"), pairs):
                samples = [run["cases"][case] for run in runs]
                median = lambda key: statistics.median(s[key] for s in samples)
                count_med = lambda key: statistics.median(s["counts"].get(key, 0) for s in samples)
                summary[component][case][label] = {
                    "cpu_s_per_wall_s": median("cpu_s_per_wall_s"), "cpu_ms_per_capture": median("cpu_ms_per_capture"),
                    "cpu_s": median("cpu_s"), "wall_s": median("wall_s"),
                    "sampled_peak_rss_bytes": median("rss_sampled_peak_bytes"),
                    "capture_requests": count_med("capture_requests"), "preview_encode_calls": count_med("preview_encode_calls"),
                    "placeholder_builds": count_med("placeholder_builds"), "preview_publications": count_med("preview_publications"),
                    "recorded_frames": count_med("recorded_frames"), "recording_encode_calls": count_med("recording_encode_calls"),
                    "inference_invocations": count_med("inference_invocations"),
                    "multipart_tcp_body_bytes": median("multipart_tcp_body_bytes"),
                    "duplicate_sequences": statistics.median(sum(v["duplicate_sequences"] for v in s["viewers"]) for s in samples),
                    "freshness_p95_ms": statistics.median([v["freshness_p95_ms"] for s in samples for v in s["viewers"] if v["freshness_p95_ms"] is not None]) if CASES[case][0] else None,
                    "inference_freshness_p95_ms": statistics.median([s["inference_freshness_p95_ms"] for s in samples]) if CASES[case][2] else None,
                    "whole_process_peak_rss_bytes": statistics.median(r["peak_process_rss_bytes"] for r in runs)}
    result = {"baseline": refs[0], "candidate": refs[1], "platform": platform.platform(),
              "rounds": args.rounds, "duration_target_s": args.duration, "size": SIZE,
              "target_capture_fps": FPS, "record_fps": RECORD_FPS, "inference_fps": INFERENCE_FPS,
              "note": "Fixed-duration real service workloads; counts may vary with scheduling. CPU includes all process threads. TCP multipart bodies only. Fake model, simulated camera, no physical power or control acceptance.",
              "summary": summary, "runs": all_runs}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
