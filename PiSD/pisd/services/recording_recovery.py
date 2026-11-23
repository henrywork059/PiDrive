"""Inspect and explicitly recover interrupted PiSD recording metadata.

No automatic changes are made while opening a recording or listing files. A
repair must be requested offline, and every changed original is copied to a
unique audit directory first. Orphan JPEGs and unknown metadata are retained.
"""
from __future__ import annotations

import hashlib
import json
import math
import os
import re
import shutil
import stat
import tempfile
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _stamp() -> str:
    return datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')


def _atomic_bytes(path: Path, new_bytes: bytes, expected_bytes: bytes | None) -> None:
    """Publish a whole metadata file or fail without truncating it."""
    current = path.read_bytes() if path.exists() else None
    if current != expected_bytes:
        raise RuntimeError(f'{path.name} changed during recovery; stop all recorders and rescan.')
    staged: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(mode='wb', prefix=f'.{path.name}.',
                                         suffix='.recovery-tmp', dir=path.parent, delete=False) as handle:
            staged = Path(handle.name)
            handle.write(new_bytes)
            handle.flush()
            os.fsync(handle.fileno())
        if path.exists():
            os.chmod(staged, stat.S_IMODE(path.stat().st_mode))
        if (path.read_bytes() if path.exists() else None) != expected_bytes:
            raise RuntimeError(f'{path.name} changed during recovery; original preserved.')
        os.replace(staged, path)
        staged = None
    finally:
        if staged is not None:
            staged.unlink(missing_ok=True)


def _read_jsonl(path: Path) -> tuple[dict[str, dict[str, Any]], list[str], bytes | None]:
    raw = path.read_bytes() if path.exists() else None
    entries: dict[str, dict[str, Any]] = {}
    issues: list[str] = []
    if raw is None:
        return entries, issues, None
    for n, line in enumerate(raw.decode('utf-8', errors='replace').splitlines(), 1):
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            issues.append(f'{path.name}:{n}: incomplete or invalid JSON')
            continue
        if not isinstance(row, dict):
            issues.append(f'{path.name}:{n}: JSON entry is not an object')
            continue
        entries[str(n)] = row
    return entries, issues, raw


def _frame_in_session(session: Path, row: dict[str, Any], kind: str) -> tuple[str, Path] | None:
    frames = (session / 'frames').resolve()
    choices = []
    if kind == 'records':
        training = row.get('training_label') or {}
        if isinstance(training, dict):
            choices.append(training.get('frame'))
        choices.extend([row.get('file'), row.get('relative_file')])
    else:
        choices.extend([row.get('frame'), row.get('relative_file')])
    for raw in choices:
        if not isinstance(raw, str) or not raw.strip():
            continue
        cleaned = raw.replace('\\', '/')
        candidate = Path(cleaned)
        if not candidate.is_absolute():
            if cleaned.startswith('frames/'):
                candidate = session / candidate
            elif len(candidate.parts) >= 2 and candidate.parts[-2] == 'frames' and '..' not in candidate.parts:
                # Project-relative legacy files retain their leaf filename.
                candidate = frames / candidate.name
            else:
                continue
        try:
            resolved = candidate.resolve()
            rel = resolved.relative_to(frames)
        except (OSError, ValueError):
            continue
        if len(rel.parts) == 1 and resolved.suffix.lower() in {'.jpg', '.jpeg'}:
            return f'frames/{rel.as_posix()}', resolved
    return None


def _safe_command(row: dict[str, Any]) -> tuple[float, float] | None:
    try:
        steer = float(row['steering'])
        throttle = float(row['throttle'])
        if all(math.isfinite(v) and -1 <= v <= 1 for v in (steer, throttle)):
            return steer, throttle
    except (KeyError, TypeError, ValueError, OverflowError):
        pass
    return None


