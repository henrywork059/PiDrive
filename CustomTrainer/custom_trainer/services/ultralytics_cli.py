from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from custom_trainer.services.session_service import resolve_prediction_source

from custom_trainer.services.device_service import resolve_device, runtime_summary


_IMAGE_SUFFIXES = {'.jpg', '.jpeg', '.png', '.bmp', '.webp'}


def _configure_stdio() -> None:
    for stream_name in ('stdout', 'stderr'):
        stream = getattr(sys, stream_name, None)
        reconfigure = getattr(stream, 'reconfigure', None)
        if callable(reconfigure):
            try:
                reconfigure(encoding='utf-8', errors='replace')
            except Exception:
                pass


def _ensure_ultralytics():
    try:
        from ultralytics import YOLO
    except Exception as exc:
        print(f'[error] Failed to import ultralytics: {exc}', flush=True)
        raise
    return YOLO


def _resolved_device(args_device: str | None) -> str:
    requested = args_device or 'auto'
    resolved = resolve_device(requested)
    print(f'[device] Requested={requested} | Resolved={resolved} | {runtime_summary()}', flush=True)
    return resolved


def _metric_value(metrics: dict[str, object], key: str) -> float | None:
    value = metrics.get(key)
    if value is None:
        return None
    try:
        return float(value)
    except Exception:
        return None


def _print_metrics(result: object) -> None:
    metrics = getattr(result, 'results_dict', None)
    if not isinstance(metrics, dict):
        return
    precision = _metric_value(metrics, 'metrics/precision(B)')
    recall = _metric_value(metrics, 'metrics/recall(B)')
    map50 = _metric_value(metrics, 'metrics/mAP50(B)')
    map5095 = _metric_value(metrics, 'metrics/mAP50-95(B)')
    fitness = _metric_value(metrics, 'fitness')
    pieces: list[str] = []
    if precision is not None:
        pieces.append(f'precision={precision:.3f}')
    if recall is not None:
        pieces.append(f'recall={recall:.3f}')
    if map50 is not None:
        pieces.append(f'mAP50={map50:.3f}')
    if map5095 is not None:
        pieces.append(f'mAP50-95={map5095:.3f}')
    if fitness is not None:
        pieces.append(f'fitness={fitness:.3f}')
    if pieces:
        print('[metrics] ' + ' | '.join(pieces), flush=True)


def _bool_arg(value: object) -> bool:
    if isinstance(value, bool):
        return value
    text = str(value).strip().lower()
    return text not in {'0', 'false', 'no', 'off', ''}


def _ensure_output_path(output_dir: Path, source_name: str, index: int) -> Path:
    source_path = Path(source_name)
    stem = source_path.stem or f'frame_{index:05d}'
    suffix = source_path.suffix or '.jpg'
    target = output_dir / f'{stem}{suffix}'
    if not target.exists():
        return target
    return output_dir / f'{stem}_{index:05d}{suffix}'


def cmd_train(args: argparse.Namespace) -> int:
    YOLO = _ensure_ultralytics()
    model = YOLO(args.model)
    result = model.train(
        data=args.data,
        epochs=args.epochs,
        imgsz=args.imgsz,
        batch=args.batch,
        device=_resolved_device(args.device),
        project=args.project or 'runs',
        name=args.name or 'customtrainer_train',
    )
    save_dir = getattr(result, 'save_dir', None)
    if save_dir:
        print(f'[save-dir] {save_dir}', flush=True)
    return 0


def cmd_val(args: argparse.Namespace) -> int:
    YOLO = _ensure_ultralytics()
    model = YOLO(args.weights)
    result = model.val(
        data=args.data,
        imgsz=args.imgsz,
        device=_resolved_device(args.device),
        project=args.project or None,
        name=args.name or None,
    )
    save_dir = getattr(result, 'save_dir', None)
    if save_dir:
        print(f'[save-dir] {save_dir}', flush=True)
    _print_metrics(result)
    return 0


