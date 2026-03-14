from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Iterable

import cv2
import numpy as np

try:
    from tflite_runtime.interpreter import Interpreter
except Exception:
    from tensorflow.lite import Interpreter  # type: ignore


def load_labels(path: Path) -> list[str]:
    if not path.exists():
        return []
    return [line.strip() for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def letterbox(image: np.ndarray, new_shape: int) -> tuple[np.ndarray, float, tuple[float, float]]:
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


def preprocess(image: np.ndarray, size: int, dtype: np.dtype) -> tuple[np.ndarray, float, tuple[float, float]]:
    padded, scale, pad = letterbox(image, size)
    rgb = cv2.cvtColor(padded, cv2.COLOR_BGR2RGB)
    arr = rgb.astype(np.float32) / 255.0
    if np.issubdtype(dtype, np.integer):
        arr = (arr * 255.0).clip(0, 255).astype(dtype)
    else:
        arr = arr.astype(dtype)
    arr = np.expand_dims(arr, axis=0)
    return arr, scale, pad


def xywh_to_xyxy(box: np.ndarray) -> np.ndarray:
    x, y, w, h = box
    return np.array([x - w / 2.0, y - h / 2.0, x + w / 2.0, y + h / 2.0], dtype=np.float32)


def scale_boxes(boxes: np.ndarray, scale: float, pad: tuple[float, float], orig_shape: tuple[int, int]) -> np.ndarray:
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


def nms(boxes: np.ndarray, scores: np.ndarray, iou_threshold: float) -> list[int]:
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


def parse_output(output: np.ndarray, conf_threshold: float, num_classes: int, input_size: int) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
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
        boxes.append(xywh_to_xyxy(box))
        scores.append(score)
        class_ids.append(class_id)

    if not boxes:
        return np.empty((0, 4), dtype=np.float32), np.empty((0,), dtype=np.float32), np.empty((0,), dtype=np.int32)

    return np.stack(boxes).astype(np.float32), np.array(scores, dtype=np.float32), np.array(class_ids, dtype=np.int32)


def draw(frame: np.ndarray, boxes: np.ndarray, scores: np.ndarray, classes: np.ndarray, labels: list[str]) -> np.ndarray:
    out = frame.copy()
    for box, score, class_id in zip(boxes, scores, classes):
        x1, y1, x2, y2 = box.astype(int).tolist()
        name = labels[class_id] if 0 <= class_id < len(labels) else str(class_id)
        text = f"{name} {score:.2f}"
        cv2.rectangle(out, (x1, y1), (x2, y2), (0, 255, 0), 2)
        cv2.putText(out, text, (x1, max(18, y1 - 8)), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2, cv2.LINE_AA)
    return out


def run_frame(interpreter: Interpreter, frame: np.ndarray, labels: list[str], conf: float, iou: float) -> np.ndarray:
    input_details = interpreter.get_input_details()[0]
    output_details = interpreter.get_output_details()[0]
    size = int(input_details["shape"][1])
    inp, scale, pad = preprocess(frame, size, input_details["dtype"])
    interpreter.set_tensor(input_details["index"], inp)
    interpreter.invoke()
    output = interpreter.get_tensor(output_details["index"])
    boxes, scores, classes = parse_output(output, conf, len(labels), size)
    boxes = scale_boxes(boxes, scale, pad, frame.shape[:2])
    keep = nms(boxes, scores, iou)
    if keep:
        boxes = boxes[keep]
        scores = scores[keep]
        classes = classes[keep]
    else:
        boxes = np.empty((0, 4), dtype=np.float32)
        scores = np.empty((0,), dtype=np.float32)
        classes = np.empty((0,), dtype=np.int32)
    return draw(frame, boxes, scores, classes, labels)


def parse_source(source: str):
    if source.isdigit():
        return int(source)
    return source


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", required=True)
    parser.add_argument("--labels", default="labels.txt")
    parser.add_argument("--source", required=True, help="Image path, video path, or camera index like 0")
    parser.add_argument("--conf", type=float, default=None)
    parser.add_argument("--iou", type=float, default=None)
    parser.add_argument("--config", default="model_config.json")
    args = parser.parse_args()

    config_path = Path(args.config)
    config = {}
    if config_path.exists():
        config = json.loads(config_path.read_text(encoding="utf-8"))

    conf = float(args.conf if args.conf is not None else config.get("confidence_threshold", 0.25))
    iou = float(args.iou if args.iou is not None else config.get("iou_threshold", 0.45))

    interpreter = Interpreter(model_path=str(Path(args.model)))
    interpreter.allocate_tensors()
    labels = load_labels(Path(args.labels))
    source = parse_source(args.source)

    if isinstance(source, int):
        cap = cv2.VideoCapture(source)
        if not cap.isOpened():
            raise RuntimeError("Could not open camera source.")
        while True:
            ok, frame = cap.read()
            if not ok:
                break
            vis = run_frame(interpreter, frame, labels, conf, iou)
            cv2.imshow("Pi TFLite Detect", vis)
            key = cv2.waitKey(1) & 0xFF
            if key in (27, ord("q")):
                break
        cap.release()
        cv2.destroyAllWindows()
        return

    path = Path(source)
    suffix = path.suffix.lower()
    if suffix in {".jpg", ".jpeg", ".png", ".bmp", ".webp"}:
        frame = cv2.imread(str(path))
        if frame is None:
            raise RuntimeError(f"Could not read image: {path}")
        vis = run_frame(interpreter, frame, labels, conf, iou)
        out_path = path.with_name(path.stem + "_pred" + path.suffix)
        cv2.imwrite(str(out_path), vis)
        print(f"Saved: {out_path}")
        return

    cap = cv2.VideoCapture(str(path))
    if not cap.isOpened():
        raise RuntimeError(f"Could not open source: {path}")
    while True:
        ok, frame = cap.read()
        if not ok:
            break
        vis = run_frame(interpreter, frame, labels, conf, iou)
        cv2.imshow("Pi TFLite Detect", vis)
        key = cv2.waitKey(1) & 0xFF
        if key in (27, ord("q")):
            break
    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
