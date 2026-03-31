from __future__ import annotations

import json
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

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

from .models import BoundingBox, Detection, FramePerception


@dataclass(slots=True)
class ResolvedBundle:
    model_path: Path
    labels_path: Path | None
    config_path: Path | None
    config: dict[str, Any]


def tflite_runtime_available() -> tuple[bool, str]:
    if cv2 is None:
        return False, 'OpenCV is not available.'
    if np is None:
        return False, 'NumPy is not available.'
    if InterpreterType is None:
        return False, 'No TFLite interpreter is available on this system.'
    return True, 'ready'


def _safe_read_json(path: Path | None) -> dict[str, Any]:
    if path is None or not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding='utf-8'))
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def load_labels(path: Path | None) -> list[str]:
    if path is None or not path.exists():
        return []
    try:
        return [line.strip() for line in path.read_text(encoding='utf-8').splitlines() if line.strip()]
    except Exception:
        return []


def _coerce_path(value: str | Path | None, *, base_dir: Path | None = None) -> Path | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    path = Path(text).expanduser()
    if path.is_absolute():
        return path
    if base_dir is not None:
        return (base_dir / path).resolve()
    return path.resolve()


def resolve_bundle(model_path: str | Path, labels_path: str | Path | None = None, *, base_dir: str | Path | None = None) -> ResolvedBundle:
    base = Path(base_dir).resolve() if base_dir is not None else None
    model = _coerce_path(model_path, base_dir=base)
    if model is None:
        raise FileNotFoundError('No model path configured.')
    if not model.exists():
        raise FileNotFoundError(f'Model file does not exist: {model}')

    explicit_labels = _coerce_path(labels_path, base_dir=model.parent if labels_path else base)
    same_stem_config = model.with_suffix('.json')
    bundle_config = model.parent / 'model_config.json'
    config_path: Path | None = None
    config: dict[str, Any] = {}
    if same_stem_config.exists():
        config_path = same_stem_config
        config = _safe_read_json(same_stem_config)
    elif bundle_config.exists():
        bundle = _safe_read_json(bundle_config)
        model_filename = str(bundle.get('model_filename', '') or '').strip()
        if not model_filename or model_filename == model.name:
            config_path = bundle_config
            config = bundle

    resolved_labels = explicit_labels
    if resolved_labels is None:
        labels_filename = str(config.get('labels_filename', '') or '').strip()
        if labels_filename:
            candidate = (model.parent / Path(labels_filename).name).resolve()
            if candidate.exists():
                resolved_labels = candidate
        if resolved_labels is None:
            candidate = model.with_suffix('.txt')
            if candidate.exists():
                resolved_labels = candidate.resolve()
        if resolved_labels is None:
            candidate = model.parent / 'labels.txt'
            if candidate.exists():
                resolved_labels = candidate.resolve()

    return ResolvedBundle(
        model_path=model.resolve(),
        labels_path=resolved_labels.resolve() if resolved_labels is not None and resolved_labels.exists() else None,
        config_path=config_path.resolve() if config_path is not None and config_path.exists() else None,
        config=config,
    )


def letterbox(image, new_shape: int):
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


def preprocess(image, size: int, dtype):
    padded, scale, pad = letterbox(image, size)
    rgb = cv2.cvtColor(padded, cv2.COLOR_BGR2RGB)
    arr = rgb.astype(np.float32) / 255.0
    if np.issubdtype(dtype, np.integer):
        arr = (arr * 255.0).clip(0, 255).astype(dtype)
    else:
        arr = arr.astype(dtype)
    arr = np.expand_dims(arr, axis=0)
    return arr, scale, pad


def xywh_to_xyxy(box):
    x, y, w, h = box
    return np.array([x - w / 2.0, y - h / 2.0, x + w / 2.0, y + h / 2.0], dtype=np.float32)


def scale_boxes(boxes, scale: float, pad: tuple[float, float], orig_shape: tuple[int, int]):
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


