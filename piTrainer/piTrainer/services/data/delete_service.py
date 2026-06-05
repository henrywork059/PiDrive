from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterable

from .record_loader_service import IMAGE_KEYS, _resolve_image_path
from .session_service import resolve_session_dir
from .visibility_service import hidden_timestamp, is_record_hidden, mark_record_hidden, unmark_record_hidden, utc_timestamp

TS_KEYS = ['ts', 'timestamp', 'timestamp_utc', 'saved_at_utc']
ID_KEYS = ['frame_id', 'id', 'source_frame_seq']


def _training_label(record: dict[str, Any]) -> dict[str, Any]:
    training_label = record.get('training_label')
    return training_label if isinstance(training_label, dict) else {}


def _candidate_values(record: dict[str, Any], keys: list[str]) -> list[Any]:
    values: list[Any] = []
    nested = _training_label(record)
    for source in (record, nested):
        for key in keys:
            if key in source and source[key] is not None:
                values.append(source[key])
    return values


def _record_image_names(record: dict[str, Any]) -> set[str]:
    return {Path(str(value or '')).name for value in _candidate_values(record, IMAGE_KEYS) if str(value or '').strip()}


def _record_timestamps(record: dict[str, Any]) -> set[str]:
    return {str(value or '') for value in _candidate_values(record, TS_KEYS) if str(value or '').strip()}


def _record_ids(record: dict[str, Any]) -> set[str]:
    return {str(value or '') for value in _candidate_values(record, ID_KEYS) if str(value or '').strip()}


def _line_matches(record: dict, frame_id: str, image_name: str, ts: str) -> bool:
    ids = _record_ids(record)
    image_names = _record_image_names(record)
    timestamps = _record_timestamps(record)
    id_match = bool(frame_id) and str(frame_id) in ids
    image_match = bool(image_name) and str(image_name) in image_names
    ts_match = bool(ts) and str(ts) in timestamps
    if id_match and (image_match or ts_match):
        return True
    if image_match and ts_match:
        return True
    return False


def _with_newline(raw_line: str) -> str:
    return raw_line if raw_line.endswith('\n') else raw_line + '\n'


def _target_from_record(record: dict[str, Any]) -> dict[str, str]:
    return {
        'session': str(record.get('session', '') or ''),
        'frame_id': str(record.get('frame_id', '') or ''),
        'image_name': Path(str(record.get('abs_image', '') or record.get('image_path', '') or '')).name,
        'ts': str(record.get('ts', '') or ''),
    }


def _target_key(target: dict[str, str]) -> tuple[str, str, str, str]:
    return (
        str(target.get('session', '')),
        str(target.get('frame_id', '')),
        str(target.get('image_name', '')),
        str(target.get('ts', '')),
    )


def _target_label(target: dict[str, str]) -> str:
    frame_id = str(target.get('frame_id', '')).strip()
    image_name = str(target.get('image_name', '')).strip()
    ts = str(target.get('ts', '')).strip()
    if frame_id:
        return frame_id
    if image_name:
        return image_name
    return ts or 'unknown frame'


def _matching_target(record: dict[str, Any], targets: list[dict[str, str]]) -> dict[str, str] | None:
    for target in targets:
        if _line_matches(
            record,
            frame_id=str(target.get('frame_id', '')),
            image_name=str(target.get('image_name', '')),
            ts=str(target.get('ts', '')),
        ):
            return target
    return None


def _hide_in_jsonl(path: Path, targets: list[dict[str, str]], *, hidden_at_utc: str) -> tuple[int, set[tuple[str, str, str, str]]]:
    if not path.exists() or not targets:
        return 0, set()

    changed_rows = 0
    matched_targets: set[tuple[str, str, str, str]] = set()
    output_lines: list[str] = []
    with path.open('r', encoding='utf-8') as handle:
        for raw_line in handle:
            line = raw_line.strip()
            if not line:
                output_lines.append(_with_newline(raw_line))
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                output_lines.append(_with_newline(raw_line))
                continue

            if isinstance(record, dict):
                target = _matching_target(record, targets)
                if target is not None:
                    matched_targets.add(_target_key(target))
                    if not is_record_hidden(record):
                        mark_record_hidden(record, hidden_at_utc=hidden_at_utc)
                        changed_rows += 1
                        output_lines.append(json.dumps(record, ensure_ascii=False, sort_keys=True) + '\n')
                        continue

            output_lines.append(_with_newline(raw_line))

    if changed_rows:
        with path.open('w', encoding='utf-8') as handle:
            handle.writelines(output_lines)
    return changed_rows, matched_targets



