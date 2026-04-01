from __future__ import annotations

import json
import threading
from dataclasses import dataclass
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


def _normalize_output_2d(output: np.ndarray) -> tuple[np.ndarray, str]:
    arr = np.squeeze(output)
    if arr.ndim == 3:
        arr = np.squeeze(arr, axis=0)
    if arr.ndim != 2:
        return np.empty((0, 0), dtype=np.float32), 'invalid'
    layout = 'as_is'
    # Ultralytics exports commonly arrive as [channels, anchors], e.g. [6, 8400].
    # Detect that even when labels.txt is missing.
    if arr.shape[0] < arr.shape[1] and arr.shape[0] <= 256:
        arr = arr.T
        layout = 'transposed'
    return arr, layout


def _decode_rows(arr: np.ndarray, *, conf_threshold: float, input_size: int, has_obj: bool) -> tuple[np.ndarray, np.ndarray, np.ndarray, dict[str, Any]]:
    boxes = []
    scores = []
    class_ids = []
    max_score = 0.0
    row_width = int(arr.shape[1]) if arr.ndim == 2 else 0
    class_count = max(0, row_width - (5 if has_obj else 4))
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
        max_score = max(max_score, score)
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
        return (
            np.empty((0, 4), dtype=np.float32),
            np.empty((0,), dtype=np.float32),
            np.empty((0,), dtype=np.int32),
            {
                'candidate_count': int(arr.shape[0]) if arr.ndim == 2 else 0,
                'decoded_count': 0,
                'class_count': class_count,
                'score_max': float(max_score),
                'score_mean': 0.0,
                'has_objectness': has_obj,
            },
        )
    score_arr = np.array(scores, dtype=np.float32)
    return (
        np.stack(boxes).astype(np.float32),
        score_arr,
        np.array(class_ids, dtype=np.int32),
        {
            'candidate_count': int(arr.shape[0]),
            'decoded_count': len(boxes),
            'class_count': class_count,
            'score_max': float(max_score),
            'score_mean': float(score_arr.mean()) if len(score_arr) else 0.0,
            'has_objectness': has_obj,
        },
    )


def _coerce_xyxy(box: np.ndarray, *, input_size: int, order: str) -> np.ndarray:
    coords = box.astype(np.float32).copy()
    if np.max(np.abs(coords)) <= 2.0:
        coords *= float(input_size)
    if order == 'xyxy':
        x1, y1, x2, y2 = coords.tolist()
    else:
        y1, x1, y2, x2 = coords.tolist()
    if x2 < x1:
        x1, x2 = x2, x1
    if y2 < y1:
        y1, y2 = y2, y1
    return np.array([x1, y1, x2, y2], dtype=np.float32)


def _column_profile(values: np.ndarray) -> dict[str, Any]:
    finite = values[np.isfinite(values)].astype(np.float32)
    if finite.size == 0:
        return {
            'min': 0.0,
            'max': 0.0,
            'mean': 0.0,
            'non_negative_ratio': 0.0,
            'in_unit_ratio': 0.0,
            'integer_like_ratio': 0.0,
            'unique_count': 0,
        }
    rounded = np.round(finite)
    integer_like = np.abs(finite - rounded) <= 1e-3
    return {
        'min': float(finite.min()),
        'max': float(finite.max()),
        'mean': float(finite.mean()),
        'non_negative_ratio': float(np.mean(finite >= 0.0)),
        'in_unit_ratio': float(np.mean((finite >= 0.0) & (finite <= 1.05))),
        'integer_like_ratio': float(np.mean(integer_like)),
        'unique_count': int(len(np.unique(rounded if np.any(integer_like) else np.round(finite, 3)))),
    }