def cmd_predict(args: argparse.Namespace) -> int:
    YOLO = _ensure_ultralytics()
    model = YOLO(args.weights)
    output_dir = Path(args.project or 'runs/detect') / (args.name or 'predict')
    output_dir.mkdir(parents=True, exist_ok=True)
    print(f'[save-dir] {output_dir}', flush=True)
    requested_source_path = Path(args.source)
    source_path, source_note = resolve_prediction_source(requested_source_path)
    if source_note:
        print(f'[source] {source_note}', flush=True)
    if source_path != requested_source_path:
        print(f'[source] requested={requested_source_path} | resolved={source_path}', flush=True)
    results = model.predict(
        source=str(source_path),
        imgsz=args.imgsz,
        conf=args.conf,
        device=_resolved_device(args.device),
        save=False,
        verbose=True,
        stream=True,
    )
    show_labels = _bool_arg(args.show_labels)
    show_conf = _bool_arg(args.show_conf)
    show_boxes = _bool_arg(args.show_boxes)
    for index, result in enumerate(results, start=1):
        result_path = Path(getattr(result, 'path', source_path))
        boxes = getattr(result, 'boxes', None)
        box_count = int(len(boxes)) if boxes is not None else 0
        image_name = result_path.name
        print(f'[predict] {image_name} -> {box_count} box(es)', flush=True)
        print('[predict-json] ' + json.dumps({
            'type': 'image',
            'image_name': image_name,
            'image_path': str(result_path),
            'box_count': box_count,
        }, ensure_ascii=False), flush=True)
        if boxes is not None:
            names = getattr(result, 'names', {}) or {}
            for box_index, box in enumerate(boxes, start=1):
                try:
                    xyxy = [int(round(float(v))) for v in box.xyxy[0].tolist()]
                except Exception:
                    xyxy = []
                try:
                    conf = float(box.conf[0])
                except Exception:
                    conf = 0.0
                try:
                    cls_id = int(box.cls[0])
                except Exception:
                    cls_id = -1
                label = names.get(cls_id, str(cls_id))
                print(f'[predict-box] #{box_index} {label} conf={conf:.3f} xyxy={xyxy}', flush=True)
                print('[predict-json] ' + json.dumps({
                    'type': 'box',
                    'image_name': image_name,
                    'image_path': str(result_path),
                    'box_index': box_index,
                    'class_id': cls_id,
                    'label': str(label),
                    'conf': conf,
                    'xyxy': xyxy,
                }, ensure_ascii=False), flush=True)
        if result_path.suffix.lower() in _IMAGE_SUFFIXES or source_path.is_dir():
            save_path = _ensure_output_path(output_dir, result_path.name, index)
            result.plot(
                conf=show_conf,
                line_width=args.line_width,
                font_size=args.font_size,
                labels=show_labels,
                boxes=show_boxes,
                save=True,
                filename=str(save_path),
            )
            print(f'[preview-image] {save_path}', flush=True)
    return 0


def cmd_export(args: argparse.Namespace) -> int:
    YOLO = _ensure_ultralytics()
    model = YOLO(args.weights)
    kwargs = {
        'format': args.format,
        'imgsz': args.imgsz,
        'device': _resolved_device(args.device),
        'nms': args.nms,
    }
    if args.int8:
        kwargs['int8'] = True
        if args.data:
            kwargs['data'] = args.data
    if args.half:
        kwargs['half'] = True
    result = model.export(**kwargs)
    print(f'[export] {result}', flush=True)
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog='custom_trainer_ultralytics')
    sub = parser.add_subparsers(dest='action', required=True)

    train = sub.add_parser('train')
    train.add_argument('--model', required=True)
    train.add_argument('--data', required=True)
    train.add_argument('--epochs', type=int, default=100)
    train.add_argument('--imgsz', type=int, default=640)
    train.add_argument('--batch', type=int, default=16)
    train.add_argument('--device', default='auto')
    train.add_argument('--project', default='runs')
    train.add_argument('--name', default='customtrainer_train')
    train.set_defaults(func=cmd_train)

    val = sub.add_parser('val')
    val.add_argument('--weights', required=True)
    val.add_argument('--data', required=True)
    val.add_argument('--imgsz', type=int, default=640)
    val.add_argument('--device', default='auto')
    val.add_argument('--project', default='')
    val.add_argument('--name', default='')
    val.set_defaults(func=cmd_val)

    predict = sub.add_parser('predict')
    predict.add_argument('--weights', required=True)
    predict.add_argument('--source', required=True)
    predict.add_argument('--imgsz', type=int, default=640)
    predict.add_argument('--conf', type=float, default=0.25)
    predict.add_argument('--device', default='auto')
    predict.add_argument('--project', default='')
    predict.add_argument('--name', default='')
    predict.add_argument('--line-width', type=int, default=None)
    predict.add_argument('--font-size', type=int, default=None)
    predict.add_argument('--show-labels', default='1')
    predict.add_argument('--show-conf', default='1')
    predict.add_argument('--show-boxes', default='1')
    predict.set_defaults(func=cmd_predict)

    export = sub.add_parser('export')
    export.add_argument('--weights', required=True)
    export.add_argument('--format', default='tflite')
    export.add_argument('--imgsz', type=int, default=320)
    export.add_argument('--device', default='auto')
    export.add_argument('--data', default='')
    export.add_argument('--int8', action='store_true')
    export.add_argument('--half', action='store_true')
    export.add_argument('--nms', action='store_true')
    export.set_defaults(func=cmd_export)
    return parser


def main(argv: list[str] | None = None) -> int:
    _configure_stdio()
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return int(args.func(args))
    except Exception as exc:
        print(f'[error] {exc}', flush=True)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