def _first_sorted_text(values: Iterable[Any]) -> str:
    texts = sorted({str(value or '').strip() for value in values if str(value or '').strip()})
    return texts[0] if texts else ''


def _target_from_jsonl_record(session_name: str, record: dict[str, Any]) -> dict[str, str]:
    return {
        'session': str(session_name or ''),
        'frame_id': _first_sorted_text(_record_ids(record)),
        'image_name': _first_sorted_text(_record_image_names(record)),
        'ts': _first_sorted_text(_record_timestamps(record)),
    }


def _selected_session_names(sessions: Iterable[str]) -> list[str]:
    names: list[str] = []
    seen: set[str] = set()
    for session in sessions:
        name = str(session or '').strip()
        if name and name not in seen:
            names.append(name)
            seen.add(name)
    return names


def _jsonl_records(path: Path):
    if not path.exists():
        return
    with path.open('r', encoding='utf-8') as handle:
        for line_no, raw_line in enumerate(handle, start=1):
            line = raw_line.strip()
            if not line:
                yield line_no, raw_line, None
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                yield line_no, raw_line, None
                continue
            yield line_no, raw_line, record if isinstance(record, dict) else None


def _hidden_refs(records_root: Path, sessions: Iterable[str]) -> list[dict[str, Any]]:
    refs: list[dict[str, Any]] = []
    order = 0
    for session_name in _selected_session_names(sessions):
        session_dir = resolve_session_dir(records_root, session_name)
        for filename in ('labels.jsonl', 'records.jsonl'):
            path = session_dir / filename
            for line_no, _raw_line, record in _jsonl_records(path) or []:
                if not record or not is_record_hidden(record):
                    continue
                target = _target_from_jsonl_record(session_name, record)
                refs.append({
                    'session': session_name,
                    'session_dir': session_dir,
                    'path': path,
                    'filename': filename,
                    'line_no': line_no,
                    'key': _target_key(target),
                    'target': target,
                    'hidden_at_utc': hidden_timestamp(record),
                    'order': order,
                })
                order += 1
    return refs


def _recover_target_keys(refs: list[dict[str, Any]], *, recover_all: bool, count: int) -> set[tuple[str, str, str, str]]:
    if recover_all:
        return {tuple(ref['key']) for ref in refs}
    unique: dict[tuple[str, str, str, str], dict[str, Any]] = {}
    for ref in refs:
        key = tuple(ref['key'])
        previous = unique.get(key)
        if previous is None:
            unique[key] = ref
            continue
        previous_sort = (str(previous.get('hidden_at_utc', '')), int(previous.get('order', 0)))
        current_sort = (str(ref.get('hidden_at_utc', '')), int(ref.get('order', 0)))
        if current_sort > previous_sort:
            unique[key] = ref
    ordered = sorted(
        unique.values(),
        key=lambda ref: (str(ref.get('hidden_at_utc', '')), int(ref.get('order', 0))),
        reverse=True,
    )
    limit = max(1, int(count or 1))
    return {tuple(ref['key']) for ref in ordered[:limit]}