def _six_col_variant_rank(info: dict[str, Any]) -> tuple[float, ...]:
    score_profile = dict(info.get('score_profile', {}) or {})
    class_profile = dict(info.get('class_profile', {}) or {})
    score_max = float(info.get('score_max', 0.0) or 0.0)
    score_unit_ratio = float(score_profile.get('in_unit_ratio', 0.0) or 0.0)
    score_integer_ratio = float(score_profile.get('integer_like_ratio', 0.0) or 0.0)
    class_integer_ratio = float(class_profile.get('integer_like_ratio', 0.0) or 0.0)
    class_non_negative_ratio = float(class_profile.get('non_negative_ratio', 0.0) or 0.0)
    class_unique_count = int(class_profile.get('unique_count', 0) or 0)
    decoded_count = int(info.get('decoded_count', 0) or 0)
    class_count = int(info.get('class_count', 0) or 0)
    plausible_score = 1.0 if score_max <= 1.05 else (0.5 if score_max <= 1.5 else 0.0)
    score_penalty = 0.0 if score_max <= 1.05 else min(score_max, 100.0)
    unique_bonus = 1.0 if class_unique_count <= max(class_count + 2, 8) else 0.0
    return (
        plausible_score,
        score_unit_ratio,
        class_integer_ratio,
        class_non_negative_ratio,
        unique_bonus,
        float(decoded_count),
        -score_integer_ratio,
        -score_penalty,
        1.0 if str(info.get('coord_order', 'xyxy')) == 'xyxy' else 0.0,
    )


def _decode_six_column_variant(
    arr: np.ndarray,
    *,
    conf_threshold: float,
    num_classes: int,
    input_size: int,
    score_col: int,
    class_col: int,
    coord_order: str,
    variant_name: str,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, dict[str, Any]]:
    if arr.ndim != 2 or arr.shape[1] != 6:
        return np.empty((0, 4), dtype=np.float32), np.empty((0,), dtype=np.float32), np.empty((0,), dtype=np.int32), {
            'candidate_count': 0,
            'decoded_count': 0,
            'class_count': int(max(num_classes, 0)),
            'score_max': 0.0,
            'score_mean': 0.0,
            'score_col': int(score_col),
            'class_col': int(class_col),
            'coord_order': coord_order,
            'selected_variant': variant_name,
            'score_profile': _column_profile(np.empty((0,), dtype=np.float32)),
            'class_profile': _column_profile(np.empty((0,), dtype=np.float32)),
        }
    score_values = arr[:, score_col].astype(np.float32)
    class_values = arr[:, class_col].astype(np.float32)
    score_profile = _column_profile(score_values)
    class_profile = _column_profile(class_values)
    finite_scores = score_values[np.isfinite(score_values)]
    score_max = float(finite_scores.max()) if finite_scores.size else 0.0
    score_mean = float(finite_scores.mean()) if finite_scores.size else 0.0
    keep = np.isfinite(score_values) & (score_values >= conf_threshold)
    kept_idx = np.where(keep)[0]
    boxes = []
    scores = []
    class_ids = []
    inferred_class_count = int(max(num_classes, 0))
    for idx in kept_idx.tolist():
        row = arr[idx]
        class_id = int(max(0.0, round(float(class_values[idx]))))
        inferred_class_count = max(inferred_class_count, class_id + 1)
        boxes.append(_coerce_xyxy(row[:4], input_size=input_size, order=coord_order))
        scores.append(float(score_values[idx]))
        class_ids.append(class_id)
    if not boxes:
        inferred = class_values[np.isfinite(class_values)]
        if inferred.size:
            inferred_class_count = max(inferred_class_count, int(np.max(np.round(inferred))) + 1)
        return (
            np.empty((0, 4), dtype=np.float32),
            np.empty((0,), dtype=np.float32),
            np.empty((0,), dtype=np.int32),
            {
                'candidate_count': int(arr.shape[0]),
                'decoded_count': 0,
                'class_count': inferred_class_count,
                'score_max': score_max,
                'score_mean': score_mean,
                'score_col': int(score_col),
                'class_col': int(class_col),
                'coord_order': coord_order,
                'selected_variant': variant_name,
                'score_profile': score_profile,
                'class_profile': class_profile,
            },
        )
    score_arr = np.array(scores, dtype=np.float32)
    return (
        np.stack(boxes).astype(np.float32),
        score_arr,
        np.array(class_ids, dtype=np.int32),
        {
            'candidate_count': int(arr.shape[0]),
            'decoded_count': len(boxes),
            'class_count': inferred_class_count,
            'score_max': float(score_arr.max()) if score_arr.size else score_max,
            'score_mean': float(score_arr.mean()) if score_arr.size else score_mean,
            'score_col': int(score_col),
            'class_col': int(class_col),
            'coord_order': coord_order,
            'selected_variant': variant_name,
            'score_profile': score_profile,
            'class_profile': class_profile,
        },
    )


