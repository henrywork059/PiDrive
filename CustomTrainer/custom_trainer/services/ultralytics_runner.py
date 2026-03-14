from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from typing import Callable, Iterable, Sequence

LogFn = Callable[[str], None]


def run_command(command: Sequence[str], log: LogFn, cwd: Path | None = None) -> int:
    log("$ " + " ".join(command))
    process = subprocess.Popen(
        list(command),
        cwd=str(cwd) if cwd else None,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    )
    assert process.stdout is not None
    for line in process.stdout:
        log(line.rstrip())
    process.wait()
    log(f"[exit code] {process.returncode}")
    return process.returncode


def build_train_command(
    model: str,
    data: str,
    epochs: int,
    imgsz: int,
    batch: int,
    device: str,
    project: str,
    name: str,
) -> list[str]:
    return [
        sys.executable,
        "-m",
        "ultralytics",
        "train",
        f"model={model}",
        f"data={data}",
        f"epochs={epochs}",
        f"imgsz={imgsz}",
        f"batch={batch}",
        f"device={device}",
        f"project={project}",
        f"name={name}",
    ]


def build_val_command(weights: str, data: str, imgsz: int, device: str) -> list[str]:
    return [
        sys.executable,
        "-m",
        "ultralytics",
        "val",
        f"model={weights}",
        f"data={data}",
        f"imgsz={imgsz}",
        f"device={device}",
    ]


def build_predict_command(weights: str, source: str, imgsz: int, conf: float, device: str) -> list[str]:
    return [
        sys.executable,
        "-m",
        "ultralytics",
        "predict",
        f"model={weights}",
        f"source={source}",
        f"imgsz={imgsz}",
        f"conf={conf}",
        f"device={device}",
        "save=True",
    ]


def build_export_command(
    weights: str,
    export_format: str,
    imgsz: int,
    device: str,
    int8: bool = False,
    half: bool = False,
    nms: bool = False,
    data: str = "",
) -> list[str]:
    command = [
        sys.executable,
        "-m",
        "ultralytics",
        "export",
        f"model={weights}",
        f"format={export_format}",
        f"imgsz={imgsz}",
        f"device={device}",
    ]
    if int8:
        command.append("int8=True")
    if half:
        command.append("half=True")
    if nms:
        command.append("nms=True")
    if data:
        command.append(f"data={data}")
    return command
