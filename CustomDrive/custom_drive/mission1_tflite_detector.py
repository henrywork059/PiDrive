from __future__ import annotations

import os
import threading
import uuid
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

try:
    from tflite_runtime.interpreter import Interpreter as _Interpreter  # type: ignore
except Exception:  # pragma: no cover
    try:
        from tensorflow.lite.python.interpreter import Interpreter as _Interpreter  # type: ignore
    except Exception:  # pragma: no cover
        _Interpreter = None  # type: ignore

from .models import BoundingBox, Detection


class Mission1TFLiteDetector:
    def __init__(self, root: str | Path):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self.interpreter = None
        self.active_name = 'none'
        self.labels: list[str] = []
        self.last_message = 'No model loaded.'

    def backend_ready(self) -> tuple[bool, str]:
        if cv2 is None:
            return False, 'OpenCV is not available.'
        if np is None:
            return False, 'NumPy is not available.'
        if _Interpreter is None:
            return False, 'No TFLite interpreter is available on this system.'
        return True, 'ready'

    def list_models(self) -> list[str]:
        return sorted([path.name for path in self.root.glob('*.tflite')])

    def save_uploaded_model(self, file_storage) -> tuple[bool, str]:
        filename = (getattr(file_storage, 'filename', '') or '').strip()
        safe_name = Path(filename).name
        if not safe_name or not safe_name.lower().endswith('.tflite'):
            return False, 'Only .tflite files are supported.'
        target = self.root / safe_name
        tmp_target = self.root / f'.{safe_name}.{uuid.uuid4().hex}.upload'
        try:
            file_storage.save(tmp_target)
            os.replace(tmp_target, target)
            self.last_message = f'Saved model: {safe_name}'
            return True, safe_name
        except Exception as exc:
            try:
                if tmp_target.exists():
                    tmp_target.unlink()
            except Exception:
                pass
            return False, f'Failed to save model: {exc}'

    def load_model(self, filename: str) -> tuple[bool, str]:
        ready, message = self.backend_ready()
        if not ready:
            self.last_message = message
            return False, message
        path = self.root / Path(str(filename or '')).name
        if not path.exists() or not path.is_file():
            self.last_message = 'Model file does not exist.'
            return False, self.last_message
        try:
            interpreter = _Interpreter(model_path=str(path))  # type: ignore[misc]
            interpreter.allocate_tensors()
        except Exception as exc:
            self.last_message = f'Failed to load model: {exc}'
            return False, self.last_message
        labels = self._load_labels_for_model(path)
        with self._lock:
            self.interpreter = interpreter
            self.active_name = path.name
            self.labels = labels
            self.last_message = f'Loaded model: {path.name}'
        return True, self.last_message

    def unload(self) -> None:
        with self._lock:
            self.interpreter = None
            self.active_name = 'none'
            self.labels = []
            self.last_message = 'Model unloaded.'

    def get_active_name(self) -> str:
        with self._lock:
            return self.active_name

    def detect(self, frame_bgr, conf_threshold: float = 0.25, iou_threshold: float = 0.45) -> list[Detection]:
        ready, _ = self.backend_ready()
        if not ready or frame_bgr is None or np is None or cv2 is None:
            return []
        with self._lock:
            interpreter = self.interpreter
            labels = list(self.labels)
        if interpreter is None:
            return []

        input_details = interpreter.get_input_details()[0]
        output_details = interpreter.get_output_details()[0]
        size = int(input_details['shape'][1])
        inp, scale, pad = self._preprocess(frame_bgr, size, input_details['dtype'])
        interpreter.set_tensor(input_details['index'], inp)
        interpreter.invoke()
        output = interpreter.get_tensor(output_details['index'])
        boxes, scores, classes = self._parse_output(output, float(conf_threshold), len(labels), size)
        boxes = self._scale_boxes(boxes, scale, pad, frame_bgr.shape[:2])
        keep = self._nms(boxes, scores, float(iou_threshold))
        if keep:
            boxes = boxes[keep]
            scores = scores[keep]
            classes = classes[keep]
        else:
            boxes = np.empty((0, 4), dtype=np.float32)
            scores = np.empty((0,), dtype=np.float32)
            classes = np.empty((0,), dtype=np.int32)

        detections: list[Detection] = []
        for box, score, class_id in zip(boxes, scores, classes):
            label = self._label_name(int(class_id), labels)
            detections.append(
                Detection(
                    label=label,
                    confidence=float(score),
                    box=BoundingBox(
                        x1=float(box[0]),
                        y1=float(box[1]),
                        x2=float(box[2]),
                        y2=float(box[3]),
                    ),
                )
            )
        return detections

    def _load_labels_for_model(self, model_path: Path) -> list[str]:
        candidates = [
            model_path.with_suffix('.txt'),
            model_path.with_name(model_path.stem + '_labels.txt'),
            self.root / 'labels.txt',
        ]
        for path in candidates:
            if not path.exists():
                continue
            try:
                lines = [line.strip() for line in path.read_text(encoding='utf-8').splitlines() if line.strip()]
            except Exception:
                lines = []
            if lines:
                return lines
        return []

    def _label_name(self, class_id: int, labels: list[str]) -> str:
        # Mission 1 target logic keys to the numeric class id so class 1 remains
        # stable even when an optional labels.txt uses different display names.
        return str(class_id)

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
        idxs = np.array(idxs).reshape(-1).tolist()
        return [int(item) for item in idxs]

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

        if arr.ndim != 2:
            return np.empty((0, 4), dtype=np.float32), np.empty((0,), dtype=np.float32), np.empty((0,), dtype=np.int32)

        if arr.shape[0] in (num_classes + 4, num_classes + 5):
            arr = arr.T
        elif arr.shape[1] not in (num_classes + 4, num_classes + 5):
            if arr.shape[0] > arr.shape[1]:
                arr = arr.T

        has_obj = arr.shape[1] == num_classes + 5
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
