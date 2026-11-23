#!/usr/bin/env python3
"""Read-only PiSD steering replay. No camera, Flask, GPIO or motor service is imported.

Fixture mode uses explicitly supplied synthetic predictions (NOT model inference).
Model mode calls only the AI model loader and inference on recorded JPEG bytes.
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import json
import math
import sys
from pathlib import Path
from typing import Any, Callable

MAX_RECORDS = 5000
MAX_FRAME_BYTES = 12 * 1024 * 1024


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def finite_steering(value: Any, name: str) -> float:
    if isinstance(value, bool):
        raise ValueError(f'{name} cannot be a boolean')
    x = float(value)
    if not math.isfinite(x) or not -1.0 <= x <= 1.0:
        raise ValueError(f'{name} must be finite and between -1 and 1')
    return x


def confidence_or_none(value: Any) -> float | None:
    if value is None:
        return None  # steering regressors do not output calibrated confidence
    if isinstance(value, bool):
        raise ValueError('confidence must be numeric')
    x = float(value)
    if not math.isfinite(x) or not 0.0 <= x <= 1.0:
        raise ValueError('confidence must be a finite [0,1] value')
    return x


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        raise ValueError(f'Input JSONL missing: {path}')
    rows = []
    with path.open('r', encoding='utf-8') as f:
        for line_no, line in enumerate(f, 1):
            if not line.strip():
                continue
            if len(line) > 18 * 1024 * 1024:
                raise ValueError(f'Line {line_no} exceeds the bounded replay input limit')
            if len(rows) >= MAX_RECORDS:
                raise ValueError(f'Exceeded {MAX_RECORDS} rows')
            item = json.loads(line)
            if not isinstance(item, dict):
                raise ValueError(f'Line {line_no} is not an object')
            rows.append(item)
    if not rows:
        raise ValueError('No replay rows found')
    return rows


def safe_frame(row: dict[str, Any], session_dir: Path | None) -> bytes:
    # Embedded JPEG is only for disposable synthetic fixtures; no paths are created.
    embedded = row.get('image_b64')
    if embedded is not None:
        if session_dir is not None:
            raise ValueError('Base64 frames are for synthetic fixtures only')
        raw = base64.b64decode(str(embedded), validate=True)
    else:
        if session_dir is None:
            raise ValueError('Synthetic fixture must supply image_b64')
        relative = str(row.get('frame') or '').replace('\\', '/')
        if not relative or Path(relative).is_absolute():
            raise ValueError('Invalid frame path')
        base = session_dir.resolve()
        path = (base / relative).resolve()
        if not path.is_relative_to(base):
            raise ValueError('Frame path escapes session directory')
        if not path.is_file():
            raise FileNotFoundError(f'Frame missing: {relative}')
        if path.stat().st_size > MAX_FRAME_BYTES:
            raise ValueError('Frame exceeds size limit')
        raw = path.read_bytes()
    if not raw or len(raw) > MAX_FRAME_BYTES:
        raise ValueError('Frame empty or oversized')
    return raw


def model_predictor(path: Path) -> Callable[[bytes, dict[str, Any]], tuple[float, float | None]]:
    """Load existing steering model without ever constructing CameraService/MotorService.

    Uses U27 preflight/manifest contract; never calls predict_once or start().
    """
    root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(root))
    from pisd.services.ai_drive_service import AIDriveService

    model_path = path.resolve(strict=True)
    service = AIDriveService(model_path.parent.parent, models_dir_name=model_path.parent.name)
    loaded = service.load_model(model_path.name)
    if not loaded.get('ok'):
        raise ValueError(f'Model preflight failed: {loaded.get("message", "unknown") }')

    def predict(image: bytes, _row: dict[str, Any]) -> tuple[float, None]:
        steering, _throttle = service._predict_from_jpeg(image)
        return float(steering), None  # no calibrated steering confidence output

    return predict


def synthetic_predictor(_image: bytes, row: dict[str, Any]) -> tuple[float, float | None]:
    if 'predicted_steering' not in row:
        raise ValueError('No synthetic predicted_steering; provide --model for real inference')
    return finite_steering(row['predicted_steering'], 'predicted_steering'), confidence_or_none(row.get('confidence'))


def replay(input_file: Path, *, model_file: Path | None = None,
           session_dir: Path | None = None, tick_s: float = 0.1,
           predictor: Callable[[bytes, dict[str, Any]], tuple[float, float | None]] | None = None) -> dict[str, Any]:
    if not math.isfinite(tick_s) or tick_s <= 0:
        raise ValueError('tick_s must be finite and positive')
    if model_file is not None and predictor is not None:
        raise ValueError('Select either --model or an injected predictor')
    rows = read_jsonl(input_file)
    source_hash = digest(input_file)
    model_hash = digest(model_file) if model_file else None
    predict = predictor or (model_predictor(model_file) if model_file else synthetic_predictor)
    predictions, failures, absolute_errors = [], [], []
    seen = set()
    for i, row in enumerate(rows):
        frame = str(row.get('frame') or f'fixture_{i:06d}.jpg')
        item: dict[str, Any] = {'index': i, 'virtual_time_s': round(i * tick_s, 6), 'frame': frame}
        try:
            if frame in seen:
                raise ValueError('Duplicate frame identity')
            seen.add(frame)
            expected = finite_steering(row['steering'], 'label steering')
            image = safe_frame(row, session_dir)
            raw_pred, confidence = predict(image, row)
            predicted = finite_steering(raw_pred, 'predicted steering')
            conf = confidence_or_none(confidence)
            error = abs(predicted - expected)
            absolute_errors.append(error)
            item.update({'label_steering': expected, 'predicted_steering': predicted,
                         'prediction_confidence': conf, 'absolute_error': round(error, 8),
                         'event': 'ok'})
        except (ValueError, TypeError, KeyError, OSError, RuntimeError) as exc:
            item.update({'event': 'prediction_failure', 'error': str(exc)})
            failures.append({'index': i, 'virtual_time_s': item['virtual_time_s'],
                             'frame': frame, 'event': 'prediction_failure', 'detail': str(exc)})
        predictions.append(item)
    return {
        'schema_version': 1,
        'component': 'PiSD', 'mode': 'model_inference' if model_file else 'synthetic_predictions',
        'read_only': True, 'hardware_initialized': False,
        'input': {'source': str(input_file), 'source_sha256': source_hash,
                  'model': str(model_file) if model_file else None, 'model_sha256': model_hash},
        'total_frames': len(rows), 'successful_predictions': len(absolute_errors),
        'failed_frames': len(failures), 'steering_mae': round(sum(absolute_errors) / len(absolute_errors), 8) if absolute_errors else None,
        'frames': predictions, 'failure_events': failures,
    }


def write_report(report: dict[str, Any], report_path: Path, source: Path, session_dir: Path | None) -> None:
    output = report_path.resolve()
    if output == source.resolve() or (session_dir is not None and output.is_relative_to(session_dir.resolve())):
        raise ValueError('Output must not overwrite or modify the source session')
    # Exclusive create: no accidental overwrite, and no runtime config changes.
    with output.open('x', encoding='utf-8') as f:
        json.dump(report, f, sort_keys=True, indent=2, allow_nan=False)
        f.write('\n')


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--fixture', type=Path, help='Synthetic JSONL with base64 frames and labelled mock predictions')
    group.add_argument('--session', type=Path, help='Read-only PiSD recording session directory with labels.jsonl')
    parser.add_argument('--model', type=Path, help='Optional real .tflite/.keras model; never starts camera/motor')
    parser.add_argument('--tick-s', type=float, default=0.1, help='Deterministic virtual replay step')
    parser.add_argument('--report', type=Path, help='Optional new JSON report path outside the session')
    parser.add_argument('--max-steering-mae', type=float, default=None, help='Optional CI regression threshold')
    args = parser.parse_args(argv)
    try:
        source = args.fixture or args.session / 'labels.jsonl'
        if args.session is not None and args.model is None:
            raise ValueError('Real PiSD sessions require --model; fixture predictions are not real inference')
        result = replay(source, model_file=args.model, session_dir=args.session, tick_s=args.tick_s)
        if args.max_steering_mae is not None and (
            not math.isfinite(args.max_steering_mae) or args.max_steering_mae < 0):
            raise ValueError('Invalid MAE threshold')
        if args.report is not None:
            write_report(result, args.report, source, args.session)
        print(json.dumps(result, indent=2, sort_keys=True, allow_nan=False))
        if args.max_steering_mae is not None:
            if result['steering_mae'] is None or result['steering_mae'] > args.max_steering_mae:
                return 2
        return 2 if result['failed_frames'] else 0
    except (OSError, ValueError, RuntimeError, json.JSONDecodeError) as exc:
        print(f'Replay refused: {exc}', file=sys.stderr)
        return 2


if __name__ == '__main__':
    sys.exit(main())
