from __future__ import annotations

from dataclasses import asdict
from typing import Any, Iterable
import time

try:
    import cv2
except Exception:  # pragma: no cover
    cv2 = None  # type: ignore

try:
    import numpy as np
except Exception:  # pragma: no cover
    np = None  # type: ignore

from .models import BoundingBox, Detection, FramePerception
from .tflite_perception import TFLitePerception, tflite_runtime_available


DEFAULT_PERCEPTION_SETTINGS: dict[str, Any] = {
    'enabled': True,
    'perception_backend': 'color',
    'model_path': '',
    'labels_path': '',
    'input_size': 0,
    'confidence_threshold': 0.25,
    'iou_threshold': 0.45,
    'target_label': 'he3',
    'drop_zone_label': 'he3_zone',
    'blur_kernel': 5,
    'open_iterations': 1,
    'close_iterations': 1,
    'min_box_area_ratio': 0.0025,
    'max_detections_per_label': 3,
    'labels': {
        'he3': {
            'ranges': [
                {'lower': [5, 100, 90], 'upper': [35, 255, 255]},
            ],
            'min_box_area_ratio': 0.0025,
        },
        'he3_zone': {
            'ranges': [
                {'lower': [90, 80, 70], 'upper': [135, 255, 255]},
            ],
            'min_box_area_ratio': 0.0040,
        },
    },
}


def _deep_merge(base: dict[str, Any], incoming: dict[str, Any]) -> dict[str, Any]:
    out = dict(base)
    for key, value in (incoming or {}).items():
        if isinstance(value, dict) and isinstance(out.get(key), dict):
            out[key] = _deep_merge(out[key], value)
        else:
            out[key] = value
    return out


def merge_perception_settings(data: dict[str, Any] | None) -> dict[str, Any]:
    merged = _deep_merge(DEFAULT_PERCEPTION_SETTINGS, data or {})
    merged['perception_backend'] = str(merged.get('perception_backend', 'color') or 'color').strip().lower() or 'color'
    if merged['perception_backend'] not in {'color', 'tflite'}:
        merged['perception_backend'] = 'color'
    merged['model_path'] = str(merged.get('model_path', '') or '').strip()
    merged['labels_path'] = str(merged.get('labels_path', '') or '').strip()
    merged['target_label'] = str(merged.get('target_label', 'he3') or 'he3').strip() or 'he3'
    merged['drop_zone_label'] = str(merged.get('drop_zone_label', 'he3_zone') or 'he3_zone').strip() or 'he3_zone'
    try:
        merged['input_size'] = max(0, int(merged.get('input_size', 0) or 0))
    except Exception:
        merged['input_size'] = 0
    try:
        merged['confidence_threshold'] = float(merged.get('confidence_threshold', 0.25) or 0.25)
    except Exception:
        merged['confidence_threshold'] = 0.25
    try:
        merged['iou_threshold'] = float(merged.get('iou_threshold', 0.45) or 0.45)
    except Exception:
        merged['iou_threshold'] = 0.45
    return merged


def perception_backend_ready(settings: dict[str, Any] | None = None) -> tuple[bool, str]:
    merged = merge_perception_settings(settings)
    backend = merged.get('perception_backend', 'color')
    if backend == 'tflite':
        ready, reason = tflite_runtime_available()
        if not ready:
            return False, reason
        if not merged.get('model_path'):
            return False, 'TFLite backend selected but no model path is configured.'
        return True, 'ready'
    if cv2 is None:
        return False, 'OpenCV is not available.'
    if np is None:
        return False, 'NumPy is not available.'
    return True, 'ready'


def _odd_kernel(value: Any, default: int = 5) -> int:
    try:
        kernel = int(value)
    except Exception:
        kernel = int(default)
    kernel = max(1, kernel)
    if kernel % 2 == 0:
        kernel += 1
    return kernel


def _normalize_range(item: dict[str, Any]) -> tuple[Any, Any] | None:
    if np is None:
        return None
    lower = item.get('lower')
    upper = item.get('upper')
    if not isinstance(lower, (list, tuple)) or not isinstance(upper, (list, tuple)):
        return None
    if len(lower) != 3 or len(upper) != 3:
        return None
    try:
        low = np.array([int(v) for v in lower], dtype=np.uint8)
        high = np.array([int(v) for v in upper], dtype=np.uint8)
        return low, high
    except Exception:
        return None


def _make_mask(hsv_frame, ranges: Iterable[dict[str, Any]]):
    if cv2 is None or np is None:
        return None
    mask = None
    for item in ranges:
        normalized = _normalize_range(item)
        if normalized is None:
            continue
        low, high = normalized
        current = cv2.inRange(hsv_frame, low, high)
        mask = current if mask is None else cv2.bitwise_or(mask, current)
    return mask