def _scan(session: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    session = session.resolve()
    if not (session / 'frames').is_dir():
        raise ValueError(f'Not a PiSD recording session: {session} (frames directory missing)')
    records_path, labels_path, manifest_path = (session / name for name in
                                               ('records.jsonl', 'labels.jsonl', 'manifest.json'))
    record_lines, record_issues, record_raw = _read_jsonl(records_path)
    label_lines, label_issues, label_raw = _read_jsonl(labels_path)
    issues = record_issues + label_issues
    mapped: dict[str, dict[str, dict[str, Any]]] = {'records': {}, 'labels': {}}
    for name, rows in (('records', record_lines), ('labels', label_lines)):
        for line, row in rows.items():
            found = _frame_in_session(session, row, name)
            if found is None:
                issues.append(f'{name}.jsonl:{line}: missing or unsafe frame path')
                continue
            key, path = found
            if key in mapped[name]:
                issues.append(f'{name}.jsonl:{line}: duplicate frame {key}')
                continue
            mapped[name][key] = row
            if not path.is_file():
                issues.append(f'{name}.jsonl:{line}: JPEG missing: {key}')
    records, labels = mapped['records'], mapped['labels']
    disk_frames = {
        f'frames/{path.relative_to((session / "frames").resolve()).as_posix()}'
        for path in (session / 'frames').iterdir()
        if path.is_file() and path.suffix.lower() in {'.jpg', '.jpeg'}
    }
    missing_labels = sorted(records.keys() - labels.keys())
    missing_records = sorted(labels.keys() - records.keys())
    orphans = sorted(disk_frames - (records.keys() | labels.keys()))
    existing_manifest: dict[str, Any] | None = None
    raw_manifest = manifest_path.read_bytes() if manifest_path.exists() else None
    if raw_manifest is not None:
        try:
            obj = json.loads(raw_manifest)
            if not isinstance(obj, dict):
                raise ValueError('not a JSON object')
            existing_manifest = obj
        except (ValueError, UnicodeError):
            issues.append('manifest.json: malformed JSON; recovery will not overwrite it')
    else:
        issues.append('manifest.json: missing; recovery will not fabricate original session settings')
    complete = len(records.keys() & labels.keys())
    manifest_count = existing_manifest.get('frame_count') if existing_manifest else None
    summary = {
        'session': str(session),
        'record_entries': len(records),
        'label_entries': len(labels),
        'complete_pairs': complete,
        'jpeg_files': len(disk_frames),
        'missing_labels': missing_labels,
        'missing_records': missing_records,
        'orphan_jpegs': orphans,
        'issues': issues,
        'manifest_frame_count': manifest_count,
        'manifest_running': bool(existing_manifest.get('running', False)) if existing_manifest else None,
        'manifest_count_mismatch': bool(isinstance(manifest_count, int) and manifest_count != complete),
        'needs_attention': bool(missing_labels or missing_records or orphans or issues or
                                (isinstance(manifest_count, int) and manifest_count != complete)),
    }
    data = {'records': records, 'labels': labels, 'record_raw': record_raw,
            'label_raw': label_raw, 'manifest': existing_manifest, 'manifest_raw': raw_manifest}
    return summary, data


def inspect_session(session_dir: Path | str) -> dict[str, Any]:
    """Report incomplete frames, malformed JSONL, duplicate IDs and stale counts."""
    summary, _ = _scan(Path(session_dir))
    return summary


def _label_from_record(session: Path, key: str, record: dict[str, Any]) -> dict[str, Any] | None:
    command = _safe_command(record)
    if command is None:
        return None
    training = record.get('training_label')
    label = dict(training) if isinstance(training, dict) else {}
    label.update({
        'frame': key,
        'steering': command[0],
        'throttle': command[1],
        'timestamp_utc': label.get('timestamp_utc') or record.get('saved_at_utc', ''),
        'session_id': label.get('session_id') or record.get('session_id', session.name),
        'control_label_source': label.get('control_label_source') or record.get('control_label_source', 'manual_command'),
    })
    for field in ('relative_file', 'source_frame_seq', 'overlay_settings',
                  'overlay_settings_file', 'overlay_settings_history_file', 'overlay_schema_version'):
        if field not in label and field in record:
            label[field] = record[field]
    return label


def _record_from_label(session: Path, key: str, label: dict[str, Any]) -> dict[str, Any] | None:
    command = _safe_command(label)
    if command is None:
        return None
    frame = session / key
    match = re.match(r'frame_(\d+)_', frame.name)
    frame_index = int(match.group(1)) if match else 0
    stable = hashlib.sha256((session.name + '/' + key).encode()).hexdigest()[:20]
    return {
        'frame_id': f'recovered_{stable}',
        'frame_index': frame_index,
        'session_id': label.get('session_id') or session.name,
        'saved_at_utc': label.get('timestamp_utc') or '',
        'file': str(frame),
        'relative_file': label.get('relative_file') or '',
        'steering': command[0],
        'throttle': command[1],
        'control_label_source': label.get('control_label_source', 'manual_command'),
        'source_frame_seq': label.get('source_frame_seq', 0),
        'training_label': dict(label),
        'recovery': {
            'source': 'labels.jsonl',
            'limited_metadata': True,
            'message': 'Original camera, motor and timestamp metadata cannot be reconstructed',
        },
    }


def _append_jsonl(original: bytes | None, rows: list[dict[str, Any]]) -> bytes:
    content = original or b''
    if content and not content.endswith(b'\n'):
        content += b'\n'
    return content + b''.join((json.dumps(row, ensure_ascii=False, sort_keys=True, allow_nan=False) + '\n').encode('utf-8') for row in rows)


def recover_session(session_dir: Path | str, *, confirm_offline: bool = False) -> dict[str, Any]:
    """Reconcile safe metadata and update counts only after preserving originals.

    The operator must explicitly confirm that no recorder is writing the
    session. This cannot coordinate with unpatched external writers.
    """
    if not confirm_offline:
        raise RuntimeError('Stop recording first and pass confirm_offline=True to repair the session.')
    session = Path(session_dir).resolve()
    before, data = _scan(session)
    record_additions: list[dict[str, Any]] = []
    label_additions: list[dict[str, Any]] = []
    skipped: list[str] = []
    for key in before['missing_labels']:
        if not (session / key).is_file():
            skipped.append(f'{key}: JPEG is missing')
            continue
        label = _label_from_record(session, key, data['records'][key])
        if label is None:
            skipped.append(f'{key}: record does not contain finite training controls')
        else:
            label_additions.append(label)
    for key in before['missing_records']:
        if not (session / key).is_file():
            skipped.append(f'{key}: JPEG is missing')
            continue
        record = _record_from_label(session, key, data['labels'][key])
        if record is None:
            skipped.append(f'{key}: label does not contain finite training controls')
        else:
            record_additions.append(record)
    before_count = data['manifest'].get('frame_count') if data['manifest'] else None
    manifest_new_count = (before['complete_pairs'] + len(record_additions) + len(label_additions))
    count_changed = isinstance(before_count, int) and before_count != manifest_new_count
    stale_running = bool(data['manifest'] and data['manifest'].get('running'))
    if not (record_additions or label_additions or count_changed or stale_running):
        return {**before, 'repaired': False, 'added_records': 0, 'added_labels': 0,
                'skipped_recovery': skipped, 'backup_dir': ''}
    if data['manifest'] is None:
        # We will not invent manifest schema or silently overwrite bad JSON.
        return {**before, 'repaired': False, 'added_records': 0, 'added_labels': 0,
                'skipped_recovery': skipped + ['manifest unavailable or malformed; manual recovery required'],
                'backup_dir': ''}
    backup_dir = session / '.recovery_backups' / f'{_stamp()}_{uuid.uuid4().hex[:8]}'
    backup_dir.mkdir(parents=True, exist_ok=False)
    for filename in ('records.jsonl', 'labels.jsonl', 'manifest.json'):
        path = session / filename
        if path.exists():
            with path.open('rb') as source, (backup_dir / filename).open('xb') as dest:
                shutil.copyfileobj(source, dest)
                dest.flush()
                os.fsync(dest.fileno())
    if record_additions:
        _atomic_bytes(session / 'records.jsonl', _append_jsonl(data['record_raw'], record_additions), data['record_raw'])
    if label_additions:
        _atomic_bytes(session / 'labels.jsonl', _append_jsonl(data['label_raw'], label_additions), data['label_raw'])
    after, _ = _scan(session)
    manifest = dict(data['manifest'])
    manifest['frame_count'] = after['complete_pairs']
    # The operator has confirmed this historical session is offline. Clearing
    # stale running=True is truthful; do not fabricate an ended_at_utc timestamp.
    manifest['running'] = False
    manifest['recording_recovery'] = {
        'recovered_at_utc': datetime.now(timezone.utc).isoformat(),
        'source_frame_count': before_count,
        'was_marked_running': stale_running,
        'complete_pairs': after['complete_pairs'],
        'unmatched_record_entries': len(after['missing_labels']),
        'unmatched_label_entries': len(after['missing_records']),
        'orphan_jpeg_count': len(after['orphan_jpegs']),
        'invalid_or_duplicate_rows': len(after['issues']),
        'limited_metadata_records_added': len(record_additions),
        'labels_added': len(label_additions),
        'recovery_backup': str(backup_dir.relative_to(session)),
    }
    encoded = (json.dumps(manifest, indent=2, sort_keys=True, ensure_ascii=False) + '\n').encode('utf-8')
    _atomic_bytes(session / 'manifest.json', encoded, data['manifest_raw'])
    after = inspect_session(session)
    audit = {'before': before, 'after': after,
             'added_records': len(record_additions), 'added_labels': len(label_additions),
             'skipped_recovery': skipped}
    (backup_dir / 'audit.json').write_text(json.dumps(audit, indent=2, sort_keys=True) + '\n', encoding='utf-8')
    return {**after, 'repaired': True, 'added_records': len(record_additions),
            'added_labels': len(label_additions), 'skipped_recovery': skipped,
            'backup_dir': str(backup_dir)}