def parse_output(output: np.ndarray, conf_threshold: float, num_classes: int, input_size: int, model_type: str = 'yolo_detect'):
    debug: dict[str, Any] = {
        'raw_shape': list(np.asarray(output).shape),
        'layout': 'invalid',
        'selected_variant': 'none',
        'candidate_count': 0,
        'decoded_count': 0,
        'class_count': int(max(num_classes, 0)),
        'score_max': 0.0,
        'score_mean': 0.0,
        'score_col': -1,
        'class_col': -1,
        'coord_order': 'unknown',
    }
    arr, layout = _normalize_output_2d(output)
    debug['layout'] = layout
    if arr.size == 0:
        return np.empty((0, 4), dtype=np.float32), np.empty((0,), dtype=np.float32), np.empty((0,), dtype=np.int32), debug

    if arr.ndim == 2 and arr.shape[-1] == 6:
        variants = []
        variant_summaries = []
        for score_col, class_col, coord_order, variant_name in [
            (4, 5, 'xyxy', 'xyxy_score_class'),
            (5, 4, 'xyxy', 'xyxy_class_score'),
            (4, 5, 'yxyx', 'yxyx_score_class'),
            (5, 4, 'yxyx', 'yxyx_class_score'),
        ]:
            boxes_v, scores_v, classes_v, info_v = _decode_six_column_variant(
                arr,
                conf_threshold=conf_threshold,
                num_classes=num_classes,
                input_size=input_size,
                score_col=score_col,
                class_col=class_col,
                coord_order=coord_order,
                variant_name=variant_name,
            )
            rank = _six_col_variant_rank(info_v)
            variants.append((rank, variant_name, boxes_v, scores_v, classes_v, info_v))
            variant_summaries.append({
                'name': variant_name,
                'decoded_count': int(info_v.get('decoded_count', 0)),
                'score_max': float(info_v.get('score_max', 0.0)),
                'score_mean': float(info_v.get('score_mean', 0.0)),
                'score_col': int(info_v.get('score_col', -1)),
                'class_col': int(info_v.get('class_col', -1)),
                'coord_order': str(info_v.get('coord_order', 'unknown')),
                'score_in_unit_ratio': float((info_v.get('score_profile', {}) or {}).get('in_unit_ratio', 0.0)),
                'score_integer_like_ratio': float((info_v.get('score_profile', {}) or {}).get('integer_like_ratio', 0.0)),
                'class_integer_like_ratio': float((info_v.get('class_profile', {}) or {}).get('integer_like_ratio', 0.0)),
                'class_unique_count': int((info_v.get('class_profile', {}) or {}).get('unique_count', 0)),
            })
        selected = max(variants, key=lambda item: item[0])
        _, variant_name, boxes, scores, classes, info = selected
        debug.update(info)
        debug['selected_variant'] = variant_name
        debug['variant_candidates'] = variant_summaries
        return boxes, scores, classes, debug

    if arr.ndim != 2 or arr.shape[1] < 5:
        debug['selected_variant'] = 'unsupported'
        return np.empty((0, 4), dtype=np.float32), np.empty((0,), dtype=np.float32), np.empty((0,), dtype=np.int32), debug

    preferred_noobj = model_type in {'yolo_detect', 'yolo', 'ultralytics', 'ultralytics_yolo'}
    variants: list[tuple[str, np.ndarray, np.ndarray, np.ndarray, dict[str, Any]]] = []
    if arr.shape[1] > 4:
        boxes_noobj, scores_noobj, classes_noobj, info_noobj = _decode_rows(arr, conf_threshold=conf_threshold, input_size=input_size, has_obj=False)
        variants.append(('no_objectness', boxes_noobj, scores_noobj, classes_noobj, info_noobj))
    if arr.shape[1] > 5:
        boxes_obj, scores_obj, classes_obj, info_obj = _decode_rows(arr, conf_threshold=conf_threshold, input_size=input_size, has_obj=True)
        variants.append(('with_objectness', boxes_obj, scores_obj, classes_obj, info_obj))

    selected = None
    if preferred_noobj:
        for variant in variants:
            if variant[0] == 'no_objectness':
                selected = variant
                break
    else:
        for variant in variants:
            if variant[0] == 'with_objectness':
                selected = variant
                break
    if selected is None and variants:
        selected = max(variants, key=lambda item: (item[4].get('decoded_count', 0), item[4].get('score_max', 0.0)))
    if selected is None:
        debug['selected_variant'] = 'none'
        return np.empty((0, 4), dtype=np.float32), np.empty((0,), dtype=np.float32), np.empty((0,), dtype=np.int32), debug

    variant_name, boxes, scores, classes, info = selected
    for alt in variants:
        if alt is selected:
            continue
        if alt[4].get('decoded_count', 0) > info.get('decoded_count', 0):
            variant_name, boxes, scores, classes, info = alt
            break
    debug.update(info)
    debug['selected_variant'] = variant_name
    return boxes, scores, classes, debug


