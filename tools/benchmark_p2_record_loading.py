"""Paired actual JSONL loading against two exact Git revisions (Linux CI)."""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path
import resource
import statistics
import subprocess
import sys
import tempfile
import time


def git(*args):
    return subprocess.check_output(["git", *args], text=True).strip()


def worker(args):
    assert git("-C", args.checkout, "rev-parse", "HEAD") == args.revision
    sys.path.insert(0, str(Path(args.checkout) / "piTrainer"))
    from piTrainer.services.data.record_loader_service import load_records_dataframe
    start = time.process_time()
    wall = time.monotonic()
    frame = load_records_dataframe(Path(args.fixture), ["drive"])
    elapsed, cpu = time.monotonic()-wall, time.process_time()-start
    peak = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024
    assert len(frame) == args.rows
    digest = hashlib.sha256(frame.to_json(orient="records", double_precision=15).encode()).hexdigest()
    print(json.dumps({"rows": len(frame), "cpu_s": cpu, "wall_s": elapsed,
                      "process_peak_rss_bytes": peak, "semantic_sha256": digest}))


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--base")
    p.add_argument("--candidate")
    p.add_argument("--rounds", type=int, default=5)
    p.add_argument("--rows", type=int, default=30000)
    p.add_argument("--output", type=Path)
    p.add_argument("--worker", action="store_true")
    p.add_argument("--checkout")
    p.add_argument("--revision")
    p.add_argument("--fixture")
    args = p.parse_args()
    if args.worker:
        worker(args)
        return
    if args.rounds < 5 or not 1000 <= args.rows <= 200000 or not args.output:
        p.error("five or more rounds, 1000..200000 rows, output required")
    refs = [args.base, args.candidate]
    for ref in refs:
        if not ref or len(ref)!=40 or git("rev-parse", "--verify", ref+"^{commit}") != ref:
            p.error("exact trusted commit SHAs required")
    with tempfile.TemporaryDirectory(prefix="pidrive-load-p2-") as tmp:
        fixture = Path(tmp) / "dataset"
        frames = fixture / "drive" / "frames"
        frames.mkdir(parents=True)
        for i in range(512):
            (frames / f"{i}.jpg").write_bytes(b"metadata-only-image-fixture")
        with (frames.parent / "labels.jsonl").open("w", encoding="utf-8") as handle:
            for i in range(args.rows):
                handle.write(json.dumps({"frame": f"frames/{i%512}.jpg", "frame_id": i,
                                         "ts": str(i), "mode": "manual", "steering": (i%201-100)/100,
                                         "throttle": (i%100)/100, "cam_w": 426,
                                         "overlay_settings": {"brightness": 1.0}})+"\n")
        checkouts = [Path(tmp) / "before", Path(tmp) / "after"]
        runs = [[], []]
        try:
            for ref, checkout in zip(refs, checkouts):
                subprocess.run(["git", "worktree", "add", "--detach", str(checkout), ref], check=True)
            for n in range(args.rounds):
                for i in ((0,1) if n%2==0 else (1,0)):
                    cmd = [sys.executable, str(Path(__file__).resolve()), "--worker",
                           "--checkout", str(checkouts[i]), "--revision", refs[i],
                           "--fixture", str(fixture), "--rows", str(args.rows)]
                    result = subprocess.run(cmd, text=True, capture_output=True, check=True,
                                            timeout=180, env={**os.environ, "PYTHONDONTWRITEBYTECODE":"1"})
                    runs[i].append(json.loads(result.stdout))
        finally:
            for checkout in checkouts:
                if checkout.exists():
                    subprocess.run(["git", "worktree", "remove", "--force", str(checkout)], check=True)
        assert len({r["semantic_sha256"] for series in runs for r in series}) == 1
        report = {"revisions": refs, "rows": args.rows, "unique_image_paths": 512,
                  "scope": "actual JSONL loader with existing metadata-only image paths; no decoding",
                  "runs": dict(zip(refs,runs)), "summary": {
                      ref: {metric: statistics.median(r[metric] for r in series)
                            for metric in ("cpu_s","wall_s","process_peak_rss_bytes")}
                      for ref,series in zip(refs,runs)}}
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report,indent=2)+"\n",encoding="utf-8")
        print(json.dumps(report["summary"],indent=2))


if __name__ == "__main__":
    main()
