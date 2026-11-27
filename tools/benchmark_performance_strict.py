#!/usr/bin/env python3
"""Strict Update 1: longer camera trials and native Qt Data-review workloads.

Exact trusted Git revisions are checked out into temporary worktrees. Camera
trials reuse the previously qualified service fixture, one case per process.
A separate diagnostic run uses inclusive thread CPU attribution (not timed
comparisons). Trainer trials exercise real loader/filter/Qt preview/plot/image
panels and retain per-revision process RSS, action latency and semantic digests.
No user data, hardware control, dependency or production thread changes.
"""
from __future__ import annotations
import argparse
import collections
import contextlib
import functools
import hashlib
import json
import os
from pathlib import Path
import resource
import statistics
import subprocess
import sys
import tempfile
import threading
import time

import benchmark_camera_workloads as camera

CASES = {"PiSD": ("idle", "concurrent"), "PiServer": ("inference", "concurrent")}


def percentile(values):
    return camera.p95(values)


def attach_attribution(component):
    totals = collections.defaultdict(lambda: {"calls": 0, "thread_cpu_ns_inclusive": 0})
    lock = threading.Lock()
    if component == "PiSD":
        from pisd.services.camera_service import CameraService
        from pisd.services.ai_drive_service import AIDriveService
        from pisd.services.recording_service import RecordingService
        targets = [(CameraService, "_make_simulated_frame"), (CameraService, "_encode_jpeg"),
                   (CameraService, "_publish_frame"), (AIDriveService, "_predict_from_jpeg"),
                   (AIDriveService, "_prepare_input"), (RecordingService, "_save_frame_record_locked")]
    else:
        from piserver.services.camera_service import CameraService
        from piserver.services.model_service import ModelService
        from piserver.services.recorder_service import RecorderService
        targets = [(CameraService, "_capture_picamera_request"), (CameraService, "_frame_from_pil"),
                   (CameraService, "_jpeg_from_pil"), (CameraService, "_placeholder_frame"),
                   (ModelService, "predict_uv_from_frame"), (ModelService, "_prepare_input"),
                   (RecorderService, "maybe_record")]
    import cv2
    targets.append((cv2, "imwrite"))
    for owner, name in targets:
        original = getattr(owner, name)
        key = getattr(owner, "__name__", str(owner)) + "." + name
        def wrapped(*a, _fn=original, _key=key, **kw):
            start = time.thread_time_ns()
            try:
                return _fn(*a, **kw)
            finally:
                elapsed = time.thread_time_ns() - start
                with lock:
                    totals[_key]["calls"] += 1
                    totals[_key]["thread_cpu_ns_inclusive"] += elapsed
        setattr(owner, name, wrapped)
    return totals