def nms(boxes, scores, iou_threshold: float) -> list[int]:
    if len(boxes) == 0:
        return []
    boxes_xywh = []
    for box in boxes:
        x1, y1, x2, y2 = box.tolist()
        boxes_xywh.append([float(x1), float(y1), float(max(0.0, x2 - x1)), float(max(0.0, y2 - y1))])
    idxs = cv2.dnn.NMSBoxes(boxes_xywh, scores.tolist(), score_threshold=0.0, nms_threshold=iou_threshold)
    if idxs is None or len(idxs) == 0:
        return []
    idxs = np.array(idxs).reshape(-1).tolist()
    return [int(i) for i in idxs]


def parse_output(output, conf_threshold: float, num_classes: int, input_size: int, model_type: str = 'yolo_detect'):
    arr = np.squeeze(output)
    if arr.ndim == 3:
        arr = np.squeeze(arr, axis=0)

    if arr.ndim == 2 and arr.shape[-1] == 6:
        boxes = arr[:, :4].astype(np.float32)
        scores = arr[:, 4].astype(np.float32)
        classes = arr[:, 5].astype(np.int32)
        keep = scores >= conf_threshold
        return boxes[keep], scores[keep], classes[keep]

    if arr.ndim != 2:
        return np.empty((0, 4), dtype=np.float32), np.empty((0,), dtype=np.float32), np.empty((0,), dtype=np.int32)

    if arr.shape[0] in (num_classes + 4, num_classes + 5):
        arr = arr.T
    elif arr.shape[1] not in (num_classes + 4, num_classes + 5):
        if arr.shape[0] > arr.shape[1]:
            arr = arr.T

    has_obj = False if model_type in {'yolo_detect', 'yolo', 'ultralytics', 'ultralytics_yolo'} else arr.shape[1] == num_classes + 5
    if arr.shape[1] == num_classes + 5:
        has_obj = True
    elif arr.shape[1] == num_classes + 4:
        has_obj = False

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
        boxes.append(xywh_to_xyxy(box))
        scores.append(score)
        class_ids.append(class_id)

    if not boxes:
        return np.empty((0, 4), dtype=np.float32), np.empty((0,), dtype=np.float32), np.empty((0,), dtype=np.int32)

    return np.stack(boxes).astype(np.float32), np.array(scores, dtype=np.float32), np.array(class_ids, dtype=np.int32)


