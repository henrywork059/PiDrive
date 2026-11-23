"""R42: immutable-at-launch, honest subprocess result and artifact tracking.

This module uses the existing structured markers emitted by ultralytics_cli.
It never guesses a model, validation folder, or export path from a log message
other than the exact reserved [save-dir], [export] and [metrics] markers.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}


def _now() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def _resolve(text: str, cwd: Path) -> Path | None:
    raw = str(text or "").strip().strip('"').strip("'")
    if not raw:
        return None
    path = Path(raw).expanduser()
    return (path if path.is_absolute() else cwd / path).resolve()


def verified_output(path: str | Path | None, kind: str) -> Path | None:
    """Only completed, nonempty outputs are eligible for Open Location."""
    if not path:
        return None
    try:
        candidate = Path(path).expanduser().resolve()
        if candidate.is_file():
            if kind == "val":
                return None  # Ultralytics validation reports a results directory.
            if candidate.stat().st_size == 0:
                return None
            if kind == "predict" and candidate.suffix.lower() not in IMAGE_EXTENSIONS:
                return None
            if kind == "export" and candidate.suffix.lower() == ".tflite":
                # U27 requires a checksum-bound sidecar for new TFLite exports.
                from custom_trainer.services.model_manifest import inspect_manifest
                metadata, _ = inspect_manifest(candidate, expected_kind="yolo_detection")
                if metadata is None:
                    return None
            return candidate
        if candidate.is_dir():
            if kind == "export":
                return candidate if any(item.is_file() and item.stat().st_size > 0
                                        and not item.name.endswith(".manifest.json")
                                        and item.suffix.lower() != ".tmp"
                                        for item in candidate.rglob("*")) else None
            if kind == "predict":
                return candidate if any(
                    item.is_file() and item.suffix.lower() in IMAGE_EXTENSIONS
                    and item.stat().st_size > 0 for item in candidate.iterdir()
                ) else None
            if kind == "val":
                return candidate if any(item.is_file() and item.stat().st_size > 0
                                        for item in candidate.rglob("*")) else None
    except (OSError, ValueError, RuntimeError):
        return None
    return None


@dataclass
class TaskResult:
    mode: str
    kind: str
    model: str
    dataset: str
    cwd: Path
    export_format: str = ""
    state: str = "Running"
    started_at: str = field(default_factory=_now)
    finished_at: str = ""
    metrics: str = ""
    output_path: str = ""
    reason: str = ""
    stop_requested: bool = False

    @classmethod
    def begin(cls, mode: str, kind: str, model: str, dataset: str, cwd: Path,
              export_format: str = "") -> "TaskResult":
        root = Path(cwd).resolve()
        resolved_model = _resolve(model, root)
        resolved_data = _resolve(dataset, root)
        return cls(
            mode=mode, kind=kind,
            model=str(resolved_model) if resolved_model else "Unknown",
            dataset=str(resolved_data) if resolved_data else "Unknown",
            cwd=root, export_format=str(export_format),
        )

    def observe(self, line: str) -> None:
        text = str(line).strip()
        if text.startswith("[save-dir] ") and self.kind in ("val", "predict"):
            path = _resolve(text[len("[save-dir] "):], self.cwd)
            if path:
                self.output_path = str(path)
        elif text.startswith("[export] ") and self.kind == "export":
            value = text[len("[export] "):].strip()
            if not value.startswith("Model manifest:"):
                path = _resolve(value, self.cwd)
                if path:
                    self.output_path = str(path)
        elif text.startswith("[metrics] ") and self.kind == "val":
            self.metrics = text[len("[metrics] "):].strip()
        elif text.startswith("[error] "):
            self.reason = text[len("[error] "):].strip()

    def request_stop(self) -> None:
        self.stop_requested = True
        self.state = "Stopping"
        self.reason = "Stop requested; waiting for the worker to terminate."

    def finish(self, exit_code: int) -> None:
        self.finished_at = _now()
        if self.stop_requested:
            self.state = "Cancelled"
            self.reason = "Stop requested; partial output is not confirmed."
            return
        if int(exit_code) != 0:
            self.state = "Failed"
            self.reason = self.reason or f"Process exited with code {exit_code}."
            return
        if (self.kind == "export" and self.output_path == self.model) or (
            self.kind == "predict" and self.output_path == self.dataset
        ):
            self.state = "Failed"
            self.reason = "Output path equals the input; no distinct generated artifact was verified."
            return
        if verified_output(self.output_path, self.kind) is None:
            self.state = "Failed"
            self.reason = "Task returned success, but its output was not reported or could not be verified."
            return
        self.state = "Succeeded"
        self.reason = ""

    def verified_path(self) -> Path | None:
        if self.state != "Succeeded":
            return None
        return verified_output(self.output_path, self.kind)

    def _model_file_status(self) -> str:
        try:
            path = Path(self.model)
            return "Present (nonempty); bytes not pinned" if path.is_file() and path.stat().st_size > 0 else "Not verified (original model reference only)"
        except (OSError, ValueError):
            return "Not verified (original model reference only)"

    def display_text(self) -> str:
        description = {
            ("native", "val"): "Native-model validation (.pt)",
            ("native", "predict"): "Native-model prediction (.pt)",
            ("exported", "val"): "Exported-model validation",
            ("exported", "predict"): "Exported-model prediction",
            ("export", "export"): "Model export",
        }.get((self.mode, self.kind), "Model operation")
        state_text = f"{description} — {self.state}"
        parts = [
            state_text, f"Started: {self.started_at}",
            f"Finished: {self.finished_at or 'Not finished'}",
            f"Model: {Path(self.model).name if self.model != 'Unknown' else 'Unknown'}",
            f"Model path: {self.model}",
            f"Model file at path: {self._model_file_status()}",
            f"Dataset/source: {Path(self.dataset).name if self.dataset != 'Unknown' else 'Unknown'}",
            f"Dataset/source path: {self.dataset}",
        ]
        if self.export_format:
            parts.append(f"Export format: {self.export_format}")
        if self.kind == "val":
            parts.append(f"Reported metrics: {self.metrics or 'Unknown'}")
        output_label = "Verified output path" if self.state == "Succeeded" else "Reported output path (unconfirmed)"
        parts.append(f"{output_label}: {self.output_path or 'Unknown'}")
        if self.reason:
            parts.append(f"Result detail: {self.reason}")
        return "\n".join(parts)