class TFLitePerception:
    def __init__(self, *, base_dir: str | Path | None = None):
        self.base_dir = Path(base_dir).resolve() if base_dir is not None else None
        self._lock = threading.RLock()
        self.interpreter = None
        self.bundle: ResolvedBundle | None = None
        self.labels: list[str] = []
        self.labels_mode = 'missing'
        self.model_type = 'yolo_detect'
        self.confidence_threshold = 0.25
        self.iou_threshold = 0.45
        self.configured_input_size = 0
        self.resolved_input_size = 0
        self.last_error = ''
        self.last_inference_ms = 0.0
        self.last_detections: list[Detection] = []
        self.debug_info: dict[str, Any] = {
            'input_shape': [],
            'input_dtype': '',
            'output_shapes': [],
            'output_dtypes': [],
            'layout': 'unknown',
            'selected_variant': 'none',
            'candidate_count': 0,
            'decoded_count': 0,
            'nms_count': 0,
            'class_count': 0,
            'score_max': 0.0,
            'score_mean': 0.0,
        }

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
        loaded_labels = load_labels(bundle.labels_path)
        labels_mode = 'file' if loaded_labels else 'missing'
        model_type = str(config.get('model_type', 'yolo_detect') or 'yolo_detect').strip() or 'yolo_detect'
        configured_size = int(input_size or config.get('image_size', 0) or 0)
        input_details = interpreter.get_input_details()[0]
        output_details = interpreter.get_output_details()
        try:
            tensor_size = int(input_details['shape'][1])
        except Exception:
            tensor_size = 0
        resolved_size = tensor_size or configured_size or 640

        with self._lock:
            self.interpreter = interpreter
            self.bundle = bundle
            self.labels = loaded_labels
            self.labels_mode = labels_mode
            self.model_type = model_type
            self.confidence_threshold = float(confidence_threshold if confidence_threshold is not None else config.get('confidence_threshold', 0.25))
            self.iou_threshold = float(iou_threshold if iou_threshold is not None else config.get('iou_threshold', 0.45))
            self.configured_input_size = configured_size
            self.resolved_input_size = resolved_size
            self.last_error = ''
            self.last_detections = []
            self.last_inference_ms = 0.0
            self.debug_info = {
                'input_shape': [int(v) for v in input_details.get('shape', [])],
                'input_dtype': str(input_details.get('dtype', '')),
                'output_shapes': [[int(v) for v in detail.get('shape', [])] for detail in output_details],
                'output_dtypes': [str(detail.get('dtype', '')) for detail in output_details],
                'layout': 'unknown',
                'selected_variant': 'none',
                'candidate_count': 0,
                'decoded_count': 0,
                'nms_count': 0,
                'class_count': len(loaded_labels),
                'score_max': 0.0,
                'score_mean': 0.0,
            }
        return True, f'Deployed detector: {bundle.model_path.name}'

    def clear(self) -> None:
        with self._lock:
            self.interpreter = None
            self.bundle = None
            self.labels = []
            self.labels_mode = 'missing'
            self.last_detections = []
            self.last_error = ''
            self.last_inference_ms = 0.0
            self.debug_info = {
                'input_shape': [],
                'input_dtype': '',
                'output_shapes': [],
                'output_dtypes': [],
                'layout': 'unknown',
                'selected_variant': 'none',
                'candidate_count': 0,
                'decoded_count': 0,
                'nms_count': 0,
                'class_count': 0,
                'score_max': 0.0,
                'score_mean': 0.0,
            }

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
                'labels_mode': self.labels_mode,
                'model_type': self.model_type,
                'confidence_threshold': float(self.confidence_threshold),
                'iou_threshold': float(self.iou_threshold),
                'configured_input_size': int(self.configured_input_size),
                'resolved_input_size': int(self.resolved_input_size),
                'last_error': str(self.last_error),
                'last_inference_ms': float(self.last_inference_ms),
                'debug': dict(self.debug_info),
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
        output_details = interpreter.get_output_details()
        output_detail = max(output_details, key=lambda detail: int(np.prod(detail.get('shape', [1]))))
        tensor_size = int(input_details['shape'][1]) if len(input_details.get('shape', [])) > 1 else 0
        size = tensor_size or resolved_input_size or 640
        inp, scale, pad = preprocess(frame_bgr, size, input_details['dtype'])
        start = cv2.getTickCount() if cv2 is not None else 0.0
        interpreter.set_tensor(input_details['index'], inp)
        interpreter.invoke()
        output = np.array(interpreter.get_tensor(output_detail['index']), copy=True)
        quant = output_detail.get('quantization_parameters') or {}
        scales = np.array(quant.get('scales', []), dtype=np.float32) if np is not None else None
        zero_points = np.array(quant.get('zero_points', []), dtype=np.float32) if np is not None else None
        if np is not None and np.issubdtype(output.dtype, np.integer):
            if scales is not None and scales.size:
                scale_value = float(scales.reshape(-1)[0])
                zero_value = float(zero_points.reshape(-1)[0]) if zero_points is not None and zero_points.size else 0.0
                output = (output.astype(np.float32) - zero_value) * scale_value
            else:
                output = output.astype(np.float32)
        boxes, scores, classes, parse_debug = parse_output(output, conf, len(labels), size, model_type=model_type)
        boxes = scale_boxes(boxes, scale, pad, frame_bgr.shape[:2])
        keep = nms(boxes, scores, iou)
        detections: list[Detection] = []
        if keep:
            for idx in keep:
                box = boxes[idx]
                x1, y1, x2, y2 = box.astype(float).tolist()
                class_id = int(classes[idx])
                label = labels[class_id] if 0 <= class_id < len(labels) else f'class_{class_id}'
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
            inferred_class_count = int(parse_debug.get('class_count', len(labels)))
            if not self.labels and inferred_class_count > 0:
                self.labels = [f'class_{idx}' for idx in range(inferred_class_count)]
                self.labels_mode = 'synthetic'
                labels = list(self.labels)
                for det in detections:
                    try:
                        class_id = int(det.label.split('_')[-1]) if det.label.startswith('class_') else -1
                    except Exception:
                        class_id = -1
                    if 0 <= class_id < len(labels):
                        det.label = labels[class_id]
            self.last_inference_ms = float(elapsed_ms)
            self.last_detections = list(detections)
            self.last_error = ''
            self.debug_info = {
                **self.debug_info,
                'layout': parse_debug.get('layout', 'unknown'),
                'selected_variant': parse_debug.get('selected_variant', 'none'),
                'candidate_count': int(parse_debug.get('candidate_count', 0)),
                'decoded_count': int(parse_debug.get('decoded_count', 0)),
                'nms_count': int(len(keep)),
                'class_count': inferred_class_count,
                'score_max': float(parse_debug.get('score_max', 0.0)),
                'score_mean': float(parse_debug.get('score_mean', 0.0)),
                'raw_shape': parse_debug.get('raw_shape', []),
                'score_col': int(parse_debug.get('score_col', -1)),
                'class_col': int(parse_debug.get('class_col', -1)),
                'coord_order': str(parse_debug.get('coord_order', 'unknown')),
            }
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