def trainer_workload(count):
    import numpy as np
    import pandas as pd
    import psutil
    from PIL import Image
    from PySide6.QtWidgets import QApplication
    from PySide6.QtCore import Qt
    from piTrainer.services.data.record_loader_service import load_records_dataframe, build_filtered_dataframe
    from piTrainer.services.data.filter_service import filter_preview_dataframe
    from piTrainer.panels.data.preview_panel import PreviewPanel
    from piTrainer.panels.data.data_plot_panel import DataPlotPanel
    from piTrainer.panels.data.image_preview_panel import ImagePreviewPanel
    from piTrainer.utils.image_utils import clear_scaled_pixmap_cache, scaled_pixmap_cache_stats
    import PySide6
    proc = psutil.Process()
    app = QApplication.instance() or QApplication([])
    memory = {}
    elapsed = {}
    samples = []
    digests = []
    def mark(name, started):
        elapsed[name] = (time.perf_counter() - started) * 1000
        memory[name] = proc.memory_info().rss
    with tempfile.TemporaryDirectory(prefix="pidrive-strict-trainer-") as temp:
        root = Path(temp)
        # Linked images isolate metadata scaling without consuming user storage.
        # Pixel variation and orientation are fixed by index, across revisions.
        rng = np.random.default_rng(17)
        images = []
        for i in range(24):
            path = root / f"base{i}.jpg"
            Image.fromarray(rng.integers(0,256,(240,426,3),dtype=np.uint8)).save(path, quality=75)
            images.append(path)
        sessions = ["20260101_120000_manual_a", "20260102_120000_manual_b"]
        for session_no, name in enumerate(sessions):
            folder = root / name
            frames = folder / "frames"
            frames.mkdir(parents=True)
            with (folder / "labels.jsonl").open("w", encoding="utf-8") as f:
                for i in range(count // 2):
                    image = f"frame_{i:06d}.jpg"
                    os.link(images[(i+session_no)%len(images)], frames/image)
                    row = {"frame_id": f"f{i:06d}", "frame": "frames/"+image,
                           "ts": f"2026-01-0{session_no+1}T12:00:{i%60:02d}Z",
                           "mode": "ai" if i%5==0 else "manual",
                           "steering": (i%21-10)/10, "throttle": (i%11)/10,
                           "source_frame_seq": i+1, "source_frame_bytes": images[(i+session_no)%len(images)].stat().st_size,
                           "cam_w":426,"cam_h":240,"format":"BGR888","overlay_settings":{"path_preview":True}}
                    f.write(json.dumps(row)+"\n")
        clear_scaled_pixmap_cache()
        memory["after_fixture"] = proc.memory_info().rss
        cpu0 = time.process_time()
        started = time.perf_counter()
        df = load_records_dataframe(root, sessions)
        assert len(df)==count
        mark("load", started)
        started=time.perf_counter()
        filtered = build_filtered_dataframe(df, True)
        assert len(filtered)==sum(1 for i in range(count//2) if i%5!=0)*2
        mark("filter", started)
        started=time.perf_counter()
        review = filter_preview_dataframe(filtered)
        image = ImagePreviewPanel()
        image.resize(960,540)
        table = PreviewPanel(selection_callback=image.set_record)
        table.resize(960,540)
        plot = DataPlotPanel()
        plot.resize(960,540)
        # Real panels, offscreen. Process pending paints and render the current
        # image synchronously to measure review work, not debounce delay.
        def render_selected():
            app.processEvents()
            image.selection_render_timer.stop()
            image.resize_render_timer.stop()
            image._render_preview()
            assert image.image_label._pixmap is not None
            assert not image.image_label._pixmap.isNull()
        table.set_dataframe(review)
        plot.set_dataframe(review)
        plot.canvas.draw()
        render_selected()
        mark("initial_review", started)
        # Each action validates source identity and includes native image render.
        for j in range(48):
            start = time.perf_counter()
            if j in (0,16,32):
                source = (j*613+len(review)//3)%len(review)
                record = review.iloc[source].to_dict()
                assert table.select_record_identity(table.record_identity(record))
            else:
                assert table.select_adjacent_record(1)
            render_selected()
            record = table.selected_record()
            assert table.record_identity(record)==table.record_identity(image.current_record)
            digests.append((record["session"],record["frame_id"],float(record["steering"]),float(record["throttle"])))
            samples.append((time.perf_counter()-start)*1000)
        mark("navigation", started)
        # Filter/rebuild/sort as on the Data workspace, with all original rows
        # and metadata retained in memory. Validate selected identity after sort.
        rebuild = []
        for low, high in ((.2,.8),(.0,1.0),(.4,.9)):
            start=time.perf_counter()
            subset=filter_preview_dataframe(filtered,speed_range=(low,high))
            table.set_dataframe(subset)
            plot.set_dataframe(subset)
            plot.canvas.draw()
            render_selected()
            record=table.selected_record()
            identity=table.record_identity(record)
            table.model.sort(table.model.columns.index("steering"),Qt.DescendingOrder)
            assert table.record_identity(table.selected_record())==identity
            rebuild.append((time.perf_counter()-start)*1000)
            digests.append((len(subset),identity[:3]))
        memory["after_navigation_and_filters"]=proc.memory_info().rss
        cache=scaled_pixmap_cache_stats()
        result={"rows":count,"filtered_rows":len(filtered),"stage_ms":elapsed,"stage_rss_bytes":memory,
                "cpu_s":time.process_time()-cpu0,
                "peak_rss_bytes":resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,
                "review_action_p95_ms":percentile(samples),"review_action_ms":samples,
                "rebuild_p95_ms":percentile(rebuild),"rebuild_ms":rebuild,
                "cache":cache,"semantic_sha256":hashlib.sha256(json.dumps(digests,sort_keys=True).encode()).hexdigest(),
                "versions":{"pandas":pd.__version__,"numpy":np.__version__,"qt":PySide6.__version__}}
        table.close();image.close();plot.close()
        clear_scaled_pixmap_cache()
        return result


def worker(args):
    checkout=Path(args.checkout).resolve()
    assert subprocess.check_output(["git","-C",str(checkout),"rev-parse","HEAD"],text=True).strip()==args.revision
    sys.path.insert(0,str(checkout/args.component))
    with contextlib.redirect_stdout(sys.stderr):
        if args.component=="piTrainer":
            result=trainer_workload(args.rows)
        else:
            import cv2
            cv2.setNumThreads(1)
            attribution=attach_attribution(args.component) if args.attribute else None
            result=camera.run_case(checkout,args.component,args.case,args.duration)
            if attribution is not None:
                result["inclusive_thread_cpu_attribution"]=dict(attribution)
    print(json.dumps(result))


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--base");p.add_argument("--prior");p.add_argument("--candidate")
    p.add_argument("--kind",choices=("camera","trainer"),default="camera")
    p.add_argument("--rounds",type=int,default=5);p.add_argument("--duration",type=float,default=8)
    p.add_argument("--rows",type=int,default=30000);p.add_argument("--output",type=Path)
    p.add_argument("--worker",action="store_true");p.add_argument("--checkout");p.add_argument("--revision")
    p.add_argument("--component");p.add_argument("--case");p.add_argument("--attribute",action="store_true")
    args=p.parse_args()
    if args.worker:
        worker(args);return
    if args.rounds<5 or args.duration<5 or args.rows<10000 or args.rows%2 or not args.output:
        p.error("Need five pairs, >=5-second camera trials, even >=10k trainer rows, output")
    refs=[camera.trusted(args.base),camera.trusted(args.candidate)]
    if args.kind=="trainer":
        refs.insert(1,camera.trusted(args.prior))
    result={"revisions":refs,"kind":args.kind,"rounds":args.rounds,
            "duration_target_s":args.duration,"rows":args.rows,"runs":{},"attribution":{}}
    with tempfile.TemporaryDirectory(prefix="pidrive-strict-checkout-") as temp:
        checkouts=[Path(temp)/str(i) for i in range(len(refs))]
        try:
            for ref,checkout in zip(refs,checkouts):
                camera.git("worktree","add","--detach",str(checkout),ref)
            jobs=[("piTrainer","review")] if args.kind=="trainer" else [(c,k) for c,cs in CASES.items() for k in cs]
            for component,case in jobs:
                key=component+"/"+case
                runs=[[] for _ in refs]
                def execute(i,attribute=False):
                    cmd=[sys.executable,str(Path(__file__).resolve()),"--worker","--checkout",str(checkouts[i]),
                         "--revision",refs[i],"--component",component,"--case",case,
                         "--duration",str(args.duration),"--rows",str(args.rows)]
                    if attribute:cmd.append("--attribute")
                    run=subprocess.run(cmd,capture_output=True,text=True,timeout=180,
                        env={**os.environ,"QT_QPA_PLATFORM":"offscreen","PYTHONDONTWRITEBYTECODE":"1",
                             "OPENBLAS_NUM_THREADS":"1","OMP_NUM_THREADS":"1","MPLCONFIGDIR":str(Path(temp)/"mpl")})
                    if run.returncode:
                        raise RuntimeError(f"{key} {refs[i]} failed\n{run.stderr}\n{run.stdout}")
                    return json.loads(run.stdout)
                for round_no in range(args.rounds):
                    order=list(range(len(refs)))
                    if len(refs)==3:
                        order=order[round_no%3:]+order[:round_no%3]
                    if round_no%2:order.reverse()
                    for i in order:
                        runs[i].append(execute(i))
                        print(key,round_no+1,refs[i][:7],"passed",flush=True)
                if args.kind=="trainer":
                    assert len({r["semantic_sha256"] for series in runs for r in series})==1,"review semantic parity failed"
                result["runs"][key]=dict(zip(refs,runs))
                if args.kind=="camera":
                    result["attribution"][key]={refs[i]:execute(i,True) for i in range(len(refs))}
                # Preserve completed cases even if a later workload fails.
                args.output.parent.mkdir(parents=True,exist_ok=True)
                args.output.write_text(json.dumps(result,indent=2)+"\n")
        finally:
            for checkout in checkouts:
                if checkout.exists():camera.git("worktree","remove","--force",str(checkout))
    for key,series in result["runs"].items():
        metrics=("peak_rss_bytes","review_action_p95_ms","rebuild_p95_ms","cpu_s") if args.kind=="trainer" else ("cpu_s_per_wall_s","cpu_ms_per_capture","process_high_water_rss_bytes")
        print(key,json.dumps({ref:{m:statistics.median(x[m] for x in samples) for m in metrics} for ref,samples in series.items()}),flush=True)


if __name__=="__main__":
    main()
