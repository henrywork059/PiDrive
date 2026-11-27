"""Actual PIL validation preparation: matched dense legacy, dense single buffer, chunked source.
No model, training epoch or physical-device claims. Each mode uses a fresh process.
"""
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


def worker(args):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]/"piTrainer"))
    import numpy as np
    import pandas as pd
    from PIL import Image
    from piTrainer.services.validation.validation_inputs import _prepare_input_source
    frame=pd.DataFrame({"abs_image":[str(Path(args.fixture)/f"{i%32}.jpg") for i in range(args.rows)],
        "frame_id":range(args.rows),"steering":[.3]*args.rows,"throttle":[.4]*args.rows,
        "source_steering":[.3]*args.rows,"source_throttle":[.4]*args.rows,
        "aug_flip_lr":[bool(i%2) for i in range(args.rows)]})
    start_cpu,start_wall=time.process_time(),time.monotonic()
    rows,source,steer,speed=_prepare_input_source(frame,120,160,0)
    digest=hashlib.sha256()
    max_rows=0
    if args.worker=="legacy":
        images=[]
        for path,flip in zip(source.paths,source.flips):
            with Image.open(path) as im:
                im=im.convert("RGB")
                if flip: im=im.transpose(Image.Transpose.FLIP_LEFT_RIGHT)
                images.append(np.asarray(im.resize((160,120)),dtype=np.float32)/255.0)
        x=np.stack(images,axis=0)
        digest.update(memoryview(x).cast("B"))
        max_rows=len(x)
    elif args.worker=="dense":
        x=source[:]
        digest.update(memoryview(x).cast("B"))
        max_rows=len(x)
    else:
        for start in range(0,len(source),args.batch):
            chunk=source[start:start+args.batch]
            max_rows=max(max_rows,len(chunk))
            digest.update(memoryview(chunk).cast("B"))
            del chunk
    digest.update(memoryview(steer).cast("B"))
    digest.update(memoryview(speed).cast("B"))
    digest.update(rows[["frame_id","source_row_number"]].to_json(orient="split").encode())
    cpu,wall=time.process_time()-start_cpu,time.monotonic()-start_wall
    print(json.dumps({"mode":args.worker,"rows":len(rows),"batch":args.batch,
        "maximum_materialized_image_rows":max_rows,"cpu_s":cpu,"wall_s":wall,
        "peak_rss_bytes":resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,
        "semantic_sha256":digest.hexdigest(),"numpy":np.__version__,"pandas":pd.__version__}))


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--rows",type=int,default=384)
    p.add_argument("--rounds",type=int,default=5)
    p.add_argument("--batch",type=int,default=16)
    p.add_argument("--output",type=Path)
    p.add_argument("--worker",choices=("legacy","dense","stream"))
    p.add_argument("--fixture")
    args=p.parse_args()
    if not 1<=args.batch<=128 or not 32<=args.rows<=2048: p.error("invalid rows or batch")
    if args.worker:
        worker(args)
        return
    if not 5<=args.rounds<=20 or args.output is None: p.error("five or more rounds and output required")
    import numpy as np
    from PIL import Image
    runs={mode:[] for mode in ("legacy","dense","stream")}
    with tempfile.TemporaryDirectory(prefix="pidrive-validation-p2-") as tmp:
        rng=np.random.default_rng(29)
        for i in range(32):
            Image.fromarray(rng.integers(0,256,(240,426,3),dtype=np.uint8)).save(Path(tmp)/f"{i}.jpg",quality=85)
        modes=list(runs)
        for i in range(args.rounds):
            for mode in modes[i%3:]+modes[:i%3]:
                result=subprocess.run([sys.executable,str(Path(__file__).resolve()),"--worker",mode,
                    "--fixture",tmp,"--rows",str(args.rows),"--batch",str(args.batch)],capture_output=True,
                    text=True,check=True,timeout=120,env={**os.environ,"PYTHONDONTWRITEBYTECODE":"1"})
                runs[mode].append(json.loads(result.stdout))
    assert len({x["semantic_sha256"] for series in runs.values() for x in series})==1
    assert all(x["maximum_materialized_image_rows"]<=args.batch for x in runs["stream"])
    summary={mode:{m:statistics.median(x[m] for x in series)
                   for m in ("cpu_s","wall_s","peak_rss_bytes","maximum_materialized_image_rows")}
                   for mode,series in runs.items()}
    report={"revision":subprocess.check_output(["git","rev-parse","HEAD"],text=True).strip(),
        "scope":"offline validation preparation and digest; no inference, real recording or training epoch",
        "rows":args.rows,"rounds":args.rounds,"runs":runs,"summary":summary}
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(report,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(summary,indent=2))


if __name__=="__main__":
    main()
