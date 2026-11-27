"""Matched actual CPU training + validation epochs with deterministic inputs.
Fresh process per mode, same fixture and seeds. Synthetic labels, no deployment.
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


def worker(a):
    sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"piTrainer"))
    import numpy as np
    import pandas as pd
    import tensorflow as tf
    from piTrainer.services.train.dataset_service import make_tf_dataset
    from piTrainer.services.train.model_service import build_model, compile_model
    tf.keras.utils.set_random_seed(42)
    tf.config.experimental.enable_op_determinism()
    n=a.rows
    frame=pd.DataFrame({"abs_image":[str(Path(a.fixture)/f"{i%32}.jpg") for i in range(n)],
        "frame_id":range(n),"steering":np.linspace(-.4,.4,n),"throttle":np.linspace(.2,.8,n),
        "aug_flip_lr":np.arange(n)%2==1,"source_steering":np.linspace(-.4,.4,n),
        "source_throttle":np.linspace(.2,.8,n)})
    bounded=a.worker=="bounded"
    cut=n*3//4
    train=make_tf_dataset(frame.iloc[:cut],120,160,8,False,False,bounded_input=bounded)
    val=make_tf_dataset(frame.iloc[cut:],120,160,8,False,False,bounded_input=bounded)
    # Actual production small CNN and optimizer; no dropout in this deterministic
    # fixture. Hash exact prepared samples outside measured epoch execution.
    def digest_dataset(ds):
        digest=hashlib.sha256()
        count=0
        for x,y in ds.as_numpy_iterator():
            count+=len(x)
            for arr in (x,y["steering"],y["throttle"]):
                digest.update(arr.tobytes())
        return digest.hexdigest(),count
    train_digest,train_count=digest_dataset(train)
    val_digest,val_count=digest_dataset(val)
    assert (train_count,val_count)==(cut,n-cut)
    model=compile_model(build_model(120,160,"Small CNN",dropout_rate=0.0),.001)
    def weights():
        digest=hashlib.sha256()
        for w in model.get_weights():
            digest.update(w.tobytes())
        return digest.hexdigest()
    initial=weights()
    c0,w0=time.process_time(),time.monotonic()
    history=model.fit(train,validation_data=val,epochs=a.epochs,verbose=0).history
    cpu,wall=time.process_time()-c0,time.monotonic()-w0
    report={"mode":a.worker,"rows":n,"epochs":a.epochs,"train_rows":train_count,
        "val_rows":val_count,"train_digest":train_digest,"validation_digest":val_digest,
        "initial_weights":initial,"final_weights":weights(),
        "metrics":{k:[float(x) for x in v] for k,v in history.items()},
        "cpu_s":cpu,"wall_s":wall,"peak_rss_bytes":resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,
        "tensorflow":tf.__version__,"deployment_authorized":False}
    print(json.dumps(report,allow_nan=False))


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--rows",type=int,default=96);p.add_argument("--rounds",type=int,default=5)
    p.add_argument("--epochs",type=int,default=2);p.add_argument("--output",type=Path)
    p.add_argument("--worker",choices=("auto","bounded"));p.add_argument("--fixture")
    a=p.parse_args()
    if not 32<=a.rows<=1024 or not 1<=a.epochs<=5: p.error("invalid rows/epochs")
    if a.worker: worker(a);return
    if not 5<=a.rounds<=10 or a.output is None: p.error("five to ten rounds and output required")
    import numpy as np
    from PIL import Image
    runs={"auto":[],"bounded":[]}
    with tempfile.TemporaryDirectory(prefix="pidrive-epochs-") as tmp:
        rng=np.random.default_rng(31)
        for i in range(32):
            Image.fromarray(rng.integers(0,256,(240,426,3),dtype=np.uint8)).save(Path(tmp)/f"{i}.jpg",quality=85)
        for i in range(a.rounds):
            for mode in (("auto","bounded") if i%2==0 else ("bounded","auto")):
                cmd=[sys.executable,str(Path(__file__).resolve()),"--worker",mode,"--fixture",tmp,
                     "--rows",str(a.rows),"--epochs",str(a.epochs)]
                result=subprocess.run(cmd,text=True,capture_output=True,timeout=180,
                    env={**os.environ,"TF_NUM_INTEROP_THREADS":"1","TF_NUM_INTRAOP_THREADS":"1",
                         "TF_ENABLE_ONEDNN_OPTS":"0","CUDA_VISIBLE_DEVICES":"-1","PYTHONDONTWRITEBYTECODE":"1"})
                if result.returncode:
                    raise RuntimeError(result.stderr[-10000:])
                runs[mode].append(json.loads(result.stdout))
    samples=[x for series in runs.values() for x in series]
    exact={key:len({x[key] for x in samples})==1 for key in
           ("train_digest","validation_digest","initial_weights","final_weights")}
    metrics_match=all(x["metrics"]==samples[0]["metrics"] for x in samples)
    summary={mode:{k:statistics.median(x[k] for x in series)
                   for k in ("cpu_s","wall_s","peak_rss_bytes")} for mode,series in runs.items()}
    report={"revision":subprocess.check_output(["git","rev-parse","HEAD"],text=True).strip(),
            "scope":"CPU Small CNN, deterministic synthetic labels, no dropout/shuffle/random augmentation",
            "rounds":a.rounds,"runs":runs,"summary":summary,"exact":exact,"metrics_exact":metrics_match,
            "deployment_authorized":False}
    a.output.parent.mkdir(parents=True,exist_ok=True)
    a.output.write_text(json.dumps(report,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(summary,indent=2))
    assert all(exact.values()) and metrics_match, "Deterministic epoch parity mismatch"


if __name__=="__main__":
    main()
