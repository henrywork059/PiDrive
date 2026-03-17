from __future__ import annotations

import sys


def _base_command(action: str) -> list[str]:
    return [sys.executable, '-m', 'custom_trainer.services.ultralytics_cli', action]


def _maybe_append(command: list[str], flag: str, value: str | int | float | None) -> None:
    if value is None:
        return
    text = str(value).strip()
    if not text:
        return
    command.extend([flag, text])


def build_train_command(*, model: str, data: str, epochs: int, imgsz: int, batch: int, device: str, project: str, name: str) -> list[str]:
    command = _base_command('train')
    _maybe_append(command, '--model', model or 'yolov8n.pt')
    _maybe_append(command, '--data', data)
    _maybe_append(command, '--epochs', epochs)
    _maybe_append(command, '--imgsz', imgsz)
    _maybe_append(command, '--batch', batch)
    _maybe_append(command, '--device', device)
    _maybe_append(command, '--project', project)
    _maybe_append(command, '--name', name)
    return command


def build_val_command(*, weights: str, data: str, imgsz: int, device: str, project: str | None = None, name: str | None = None) -> list[str]:
    command = _base_command('val')
    _maybe_append(command, '--weights', weights)
    _maybe_append(command, '--data', data)
    _maybe_append(command, '--imgsz', imgsz)
    _maybe_append(command, '--device', device)
    _maybe_append(command, '--project', project)
    _maybe_append(command, '--name', name)
    return command


def build_predict_command(
    *,
    weights: str,
    source: str,
    imgsz: int,
    conf: float,
    device: str,
    project: str | None = None,
    name: str | None = None,
) -> list[str]:
    command = _base_command('predict')
    _maybe_append(command, '--weights', weights)
    _maybe_append(command, '--source', source)
    _maybe_append(command, '--imgsz', imgsz)
    _maybe_append(command, '--conf', conf)
    _maybe_append(command, '--device', device)
    _maybe_append(command, '--project', project)
    _maybe_append(command, '--name', name)
    return command


def build_export_command(*, weights: str, export_format: str, imgsz: int, device: str, int8: bool, half: bool, nms: bool, data: str) -> list[str]:
    command = _base_command('export')
    _maybe_append(command, '--weights', weights)
    _maybe_append(command, '--format', export_format)
    _maybe_append(command, '--imgsz', imgsz)
    _maybe_append(command, '--device', device)
    if int8:
        command.append('--int8')
    if half:
        command.append('--half')
    if nms:
        command.append('--nms')
    _maybe_append(command, '--data', data)
    return command
