"""Paired, isolated-process TensorFlow metadata preparation resource benchmark."""
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
import time


def worker(mode, rows):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]/"piTrainer"))
    import numpy as np
    import pandas as pd
    from piTrainer.services.train.dataset_service import _prepare_dataset_rows, _DATASET_COLUMNS
    from piTrainer.services.data.augmentation_service import normalize_horizontal_flip_labels
    from piTrainer.services.data.visibility_service import without_hidden_rows
    rng=np.random.default_rng(17)
    i=np.arange(rows)
    frame=pd.DataFrame({"abs_image":["fixture.jpg"]*rows, "steering":rng.random(rows),
        "throttle":rng.random(rows), "aug_flip_lr":i%4==1,
        "source_steering":rng.random(rows), "source_throttle":rng.random(rows),
        "frame_id":i,"source_frame_id":i-1, "hidden":i%29==0,
        "training_label":[{"hidden":False}]*rows,
        **{f"metadata{k}":rng.random(rows) for k in range(40)}})
    start_cpu=time.process_time()
    start_wall=time.monotonic()
    prepared=(normalize_horizontal_flip_labels(without_hidden_rows(frame))
              if mode=="legacy" else _prepare_dataset_rows(frame))
    cpu=time.process_time()-start_cpu
    wall=time.monotonic()-start_wall
    peak=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024
    columns=[c for c in prepared.columns if c in _DATASET_COLUMNS]
    retained=prepared[columns]
    digest=hashlib.sha256(retained.to_json(orient="split",double_precision=15).encode()).hexdigest()
    print(json.dumps({"mode":mode,"rows":len(retained),"cpu_s":cpu,"wall_s":wall,
                      "peak_rss_bytes":peak,"semantic_sha256":digest,
                      "dtypes":[str(x) for x in retained.dtypes],
                      "numpy":np.__version__,"pandas":pd.__version__}))


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--rows",type=int,default=60000)
    p.add_argument("--rounds",type=int,default=5)
    p.add_argument("--output",type=Path)
    p.add_argument("--worker",choices=("legacy","projection"))
    a=p.parse_args()
    if not 1000<=a.rows<=200000: p.error("rows 1000..200000")
    if a.worker:
        worker(a.worker,a.rows)
        return
    if not 5<=a.rounds<=20 or a.output is None: p.error("five to twenty rounds and output required")
    runs={"legacy":[],"projection":[]}
    for i in range(a.rounds):
        for mode in (("legacy","projection") if i%2==0 else ("projection","legacy")):
            cmd=[sys.executable,str(Path(__file__).resolve()),"--worker",mode,"--rows",str(a.rows)]
            result=subprocess.run(cmd,check=True,capture_output=True,text=True,timeout=120,
                env={**os.environ,"PYTHONDONTWRITEBYTECODE":"1"})
            runs[mode].append(json.loads(result.stdout))
    samples=[x for series in runs.values() for x in series]
    assert len({x["semantic_sha256"] for x in samples})==1
    assert all(x["dtypes"]==samples[0]["dtypes"] for x in samples)
    summary={key:{m:statistics.median(x[m] for x in series)
                  for m in ("cpu_s","wall_s","peak_rss_bytes")} for key,series in runs.items()}
    report={"revision":subprocess.check_output(["git","rev-parse","HEAD"],text=True).strip(),
            "scope":"actual current metadata preparation vs exact legacy expression; no TensorFlow decode or epoch",
            "input_rows":a.rows,"rounds":a.rounds,"runs":runs,"summary":summary}
    a.output.parent.mkdir(parents=True,exist_ok=True)
    a.output.write_text(json.dumps(report,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(summary,indent=2))


if __name__=="__main__":
    main()