def recover_hidden_frames(records_root: Path, sessions: Iterable[str], *, recover_all: bool = False, count: int = 1) -> dict[str, Any]:
    """Unhide previously hidden frame rows in the selected sessions.

    Recovering removes piTrainer's soft-delete flags from matching JSONL rows.
    Image files are not modified. The loader will include the rows again after
    the Data page reloads the selected sessions.
    """
    session_names = _selected_session_names(sessions)
    if not session_names:
        return {
            'requested_sessions': 0,
            'recovered_count': 0,
            'metadata_rows_changed': 0,
            'files_changed': [],
            'failed_messages': ['No loaded/selected sessions are available to recover.'],
        }

    refs = _hidden_refs(records_root, session_names)
    if not refs:
        return {
            'requested_sessions': len(session_names),
            'recovered_count': 0,
            'metadata_rows_changed': 0,
            'files_changed': [],
            'failed_messages': ['No hidden frames were found in the loaded/selected session(s).'],
        }

    target_keys = _recover_target_keys(refs, recover_all=recover_all, count=count)
    changed_keys: set[tuple[str, str, str, str]] = set()
    metadata_rows_changed = 0
    files_changed: list[str] = []

    paths_by_session_file: dict[tuple[str, Path], Path] = {}
    for ref in refs:
        paths_by_session_file[(str(ref['session']), Path(ref['path']))] = Path(ref['session_dir'])

    for (session_name, path), _session_dir in paths_by_session_file.items():
        output_lines: list[str] = []
        changed_rows = 0
        for _line_no, raw_line, record in _jsonl_records(path) or []:
            if record and is_record_hidden(record):
                target = _target_from_jsonl_record(session_name, record)
                key = _target_key(target)
                if key in target_keys:
                    unmark_record_hidden(record)
                    output_lines.append(json.dumps(record, ensure_ascii=False, sort_keys=True) + '\n')
                    changed_rows += 1
                    changed_keys.add(key)
                    continue
            output_lines.append(_with_newline(raw_line))
        if changed_rows:
            with path.open('w', encoding='utf-8') as handle:
                handle.writelines(output_lines)
            metadata_rows_changed += changed_rows
            files_changed.append(f'{session_name}/{path.name}')

    failed_messages: list[str] = []
    if not changed_keys:
        failed_messages.append('Hidden frame rows were found, but none could be recovered.')

    return {
        'requested_sessions': len(session_names),
        'recovered_count': len(changed_keys),
        'metadata_rows_changed': metadata_rows_changed,
        'files_changed': files_changed,
        'failed_messages': failed_messages,
    }


def _safe_delete_candidate(path: Path, *, session_dir: Path, records_root: Path) -> bool:
    try:
        resolved = Path(path).expanduser().resolve()
        session_root = Path(session_dir).expanduser().resolve()
        records_root_resolved = Path(records_root).expanduser().resolve()
    except Exception:
        return False
    try:
        return resolved.is_file() and (resolved.is_relative_to(session_root) or resolved.is_relative_to(records_root_resolved))
    except AttributeError:
        text = str(resolved)
        return resolved.is_file() and (text.startswith(str(session_root)) or text.startswith(str(records_root_resolved)))


def _record_image_path(session_dir: Path, record: dict[str, Any]) -> Path | None:
    try:
        image_path = _resolve_image_path(session_dir, record)
    except Exception:
        image_path = None
    return image_path if image_path and image_path.exists() else None


def purge_hidden_frames(records_root: Path, sessions: Iterable[str]) -> dict[str, Any]:
    """Permanently remove hidden JSONL rows and their unreferenced image files.

    This is intentionally not exposed as a normal button. It is for the hidden
    cleanup shortcut after frames were already soft-hidden and reviewed.
    """
    session_names = _selected_session_names(sessions)
    if not session_names:
        return {
            'requested_sessions': 0,
            'purged_count': 0,
            'metadata_rows_removed': 0,
            'image_files_deleted': 0,
            'files_changed': [],
            'deleted_files': [],
            'skipped_files': [],
            'failed_messages': ['No loaded/selected sessions are available to purge.'],
        }

    hidden_refs = _hidden_refs(records_root, session_names)
    if not hidden_refs:
        return {
            'requested_sessions': len(session_names),
            'purged_count': 0,
            'metadata_rows_removed': 0,
            'image_files_deleted': 0,
            'files_changed': [],
            'deleted_files': [],
            'skipped_files': [],
            'failed_messages': ['No hidden frames were found to permanently delete.'],
        }

    hidden_keys = {tuple(ref['key']) for ref in hidden_refs}
    hidden_image_paths: set[Path] = set()
    visible_image_paths: set[Path] = set()
    files_changed: list[str] = []
    metadata_rows_removed = 0

    for session_name in session_names:
        session_dir = resolve_session_dir(records_root, session_name)
        for filename in ('labels.jsonl', 'records.jsonl'):
            path = session_dir / filename
            for _line_no, _raw_line, record in _jsonl_records(path) or []:
                if not record:
                    continue
                image_path = _record_image_path(session_dir, record)
                if image_path is None:
                    continue
                if is_record_hidden(record):
                    hidden_image_paths.add(image_path.resolve())
                else:
                    visible_image_paths.add(image_path.resolve())

    for session_name in session_names:
        session_dir = resolve_session_dir(records_root, session_name)
        for filename in ('labels.jsonl', 'records.jsonl'):
            path = session_dir / filename
            if not path.exists():
                continue
            output_lines: list[str] = []
            removed_rows = 0
            for _line_no, raw_line, record in _jsonl_records(path) or []:
                if record and is_record_hidden(record):
                    removed_rows += 1
                    continue
                output_lines.append(_with_newline(raw_line))
            if removed_rows:
                with path.open('w', encoding='utf-8') as handle:
                    handle.writelines(output_lines)
                metadata_rows_removed += removed_rows
                files_changed.append(f'{session_name}/{filename}')

    deleted_files: list[str] = []
    skipped_files: list[str] = []
    for image_path in sorted(hidden_image_paths, key=lambda path: str(path)):
        if image_path in visible_image_paths:
            skipped_files.append(f'{image_path} (still referenced by visible rows)')
            continue
        # Resolve the owning session from the image path for conservative safety.
        owning_session_dir = None
        for session_name in session_names:
            session_dir = resolve_session_dir(records_root, session_name)
            try:
                if image_path.is_relative_to(session_dir.resolve()):
                    owning_session_dir = session_dir
                    break
            except AttributeError:
                if str(image_path).startswith(str(session_dir.resolve())):
                    owning_session_dir = session_dir
                    break
        if owning_session_dir is None:
            skipped_files.append(f'{image_path} (outside loaded session folders)')
            continue
        if not _safe_delete_candidate(image_path, session_dir=owning_session_dir, records_root=records_root):
            skipped_files.append(f'{image_path} (not inside session/records root)')
            continue
        try:
            image_path.unlink()
            deleted_files.append(str(image_path))
        except OSError as exc:
            skipped_files.append(f'{image_path} ({exc})')

    return {
        'requested_sessions': len(session_names),
        'purged_count': len(hidden_keys),
        'metadata_rows_removed': metadata_rows_removed,
        'image_files_deleted': len(deleted_files),
        'files_changed': files_changed,
        'deleted_files': deleted_files,
        'skipped_files': skipped_files,
        'failed_messages': [],
    }

