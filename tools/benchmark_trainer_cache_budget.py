#!/usr/bin/env python3
"""Experiment with preview cache budgets in isolated real native Qt workers.

No production change. Compare 8/16/32/64 MiB using identical cold/revisit
review, semantic digests, fresh worker RSS and actual source decode counts.
"""
from __future__ import annotations
import argparse
import json
import os
from pathlib import Path
import statistics
import subprocess
import sys
import tempfile
import benchmark_camera_workloads as camera

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--revision",required=True);p.add_argument("--base",required=True)
    p.add_argument("--output",type=Path,required=True)
    p.add_argument("--rounds",type=int,default=5);p.add_argument("--rows",type=int,default=30000)
    a=p.parse_args()
    if a.rounds<5 or a.rows<10000 or a.rows%2:p.error("at least five rounds and even >=10000 rows")
    ref=camera.trusted(a.revision)
    base=camera.trusted(a.base)
    budgets=[64,32,16,8]
    treatments=[("base64",base,64)]+[(str(b),ref,b) for b in budgets]
    runs={key:[] for key,_,_ in treatments}
    with tempfile.TemporaryDirectory(prefix="pidrive-cache-budget-") as tmp:
        checkouts={base:Path(tmp)/"base",ref:Path(tmp)/"source"}
        try:
            for revision,checkout in checkouts.items():
                camera.git("worktree","add","--detach",str(checkout),revision)
            for r in range(a.rounds):
                offset=r%len(treatments)
                order=treatments[offset:]+treatments[:offset]
                if r%2:order=list(reversed(order))
                for key,revision,b in order:
                    checkout=checkouts[revision]
                    cmd=[sys.executable,str(Path(__file__).with_name("benchmark_performance_strict.py")),
                         "--worker","--checkout",str(checkout),"--revision",revision,"--component","piTrainer",
                         "--rows",str(a.rows),"--cache-budget-mib",str(b)]
                    proc=subprocess.run(cmd,capture_output=True,text=True,timeout=180,
                        env={**os.environ,"QT_QPA_PLATFORM":"offscreen","PYTHONDONTWRITEBYTECODE":"1",
                             "OPENBLAS_NUM_THREADS":"1","OMP_NUM_THREADS":"1","MPLCONFIGDIR":str(Path(tmp)/"mpl")})
                    if proc.returncode:raise RuntimeError(f"budget {b} failed\n{proc.stderr}\n{proc.stdout}")
                    runs[key].append(json.loads(proc.stdout))
                    a.output.parent.mkdir(parents=True,exist_ok=True)
                    a.output.write_text(json.dumps({"baseline":base,"revision":ref,"rounds":a.rounds,"runs":runs},indent=2)+"\n")
                    print("cache budget",key,"round",r+1,"passed",flush=True)
        finally:
            for checkout in checkouts.values():
                if checkout.exists():camera.git("worktree","remove","--force",str(checkout))
    assert len({x["semantic_sha256"] for rr in runs.values() for x in rr})==1,"semantic parity failed"
    metrics=("peak_rss_bytes","review_action_p95_ms","repeat_action_p95_ms","rebuild_p95_ms","total_decodes","repeat_decodes","cpu_s")
    summary={b:{k:statistics.median(x[k] for x in rr) for k in metrics} for b,rr in runs.items()}
    a.output.write_text(json.dumps({"baseline":base,"revision":ref,"rounds":a.rounds,"runs":runs,"summary":summary,"semantic_parity":True},indent=2)+"\n")
    print(json.dumps(summary,indent=2))

if __name__=="__main__":main()