def _detect_label(frame_bgr, hsv_frame, label: str, spec: dict[str, Any], fallback_min_area_ratio: float) -> list[Detection]:
    if cv2 is None or np is None:
        return []

    ranges = spec.get('ranges') or []
    if not isinstance(ranges, list) or not ranges:
        return []

    mask = _make_mask(hsv_frame, ranges)
    if mask is None:
        return []

    blur_kernel = _odd_kernel(spec.get('blur_kernel', 5), 5)
    if blur_kernel > 1:
        mask = cv2.GaussianBlur(mask, (blur_kernel, blur_kernel), 0)
        _, mask = cv2.threshold(mask, 127, 255, cv2.THRESH_BINARY)

    open_iterations = max(0, int(spec.get('open_iterations', 1)))
    close_iterations = max(0, int(spec.get('close_iterations', 1)))
    kernel = np.ones((3, 3), dtype=np.uint8)
    if open_iterations:
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel, iterations=open_iterations)
    if close_iterations:
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel, iterations=close_iterations)

    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    frame_h, frame_w = frame_bgr.shape[:2]
    frame_area = float(max(1, frame_h * frame_w))
    min_area_ratio = float(spec.get('min_box_area_ratio', fallback_min_area_ratio))
    min_area = max(16.0, frame_area * min_area_ratio)
    max_dets = max(1, int(spec.get('max_detections_per_label', 3)))

    detections: list[Detection] = []
    for contour in contours:
        contour_area = float(cv2.contourArea(contour))
        if contour_area < min_area:
            continue
        x, y, w, h = cv2.boundingRect(contour)
        if w <= 1 or h <= 1:
            continue
        area_ratio = (w * h) / frame_area
        fill_ratio = contour_area / float(max(1, w * h))
        confidence = max(0.1, min(0.99, 0.35 + area_ratio * 12.0 + fill_ratio * 0.35))
        detections.append(
            Detection(
                label=label,
                confidence=confidence,
                box=BoundingBox(x1=float(x), y1=float(y), x2=float(x + w), y2=float(y + h)),
            )
        )

    detections.sort(key=lambda det: det.confidence * max(1.0, det.box.area), reverse=True)
    return detections[:max_dets]


def build_color_frame_perception(frame_bgr, settings: dict[str, Any] | None = None) -> FramePerception:
    frame_h = int(getattr(frame_bgr, 'shape', (0, 0, 0))[0] or 0)
    frame_w = int(getattr(frame_bgr, 'shape', (0, 0, 0))[1] or 0)
    perception = FramePerception(frame_width=frame_w, frame_height=frame_h, detections=[], timestamp=time.monotonic())

    if cv2 is None or np is None or frame_bgr is None or frame_w <= 0 or frame_h <= 0:
        return perception

    merged = merge_perception_settings(settings)
    if not bool(merged.get('enabled', True)):
        return perception

    hsv_frame = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2HSV)
    labels = merged.get('labels') or {}
    min_ratio = float(merged.get('min_box_area_ratio', 0.0025))

    detections: list[Detection] = []
    for label, spec in labels.items():
        if not isinstance(spec, dict):
            continue
        local_spec = _deep_merge(
            {
                'blur_kernel': merged.get('blur_kernel', 5),
                'open_iterations': merged.get('open_iterations', 1),
                'close_iterations': merged.get('close_iterations', 1),
                'max_detections_per_label': merged.get('max_detections_per_label', 3),
                'min_box_area_ratio': merged.get('min_box_area_ratio', 0.0025),
            },
            spec,
        )
        detections.extend(_detect_label(frame_bgr, hsv_frame, str(label), local_spec, min_ratio))

    perception.detections = detections
    return perception


def build_frame_perception(frame_bgr, settings: dict[str, Any] | None = None, *, tflite_backend: TFLitePerception | None = None) -> FramePerception:
    merged = merge_perception_settings(settings)
    if merged.get('perception_backend') == 'tflite':
        if tflite_backend is None:
            frame_h = int(getattr(frame_bgr, 'shape', (0, 0, 0))[0] or 0)
            frame_w = int(getattr(frame_bgr, 'shape', (0, 0, 0))[1] or 0)
            return FramePerception(frame_width=frame_w, frame_height=frame_h, detections=[], timestamp=time.monotonic())
        perception = tflite_backend.infer_frame(frame_bgr)
        perception.timestamp = time.monotonic()
        return perception
    return build_color_frame_perception(frame_bgr, merged)


def detections_as_dict(detections: Iterable[Detection]) -> list[dict[str, Any]]:
    payload: list[dict[str, Any]] = []
    for det in detections:
        payload.append({'label': det.label, 'confidence': det.confidence, 'box': asdict(det.box)})
    return payload