def hide_frames_from_training(records_root: Path, records: Iterable[dict[str, Any]]) -> dict[str, Any]:
    """Soft-delete selected frame rows by adding traceable hidden flags.

    This keeps labels.jsonl/records.jsonl rows and image files in place, so the
    action is fast and auditable. Hidden records are skipped by the loader and
    final training/validation guards.
    """
    targets_by_session: dict[str, list[dict[str, str]]] = {}
    selected_keys: dict[tuple[str, str, str, str], dict[str, str]] = {}
    for record in records:
        target = _target_from_record(record)
        session_name = target['session'].strip()
        key = _target_key(target)
        if not session_name or key in selected_keys:
            continue
        selected_keys[key] = target
        targets_by_session.setdefault(session_name, []).append(target)

    hidden_at = utc_timestamp()
    matched_keys: set[tuple[str, str, str, str]] = set()
    metadata_rows_changed = 0
    files_changed: list[str] = []

    for session_name, targets in targets_by_session.items():
        session_dir = resolve_session_dir(records_root, session_name)
        for filename in ('labels.jsonl', 'records.jsonl'):
            path = session_dir / filename
            changed_rows, file_matches = _hide_in_jsonl(path, targets, hidden_at_utc=hidden_at)
            if changed_rows:
                files_changed.append(f'{session_name}/{filename}')
            metadata_rows_changed += changed_rows
            matched_keys.update(file_matches)

    failed_messages = [
        f"Could not find frame '{_target_label(target)}' in session '{target.get('session', '')}'."
        for key, target in selected_keys.items()
        if key not in matched_keys
    ]

    return {
        'selected_count': len(selected_keys),
        'hidden_count': len(matched_keys),
        'metadata_rows_changed': metadata_rows_changed,
        'files_changed': files_changed,
        'failed_messages': failed_messages,
        'hidden_at_utc': hidden_at,
    }


def delete_frame_from_session(records_root: Path, session_name: str, frame_id: str, image_path: str, ts: str = '') -> tuple[bool, str]:
    """Backward-compatible wrapper: now soft-deletes by hiding from training."""
    result = hide_frames_from_training(records_root, [{
        'session': session_name,
        'frame_id': frame_id,
        'abs_image': image_path,
        'ts': ts,
    }])
    if result['hidden_count'] <= 0:
        failures = result.get('failed_messages') or [f"Could not find frame '{frame_id}' in session '{session_name}'."]
        return False, failures[0]
    rows = int(result.get('metadata_rows_changed', 0))
    return True, f"Hidden frame '{frame_id}' from training with traceable flags in {rows} metadata row(s). Image file was kept."
