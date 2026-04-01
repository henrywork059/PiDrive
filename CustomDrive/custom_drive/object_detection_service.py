from __future__ import annotations

import os
import tempfile
import threading
import time
from pathlib import Path
from typing import Any

try:
    import cv2
except Exception:  # pragma: no cover
    cv2 = None  # type: ignore

try:
    import numpy as np
except Exception:  # pragma: no cover
    np = None  # type: ignore

from .models import Detection
from .tflite_perception import TFLitePerception

_SUPPORTED_UPLOAD_SUFFIXES = {'.tflite', '.txt', '.json'}


def _atomic_write_bytes(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_path = tempfile.mkstemp(prefix=path.stem + '_', suffix='.tmp', dir=str(path.parent))
    try:
        with os.fdopen(fd, 'wb') as handle:
            handle.write(data)
        os.replace(tmp_path, path)
    finally:
        try:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)
        except OSError:
            pass


class ObjectDetectionService:
    def __init__(self, root: str | Path, config: dict[str, Any] | None = None):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self.perception = TFLitePerception(base_dir=self.root)
        self.backend_name = 'color'
        self.active_model = 'none'
        self.labels_file = ''
        self.overlay_enabled = True
        self.confidence_threshold = 0.25
        self.iou_threshold = 0.45
        self.max_overlay_fps = 6.0
        self.input_size = 0
        self.target_label = 'he3'
        self.drop_zone_label = 'he3_zone'
        self.last_error = ''
        self.last_inference_ms = 0.0
        self._last_result: dict[str, Any] = {'detections': [], 'timestamp': 0.0, 'debug': {}}
        self._last_annotated_jpeg: bytes | None = None
        self._last_annotated_ts = 0.0
        self._cache_window_s = 1.0 / max(self.max_overlay_fps, 0.5)
        self._infer_lock = threading.Lock()
        self.apply_runtime_config(config or {})
        if self.active_model != 'none' and self.backend_name == 'tflite':
            self.deploy_model(self.active_model)

    def list_label_files(self) -> list[str]:
        return self.perception.labels_candidates()

    def apply_runtime_config(self, config: dict[str, Any] | None) -> None:
        cfg = config or {}
        with self._lock:
            backend = str(cfg.get('perception_backend', self.backend_name) or self.backend_name).strip().lower() or 'color'
            self.backend_name = backend if backend in {'color', 'tflite'} else 'color'
            self.overlay_enabled = bool(cfg.get('overlay_enabled', self.overlay_enabled))
            self.confidence_threshold = max(0.01, min(0.99, float(cfg.get('confidence_threshold', self.confidence_threshold))))
            self.iou_threshold = max(0.01, min(0.99, float(cfg.get('iou_threshold', self.iou_threshold))))
            self.max_overlay_fps = max(0.5, min(30.0, float(cfg.get('max_overlay_fps', self.max_overlay_fps))))
            self._cache_window_s = 1.0 / max(self.max_overlay_fps, 0.5)
            self.input_size = max(0, int(cfg.get('input_size', self.input_size) or 0))
            self.target_label = str(cfg.get('target_label', self.target_label) or self.target_label).strip() or 'he3'
            self.drop_zone_label = str(cfg.get('drop_zone_label', self.drop_zone_label) or self.drop_zone_label).strip() or 'he3_zone'
            requested_model = str(cfg.get('deployed_model', self.active_model) or 'none').strip() or 'none'
            if requested_model and requested_model != 'none' and not requested_model.lower().endswith('.tflite'):
                requested_model = 'none'
            self.active_model = requested_model
            labels_file = str(cfg.get('labels_file', self.labels_file) or self.labels_file).strip()
            if labels_file and not labels_file.lower().endswith('.txt'):
                labels_file = ''
            self.labels_file = labels_file

    def list_models(self) -> list[dict[str, Any]]:
        models: list[dict[str, Any]] = []
        active = self.get_active_model_name()
        for name in self.perception.model_candidates():
            model_path = self.root / name
            try:
                bundle = self.perception.bundle if self.perception.bundle and self.perception.bundle.model_path == model_path.resolve() else None
                if bundle is None:
                    from .tflite_perception import resolve_bundle
                    bundle = resolve_bundle(model_path, self.labels_file or None, base_dir=self.root)
                labels_path = bundle.labels_path
                config_path = bundle.config_path
            except Exception:
                labels_path = None
                config_path = None
            models.append({
                'name': name,
                'stem': model_path.stem,
                'has_labels': labels_path is not None,
                'has_config': config_path is not None,
                'active': name == active,
                'labels_file': labels_path.name if labels_path else '',
                'config_file': config_path.name if config_path else '',
            })
        return models

    def save_uploaded_files(self, files: list[Any]) -> tuple[bool, list[str], str]:
        saved: list[str] = []
        if not files:
            return False, saved, 'No files uploaded.'
        try:
            for file_storage in files:
                filename = Path((getattr(file_storage, 'filename', '') or '').strip()).name
                if not filename:
                    continue
                suffix = Path(filename).suffix.lower()
                if suffix not in _SUPPORTED_UPLOAD_SUFFIXES:
                    return False, saved, f'Unsupported file type: {suffix or filename}'
                payload = file_storage.read() or b''
                _atomic_write_bytes(self.root / filename, payload)
                saved.append(filename)
            if not saved:
                return False, saved, 'No valid files uploaded.'
            return True, saved, f'Saved {len(saved)} file(s).'
        except Exception as exc:
            return False, saved, f'Upload failed: {exc}'

    def delete_model_bundle(self, filename: str) -> tuple[bool, str]:
        safe_name = Path(str(filename or '')).name
        if not safe_name or not safe_name.lower().endswith('.tflite'):
            return False, 'Select a .tflite model first.'
        path = self.root / safe_name
        if not path.exists():
            return False, 'Model file does not exist.'
        stem = path.stem
        removed: list[str] = []
        try:
            for target in [path, self.root / f'{stem}.txt', self.root / f'{stem}.json']:
                if target.exists() and target.is_file():
                    target.unlink()
                    removed.append(target.name)
            with self._lock:
                if self.active_model == safe_name:
                    self.active_model = 'none'
                    self.labels_file = ''
                    self.perception.clear()
                    self._last_result = {'detections': [], 'timestamp': 0.0, 'debug': {}}
                    self._last_annotated_jpeg = None
                    self._last_annotated_ts = 0.0
            return True, 'Deleted: ' + ', '.join(removed)
        except Exception as exc:
            return False, f'Delete failed: {exc}'

    def deploy_model(self, filename: str, config_overrides: dict[str, Any] | None = None) -> tuple[bool, str]:
        safe_name = Path(str(filename or '')).name
        path = self.root / safe_name
        if not safe_name or not path.exists() or path.suffix.lower() != '.tflite':
            return False, 'Model file does not exist.'
        overrides = config_overrides or {}
        labels_file = str(overrides.get('labels_file', self.labels_file) or self.labels_file).strip()
        labels_path = self.root / labels_file if labels_file else None
        ok, message = self.perception.deploy(
            path,
            labels_path=labels_path,
            input_size=int(overrides.get('input_size', self.input_size) or self.input_size or 0),
            confidence_threshold=float(overrides.get('confidence_threshold', self.confidence_threshold)),
            iou_threshold=float(overrides.get('iou_threshold', self.iou_threshold)),
        )
        with self._lock:
            if ok:
                self.active_model = safe_name
                self.confidence_threshold = float(overrides.get('confidence_threshold', self.confidence_threshold))
                self.iou_threshold = float(overrides.get('iou_threshold', self.iou_threshold))
                self.overlay_enabled = bool(overrides.get('overlay_enabled', self.overlay_enabled))
                self.max_overlay_fps = max(0.5, min(30.0, float(overrides.get('max_overlay_fps', self.max_overlay_fps))))
                self._cache_window_s = 1.0 / max(self.max_overlay_fps, 0.5)
                self.input_size = int(overrides.get('input_size', self.input_size) or self.input_size or 0)
                self.labels_file = Path(str(self.perception.status().get('labels_path', '') or '')).name
                self._last_result = {'detections': [], 'timestamp': 0.0, 'debug': {}}
                self._last_annotated_jpeg = None
                self._last_annotated_ts = 0.0
                self.last_error = ''
            else:
                self.last_error = message
        return ok, message

    def get_active_model_name(self) -> str:
        with self._lock:
            return self.active_model

    def get_status(self, include_models: bool = True) -> dict[str, Any]:
        with self._lock:
            perception_status = self.perception.status()
            payload = {
                'backend': self.backend_name,
                'active_model': self.active_model,
                'labels_file': Path(str(perception_status.get('labels_path', '') or self.labels_file)).name if (perception_status.get('labels_path') or self.labels_file) else '',
                'labels_path': str(perception_status.get('labels_path', '') or ''),
                'labels': list(perception_status.get('labels', [])),
                'overlay_enabled': bool(self.overlay_enabled),
                'confidence_threshold': float(self.confidence_threshold),
                'iou_threshold': float(self.iou_threshold),
                'max_overlay_fps': float(self.max_overlay_fps),
                'input_size': int(self.input_size),
                'resolved_input_size': int(perception_status.get('resolved_input_size', 0) or 0),
                'target_label': self.target_label,
                'drop_zone_label': self.drop_zone_label,
                'last_error': str(self.last_error or perception_status.get('last_error', '')),
                'last_inference_ms': float(perception_status.get('last_inference_ms', self.last_inference_ms) or 0.0),
                'ready': bool(self.backend_name == 'tflite' and perception_status.get('ready')),
                'last_detections': list(self._last_result.get('detections', [])),
                'last_detection_count': int(len(self._last_result.get('detections', []))),
                'debug': dict(perception_status.get('debug', {}) or self._last_result.get('debug', {}) or {}),
                'labels_mode': str(perception_status.get('labels_mode', 'missing')),
            }
        if include_models:
            payload['models'] = self.list_models()
            payload['label_files'] = self.list_label_files()
        return payload

    @staticmethod
    def _detection_to_dict(det: Detection) -> dict[str, Any]:
        return {
            'label': det.label,
            'score': round(float(det.confidence), 4),
            'class_id': -1,
            'box': [int(det.box.x1), int(det.box.y1), int(det.box.x2), int(det.box.y2)],
        }

    def _infer_frame(self, frame_bgr) -> list[dict[str, Any]]:
        detections = [self._detection_to_dict(det) for det in self.perception.infer_detections(frame_bgr)]
        perception_status = self.perception.status()
        with self._lock:
            self.last_inference_ms = float(perception_status.get('last_inference_ms', 0.0) or 0.0)
            self.last_error = str(perception_status.get('last_error', '') or '')
            now_mono = time.monotonic()
            self._last_result = {
                'detections': detections,
                'timestamp': now_mono,
                'debug': dict(perception_status.get('debug', {})),
            }
        return detections

    def run_debug_inference(self, frame_bgr=None) -> dict[str, Any]:
        if frame_bgr is not None:
            try:
                self._infer_frame(frame_bgr)
            except Exception as exc:
                with self._lock:
                    self.last_error = f'Inference failed: {exc}'
        status = self.get_status(include_models=False)
        return {
            'backend': status.get('backend', 'color'),
            'ready': bool(status.get('ready')),
            'active_model': status.get('active_model', 'none'),
            'labels_file': status.get('labels_file', ''),
            'labels_mode': status.get('labels_mode', 'missing'),
            'labels_count': len(status.get('labels', [])),
            'resolved_input_size': int(status.get('resolved_input_size', 0) or 0),
            'last_detection_count': int(status.get('last_detection_count', 0) or 0),
            'last_error': str(status.get('last_error', '') or ''),
            'last_inference_ms': float(status.get('last_inference_ms', 0.0) or 0.0),
            'debug': dict(status.get('debug', {}) or {}),
        }

    def _draw_overlay(self, frame_bgr, detections: list[dict[str, Any]]):
        if cv2 is None:
            return frame_bgr
        out = frame_bgr.copy()
        for det in detections:
            x1, y1, x2, y2 = det.get('box', [0, 0, 0, 0])
            label = det.get('label', 'obj')
            score = float(det.get('score', 0.0))
            text = f'{label} {score:.2f}'
            cv2.rectangle(out, (x1, y1), (x2, y2), (0, 255, 0), 2)
            cv2.putText(out, text, (x1, max(18, y1 - 8)), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 255, 0), 2, cv2.LINE_AA)
        debug = self.perception.status().get('debug', {}) if self.backend_name == 'tflite' else {}
        det_count = len(detections)
        if self.active_model != 'none' and self.backend_name == 'tflite':
            meta = f'OD {self.active_model} det={det_count}'
            detail = (
                f"raw={debug.get('raw_shape', [])} "
                f"variant={debug.get('selected_variant', 'none')} "
                f"cand={debug.get('candidate_count', 0)} dec={debug.get('decoded_count', 0)} keep={debug.get('nms_count', 0)}"
            )
        else:
            meta = 'OD off'
            detail = ''
        cv2.putText(out, meta, (10, 22), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (0, 255, 0), 2, cv2.LINE_AA)
        if detail:
            cv2.putText(out, detail[:96], (10, 46), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 220, 255), 1, cv2.LINE_AA)
        return out

    def annotate_jpeg_bytes(self, jpeg_bytes: bytes | None) -> tuple[bytes | None, list[dict[str, Any]]]:
        if jpeg_bytes is None or cv2 is None or np is None:
            return jpeg_bytes, []
        try:
            arr = np.frombuffer(jpeg_bytes, dtype=np.uint8)
            frame_bgr = cv2.imdecode(arr, cv2.IMREAD_COLOR)
        except Exception as exc:
            with self._lock:
                self.last_error = f'JPEG decode failed: {exc}'
            return jpeg_bytes, []
        if frame_bgr is None:
            return jpeg_bytes, []
        annotated, detections = self.annotate_frame_jpeg(frame_bgr)
        return (annotated if annotated is not None else jpeg_bytes), detections

    def annotate_frame_jpeg(self, frame_bgr) -> tuple[bytes | None, list[dict[str, Any]]]:
        if frame_bgr is None or cv2 is None or np is None:
            return None, []
        with self._lock:
            ready = self.backend_name == 'tflite' and self.perception.is_ready() and self.overlay_enabled
            last_ts = float(self._last_result.get('timestamp', 0.0))
            cache_window = float(self._cache_window_s)
            detections = list(self._last_result.get('detections', []))
            cached_jpeg = self._last_annotated_jpeg
            cached_jpeg_ts = float(self._last_annotated_ts)
        if ready:
            now = time.monotonic()
            if cached_jpeg is not None and now - cached_jpeg_ts < max(cache_window, 0.18):
                return cached_jpeg, detections
            if now - last_ts >= cache_window and self._infer_lock.acquire(blocking=False):
                try:
                    detections = self._infer_frame(frame_bgr)
                except Exception as exc:
                    with self._lock:
                        self.last_error = f'Inference failed: {exc}'
                    detections = []
                finally:
                    self._infer_lock.release()
            annotated = self._draw_overlay(frame_bgr, detections)
        else:
            annotated = frame_bgr
        ok, encoded = cv2.imencode('.jpg', annotated, [int(cv2.IMWRITE_JPEG_QUALITY), 72])
        out = encoded.tobytes() if ok else None
        if out is not None:
            with self._lock:
                self._last_annotated_jpeg = out
                self._last_annotated_ts = time.monotonic()
        return out, detections
