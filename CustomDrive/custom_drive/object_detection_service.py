from __future__ import annotations

import json
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

InterpreterType = None
try:
    from tflite_runtime.interpreter import Interpreter as _Interpreter  # type: ignore
    InterpreterType = _Interpreter
except Exception:  # pragma: no cover
    try:
        from tensorflow.lite.python.interpreter import Interpreter as _Interpreter  # type: ignore
        InterpreterType = _Interpreter
    except Exception:
        InterpreterType = None

_SUPPORTED_UPLOAD_SUFFIXES = {'.tflite', '.txt', '.json'}


def _safe_read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding='utf-8'))
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


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
        self.interpreter = None
        self.active_model = 'none'
        self.labels: list[str] = []
        self.overlay_enabled = True
        self.confidence_threshold = 0.25
        self.iou_threshold = 0.45
        self.max_overlay_fps = 6.0
        self.last_error = ''
        self.last_inference_ms = 0.0
        self._last_result: dict[str, Any] = {'detections': [], 'timestamp': 0.0}
        self._cache_window_s = 0.0
        self.apply_runtime_config(config or {})
        if self.active_model != 'none':
            self.deploy_model(self.active_model)

    def apply_runtime_config(self, config: dict[str, Any] | None) -> None:
        cfg = config or {}
        with self._lock:
            self.overlay_enabled = bool(cfg.get('overlay_enabled', self.overlay_enabled))
            self.confidence_threshold = max(0.01, min(0.99, float(cfg.get('confidence_threshold', self.confidence_threshold))))
            self.iou_threshold = max(0.01, min(0.99, float(cfg.get('iou_threshold', self.iou_threshold))))
            self.max_overlay_fps = max(0.5, min(30.0, float(cfg.get('max_overlay_fps', self.max_overlay_fps))))
            self._cache_window_s = 1.0 / max(self.max_overlay_fps, 0.5)
            requested_model = str(cfg.get('deployed_model', self.active_model) or 'none').strip()
            if requested_model:
                self.active_model = requested_model

    def _resolve_bundle_config(self, filename: str) -> dict[str, Any]:
        safe_name = Path(str(filename or '')).name
        stem = Path(safe_name).stem
        same_stem = _safe_read_json(self.root / f'{stem}.json')
        if same_stem:
            return same_stem
        bundle_cfg = _safe_read_json(self.root / 'model_config.json')
        model_filename = str(bundle_cfg.get('model_filename', '') or '').strip()
        if model_filename and model_filename == safe_name:
            return bundle_cfg
        return {}

    def _resolve_labels_path(self, filename: str, cfg: dict[str, Any] | None = None) -> Path | None:
        safe_name = Path(str(filename or '')).name
        stem = Path(safe_name).stem
        cfg = cfg or {}
        labels_name = str(cfg.get('labels_filename', '') or '').strip()
        if labels_name:
            candidate = self.root / Path(labels_name).name
            if candidate.exists():
                return candidate
        same_stem = self.root / f'{stem}.txt'
        if same_stem.exists():
            return same_stem
        bundle_labels = self.root / 'labels.txt'
        if bundle_labels.exists():
            return bundle_labels
        return None

    def list_models(self) -> list[dict[str, Any]]:
        models: list[dict[str, Any]] = []
        active = self.get_active_model_name()
        for path in sorted(self.root.glob('*.tflite')):
            cfg = self._resolve_bundle_config(path.name)
            labels_path = self._resolve_labels_path(path.name, cfg)
            models.append({
                'name': path.name,
                'stem': path.stem,
                'has_labels': labels_path is not None,
                'has_config': bool(cfg),
                'active': path.name == active,
                'bundle_labels': labels_path.name if labels_path else '',
                'bundle_config': 'model_config.json' if (self.root / 'model_config.json').exists() and str(cfg.get('model_filename', '') or '').strip() == path.name else '',
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
                payload = file_storage.read()
                if payload is None:
                    payload = b''
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
                    self.interpreter = None
                    self.active_model = 'none'
                    self.labels = []
            return True, 'Deleted: ' + ', '.join(removed)
        except Exception as exc:
            return False, f'Delete failed: {exc}'

    def _load_labels(self, filename: str, cfg: dict[str, Any] | None = None) -> list[str]:
        path = self._resolve_labels_path(filename, cfg)
        if path is None or not path.exists():
            return []
        return [line.strip() for line in path.read_text(encoding='utf-8').splitlines() if line.strip()]

    def _load_model_config(self, filename: str) -> dict[str, Any]:
        return self._resolve_bundle_config(filename)

    def deploy_model(self, filename: str, config_overrides: dict[str, Any] | None = None) -> tuple[bool, str]:
        if InterpreterType is None:
            return False, 'No TFLite interpreter is available on this system.'
        safe_name = Path(str(filename or '')).name
        path = self.root / safe_name
        if not safe_name or not path.exists() or path.suffix.lower() != '.tflite':
            return False, 'Model file does not exist.'
        try:
            interpreter = InterpreterType(model_path=str(path))
            interpreter.allocate_tensors()
        except Exception as exc:
            return False, f'Failed to load detector: {exc}'

        cfg = self._load_model_config(path.name)
        labels = self._load_labels(path.name, cfg)
        overrides = config_overrides or {}
        with self._lock:
            self.interpreter = interpreter
            self.active_model = path.name
            self.labels = labels
            self.confidence_threshold = max(0.01, min(0.99, float(overrides.get('confidence_threshold', cfg.get('confidence_threshold', self.confidence_threshold)))))
            self.iou_threshold = max(0.01, min(0.99, float(overrides.get('iou_threshold', cfg.get('iou_threshold', self.iou_threshold)))))
            self.overlay_enabled = bool(overrides.get('overlay_enabled', cfg.get('overlay_enabled', self.overlay_enabled)))
            self.max_overlay_fps = max(0.5, min(30.0, float(overrides.get('max_overlay_fps', cfg.get('max_overlay_fps', self.max_overlay_fps)))))
            self._cache_window_s = 1.0 / max(self.max_overlay_fps, 0.5)
            self.last_error = ''
            self.last_inference_ms = 0.0
            self._last_result = {'detections': [], 'timestamp': 0.0}
        return True, f'Deployed detector: {path.name}'

    def get_active_model_name(self) -> str:
        with self._lock:
            return self.active_model

    def get_status(self) -> dict[str, Any]:
        with self._lock:
            return {
                'active_model': self.active_model,
                'overlay_enabled': bool(self.overlay_enabled),
                'confidence_threshold': float(self.confidence_threshold),
                'iou_threshold': float(self.iou_threshold),
                'max_overlay_fps': float(self.max_overlay_fps),
                'last_error': str(self.last_error),
                'last_inference_ms': float(self.last_inference_ms),
                'ready': self.interpreter is not None,
                'models': self.list_models(),
                'last_detections': list(self._last_result.get('detections', [])),
            }

    def _letterbox(self, image, new_shape: int):
        h, w = image.shape[:2]
        scale = min(new_shape / max(h, 1), new_shape / max(w, 1))
        nh, nw = int(round(h * scale)), int(round(w * scale))
        resized = cv2.resize(image, (nw, nh), interpolation=cv2.INTER_LINEAR)
        top = (new_shape - nh) // 2
        bottom = new_shape - nh - top
        left = (new_shape - nw) // 2
        right = new_shape - nw - left
        padded = cv2.copyMakeBorder(resized, top, bottom, left, right, cv2.BORDER_CONSTANT, value=(114, 114, 114))
        return padded, scale, (left, top)

    def _preprocess(self, image, size: int, dtype):
        padded, scale, pad = self._letterbox(image, size)
        rgb = cv2.cvtColor(padded, cv2.COLOR_BGR2RGB)
        arr = rgb.astype(np.float32) / 255.0
        if np.issubdtype(dtype, np.integer):
            arr = (arr * 255.0).clip(0, 255).astype(dtype)
        else:
            arr = arr.astype(dtype)
        arr = np.expand_dims(arr, axis=0)
        return arr, scale, pad

    def _xywh_to_xyxy(self, box):
        x, y, w, h = box
        return np.array([x - w / 2.0, y - h / 2.0, x + w / 2.0, y + h / 2.0], dtype=np.float32)

    def _scale_boxes(self, boxes, scale: float, pad: tuple[float, float], orig_shape: tuple[int, int]):
        if boxes.size == 0:
            return boxes
        boxes = boxes.copy()
        boxes[:, [0, 2]] -= pad[0]
        boxes[:, [1, 3]] -= pad[1]
        boxes /= max(scale, 1e-6)
        h, w = orig_shape
        boxes[:, [0, 2]] = boxes[:, [0, 2]].clip(0, w - 1)
        boxes[:, [1, 3]] = boxes[:, [1, 3]].clip(0, h - 1)
        return boxes

    def _nms(self, boxes, scores, iou_threshold: float) -> list[int]:
        if len(boxes) == 0:
            return []
        boxes_xywh = []
        for box in boxes:
            x1, y1, x2, y2 = box.tolist()
            boxes_xywh.append([float(x1), float(y1), float(max(0.0, x2 - x1)), float(max(0.0, y2 - y1))])
        idxs = cv2.dnn.NMSBoxes(boxes_xywh, scores.tolist(), score_threshold=0.0, nms_threshold=iou_threshold)
        if idxs is None or len(idxs) == 0:
            return []
        return np.array(idxs).reshape(-1).astype(int).tolist()

    def _normalize_prediction_matrix(self, arr):
        if arr.ndim != 2:
            return None
        rows, cols = arr.shape
        def looks_like_feature_dim(n: int) -> bool:
            return 5 <= int(n) <= 512
        if looks_like_feature_dim(cols) and not looks_like_feature_dim(rows):
            return arr
        if looks_like_feature_dim(rows) and not looks_like_feature_dim(cols):
            return arr.T
        if cols <= rows:
            return arr
        return arr.T

    def _parse_output(self, output, conf_threshold: float, num_classes: int, input_size: int):
        arr = np.squeeze(output)
        if arr.ndim == 3:
            arr = np.squeeze(arr, axis=0)
        if arr.ndim == 2 and arr.shape[-1] == 6:
            boxes = arr[:, :4].astype(np.float32)
            scores = arr[:, 4].astype(np.float32)
            classes = arr[:, 5].astype(np.int32)
            keep = scores >= conf_threshold
            return boxes[keep], scores[keep], classes[keep]
        arr = self._normalize_prediction_matrix(arr)
        if arr is None or arr.ndim != 2 or arr.shape[1] < 5:
            return np.empty((0, 4), dtype=np.float32), np.empty((0,), dtype=np.float32), np.empty((0,), dtype=np.int32)

        feature_count = int(arr.shape[1])
        expected_with_obj = int(num_classes) + 5 if num_classes > 0 else -1
        expected_no_obj = int(num_classes) + 4 if num_classes > 0 else -1
        if feature_count == expected_with_obj:
            has_obj = True
        elif feature_count == expected_no_obj:
            has_obj = False
        else:
            has_obj = feature_count >= 6

        boxes = []
        scores = []
        class_ids = []
        for row in arr:
            if has_obj:
                obj_conf = float(row[4])
                cls_scores = row[5:]
                class_id = int(np.argmax(cls_scores)) if len(cls_scores) else 0
                score = obj_conf * float(cls_scores[class_id]) if len(cls_scores) else obj_conf
            else:
                cls_scores = row[4:]
                class_id = int(np.argmax(cls_scores)) if len(cls_scores) else 0
                score = float(cls_scores[class_id]) if len(cls_scores) else 0.0
            if score < conf_threshold:
                continue
            box = row[:4].astype(np.float32)
            if np.max(box) <= 2.0:
                box[[0, 2]] *= input_size
                box[[1, 3]] *= input_size
            boxes.append(self._xywh_to_xyxy(box))
            scores.append(score)
            class_ids.append(class_id)
        if not boxes:
            return np.empty((0, 4), dtype=np.float32), np.empty((0,), dtype=np.float32), np.empty((0,), dtype=np.int32)
        return np.stack(boxes).astype(np.float32), np.array(scores, dtype=np.float32), np.array(class_ids, dtype=np.int32)

    def _infer_frame(self, frame_bgr):
        with self._lock:
            interpreter = self.interpreter
            conf = float(self.confidence_threshold)
            iou = float(self.iou_threshold)
            labels = list(self.labels)
        if interpreter is None or cv2 is None or np is None or frame_bgr is None:
            return []
        input_details = interpreter.get_input_details()[0]
        output_details = interpreter.get_output_details()[0]
        size = int(input_details['shape'][1])
        inp, scale, pad = self._preprocess(frame_bgr, size, input_details['dtype'])
        start = time.perf_counter()
        interpreter.set_tensor(input_details['index'], inp)
        interpreter.invoke()
        output = interpreter.get_tensor(output_details['index'])
        boxes, scores, classes = self._parse_output(output, conf, len(labels), size)
        boxes = self._scale_boxes(boxes, scale, pad, frame_bgr.shape[:2])
        keep = self._nms(boxes, scores, iou)
        detections: list[dict[str, Any]] = []
        if keep:
            boxes = boxes[keep]
            scores = scores[keep]
            classes = classes[keep]
            for box, score, class_id in zip(boxes, scores, classes):
                x1, y1, x2, y2 = box.astype(int).tolist()
                name = labels[class_id] if 0 <= int(class_id) < len(labels) else str(int(class_id))
                detections.append({
                    'label': name,
                    'score': round(float(score), 4),
                    'class_id': int(class_id),
                    'box': [int(x1), int(y1), int(x2), int(y2)],
                })
        elapsed_ms = (time.perf_counter() - start) * 1000.0
        with self._lock:
            self.last_inference_ms = elapsed_ms
            self.last_error = ''
            self._last_result = {'detections': detections, 'timestamp': time.monotonic()}
        return detections

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
        meta = f'OD {self.get_active_model_name()}' if self.get_active_model_name() != 'none' else 'OD off'
        cv2.putText(out, meta, (10, 22), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (0, 255, 0), 2, cv2.LINE_AA)
        return out

    def annotate_frame_jpeg(self, frame_bgr) -> tuple[bytes | None, list[dict[str, Any]]]:
        if frame_bgr is None or cv2 is None or np is None:
            return None, []
        detections: list[dict[str, Any]]
        with self._lock:
            ready = self.interpreter is not None and self.overlay_enabled
            last_ts = float(self._last_result.get('timestamp', 0.0))
            cache_window = float(self._cache_window_s)
            detections = list(self._last_result.get('detections', []))
        if ready:
            now = time.monotonic()
            if now - last_ts >= cache_window:
                try:
                    detections = self._infer_frame(frame_bgr)
                except Exception as exc:
                    with self._lock:
                        self.last_error = f'Inference failed: {exc}'
                    detections = []
            annotated = self._draw_overlay(frame_bgr, detections)
        else:
            annotated = frame_bgr
        ok, encoded = cv2.imencode('.jpg', annotated, [int(cv2.IMWRITE_JPEG_QUALITY), 72])
        return (encoded.tobytes() if ok else None), detections