class TFLitePerception:
    def __init__(self, *, base_dir: str | Path | None = None):
        self.base_dir = Path(base_dir).resolve() if base_dir is not None else None
        self._lock = threading.RLock()
        self.interpreter = None
        self.bundle: ResolvedBundle | None = None
        self.labels: list[str] = []
        self.model_type = 'yolo_detect'
        self.confidence_threshold = 0.25
        self.iou_threshold = 0.45
        self.configured_input_size = 0
        self.resolved_input_size = 0
        self.last_error = ''
        self.last_inference_ms = 0.0
        self.last_detections: list[Detection] = []

    def deploy(
        self,
        model_path: str | Path,
        *,
        labels_path: str | Path | None = None,
        input_size: int | None = None,
        confidence_threshold: float | None = None,
        iou_threshold: float | None = None,
    ) -> tuple[bool, str]:
        ready, reason = tflite_runtime_available()
        if not ready:
            with self._lock:
                self.last_error = reason
            return False, reason
        try:
            bundle = resolve_bundle(model_path, labels_path, base_dir=self.base_dir)
        except Exception as exc:
            with self._lock:
                self.last_error = str(exc)
            return False, str(exc)

        try:
            interpreter = InterpreterType(model_path=str(bundle.model_path))
            interpreter.allocate_tensors()
        except Exception as exc:
            with self._lock:
                self.last_error = f'Failed to load detector: {exc}'
            return False, self.last_error

        config = bundle.config or {}
        labels = load_labels(bundle.labels_path)
        model_type = str(config.get('model_type', 'yolo_detect') or 'yolo_detect').strip() or 'yolo_detect'
        configured_size = int(input_size or config.get('image_size', 0) or 0)
        try:
            tensor_size = int(interpreter.get_input_details()[0]['shape'][1])
        except Exception:
            tensor_size = 0
        resolved_size = tensor_size or configured_size or 640

        with self._lock:
            self.interpreter = interpreter
            self.bundle = bundle
            self.labels = labels
            self.model_type = model_type
            self.confidence_threshold = float(confidence_threshold if confidence_threshold is not None else config.get('confidence_threshold', 0.25))
            self.iou_threshold = float(iou_threshold if iou_threshold is not None else config.get('iou_threshold', 0.45))
            self.configured_input_size = configured_size
            self.resolved_input_size = resolved_size
            self.last_error = ''
            self.last_detections = []
            self.last_inference_ms = 0.0
        return True, f'Deployed detector: {bundle.model_path.name}'

    def clear(self) -> None:
        with self._lock:
            self.interpreter = None
            self.bundle = None
            self.labels = []
            self.last_detections = []
            self.last_error = ''
            self.last_inference_ms = 0.0

    def is_ready(self) -> bool:
        with self._lock:
            return self.interpreter is not None

    def status(self) -> dict[str, Any]:
        with self._lock:
            return {
                'ready': self.interpreter is not None,
                'model_path': str(self.bundle.model_path) if self.bundle else '',
                'labels_path': str(self.bundle.labels_path) if self.bundle and self.bundle.labels_path else '',
                'config_path': str(self.bundle.config_path) if self.bundle and self.bundle.config_path else '',
                'labels': list(self.labels),
                'model_type': self.model_type,
                'confidence_threshold': float(self.confidence_threshold),
                'iou_threshold': float(self.iou_threshold),
                'configured_input_size': int(self.configured_input_size),
                'resolved_input_size': int(self.resolved_input_size),
                'last_error': str(self.last_error),
                'last_inference_ms': float(self.last_inference_ms),
            }

    def infer_detections(self, frame_bgr) -> list[Detection]:
        with self._lock:
            interpreter = self.interpreter
            bundle = self.bundle
            labels = list(self.labels)
            model_type = self.model_type
            conf = float(self.confidence_threshold)
            iou = float(self.iou_threshold)
            resolved_input_size = int(self.resolved_input_size)
        if interpreter is None or bundle is None or frame_bgr is None or cv2 is None or np is None:
            return []
        input_details = interpreter.get_input_details()[0]
        output_details = interpreter.get_output_details()[0]
        tensor_size = int(input_details['shape'][1]) if len(input_details.get('shape', [])) > 1 else 0
        size = tensor_size or resolved_input_size or 640
        inp, scale, pad = preprocess(frame_bgr, size, input_details['dtype'])
        start = cv2.getTickCount() if cv2 is not None else 0.0
        interpreter.set_tensor(input_details['index'], inp)
        interpreter.invoke()
        output = interpreter.get_tensor(output_details['index'])
        boxes, scores, classes = parse_output(output, conf, len(labels), size, model_type=model_type)
        boxes = scale_boxes(boxes, scale, pad, frame_bgr.shape[:2])
        keep = nms(boxes, scores, iou)
        detections: list[Detection] = []
        if keep:
            for idx in keep:
                box = boxes[idx]
                x1, y1, x2, y2 = box.astype(float).tolist()
                class_id = int(classes[idx])
                label = labels[class_id] if 0 <= class_id < len(labels) else str(class_id)
                detections.append(
                    Detection(
                        label=label,
                        confidence=float(scores[idx]),
                        box=BoundingBox(x1=x1, y1=y1, x2=x2, y2=y2),
                    )
                )
        if cv2 is not None:
            elapsed_ms = (cv2.getTickCount() - start) * 1000.0 / max(cv2.getTickFrequency(), 1.0)
        else:
            elapsed_ms = 0.0
        with self._lock:
            self.last_inference_ms = float(elapsed_ms)
            self.last_detections = list(detections)
            self.last_error = ''
        return detections

    def infer_frame(self, frame_bgr) -> FramePerception:
        frame_h = int(getattr(frame_bgr, 'shape', (0, 0, 0))[0] or 0)
        frame_w = int(getattr(frame_bgr, 'shape', (0, 0, 0))[1] or 0)
        detections = self.infer_detections(frame_bgr)
        return FramePerception(frame_width=frame_w, frame_height=frame_h, detections=detections)

    def labels_candidates(self) -> list[str]:
        if self.base_dir is None or not self.base_dir.exists():
            return []
        return sorted({path.name for path in self.base_dir.glob('*.txt') if path.is_file()})

    def model_candidates(self) -> list[str]:
        if self.base_dir is None or not self.base_dir.exists():
            return []
        return sorted({path.name for path in self.base_dir.glob('*.tflite') if path.is_file()})
