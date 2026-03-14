from __future__ import annotations

import argparse
import sys
from pathlib import Path


def _ensure_ultralytics():
    try:
        from ultralytics import YOLO
    except Exception as exc:
        print(f'[error] Failed to import ultralytics: {exc}', flush=True)
        raise
    return YOLO


def cmd_train(args: argparse.Namespace) -> int:
    YOLO = _ensure_ultralytics()
    model = YOLO(args.model)
    result = model.train(
        data=args.data,
        epochs=args.epochs,
        imgsz=args.imgsz,
        batch=args.batch,
        device=args.device or 'cpu',
        project=args.project or 'runs',
        name=args.name or 'customtrainer_train',
    )
    print(result, flush=True)
    return 0


def cmd_val(args: argparse.Namespace) -> int:
    YOLO = _ensure_ultralytics()
    model = YOLO(args.weights)
    result = model.val(
        data=args.data,
        imgsz=args.imgsz,
        device=args.device or 'cpu',
    )
    print(result, flush=True)
    return 0


def cmd_predict(args: argparse.Namespace) -> int:
    YOLO = _ensure_ultralytics()
    model = YOLO(args.weights)
    result = model.predict(
        source=args.source,
        imgsz=args.imgsz,
        conf=args.conf,
        device=args.device or 'cpu',
        save=True,
        verbose=True,
    )
    print(result, flush=True)
    return 0


def cmd_export(args: argparse.Namespace) -> int:
    YOLO = _ensure_ultralytics()
    model = YOLO(args.weights)
    kwargs = {
        'format': args.format,
        'imgsz': args.imgsz,
        'device': args.device or 'cpu',
        'nms': args.nms,
    }
    if args.int8:
        kwargs['int8'] = True
        if args.data:
            kwargs['data'] = args.data
    if args.half:
        kwargs['half'] = True
    result = model.export(**kwargs)
    print(result, flush=True)
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
    train.add_argument('--device', default='cpu')
    train.add_argument('--project', default='runs')
    train.add_argument('--name', default='customtrainer_train')
    train.set_defaults(func=cmd_train)

    val = sub.add_parser('val')
    val.add_argument('--weights', required=True)
    val.add_argument('--data', required=True)
    val.add_argument('--imgsz', type=int, default=640)
    val.add_argument('--device', default='cpu')
    val.set_defaults(func=cmd_val)

    predict = sub.add_parser('predict')
    predict.add_argument('--weights', required=True)
    predict.add_argument('--source', required=True)
    predict.add_argument('--imgsz', type=int, default=640)
    predict.add_argument('--conf', type=float, default=0.25)
    predict.add_argument('--device', default='cpu')
    predict.set_defaults(func=cmd_predict)

    export = sub.add_parser('export')
    export.add_argument('--weights', required=True)
    export.add_argument('--format', default='tflite')
    export.add_argument('--imgsz', type=int, default=320)
    export.add_argument('--device', default='cpu')
    export.add_argument('--data', default='')
    export.add_argument('--int8', action='store_true')
    export.add_argument('--half', action='store_true')
    export.add_argument('--nms', action='store_true')
    export.set_defaults(func=cmd_export)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return int(args.func(args))
    except Exception as exc:
        print(f'[error] {exc}', flush=True)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
