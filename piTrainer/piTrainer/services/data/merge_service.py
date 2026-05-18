from __future__ import annotations

import json
import shutil
from pathlib import Path

from ...utils.path_utils import ensure_dir, safe_filename
from .record_loader_service import load_records_dataframe


def merge_sessions(
    records_root: Path,
    session_names: list[str],
    merged_session_name: str,
) -> tuple[bool, str, dict[str, int | str]]:
    selected = [name for name in session_names if str(name).strip()]
    if len(selected) < 2:
        return False, 'Select at least 2 sessions to merge.', {}

    target_name = safe_filename(merged_session_name, default='merged_session')
    if not target_name:
        return False, 'Enter a valid merged session name.', {}
    if target_name in selected:
        return False, 'Merged session name must be different from the source sessions.', {}

    target_dir = Path(records_root).expanduser().resolve() / target_name
    if target_dir.exists():
        return False, f"Target session '{target_name}' already exists.", {}

    Path(records_root).mkdir(parents=True, exist_ok=True)
    images_dir = ensure_dir(target_dir / 'images')
    output_records_jsonl = target_dir / 'records.jsonl'
    output_labels_jsonl = target_dir / 'labels.jsonl'

    merged_records: list[dict] = []
    merged_labels: list[dict] = []
    copied_images = 0
    skipped_records = 0
    total_source_records = 0

    try:
        for session_name in selected:
            df = load_records_dataframe(Path(records_root), [session_name])
            if df.empty:
                continue
            total_source_records += len(df)
            for row_index, row in df.iterrows():
                source_image = Path(str(row.get('abs_image', '')))
                if not source_image.exists() or not source_image.is_file():
                    skipped_records += 1
                    continue

                suffix = source_image.suffix or '.jpg'
                merged_index = copied_images + 1
                image_name = f'{merged_index:06d}_{safe_filename(session_name, default="session")}{suffix}'
                target_image = images_dir / image_name
                while target_image.exists():
                    merged_index += 1
                    image_name = f'{merged_index:06d}_{safe_filename(session_name, default="session")}{suffix}'
                    target_image = images_dir / image_name

                shutil.copy2(source_image, target_image)
                copied_images += 1
                image_rel = f'images/{image_name}'
                steering = float(row.get('steering', 0.0) or 0.0)
                throttle = float(row.get('throttle', 0.0) or 0.0)
                overlay_settings = row.get('overlay_settings') if isinstance(row.get('overlay_settings'), dict) else {}
                overlay_schema_version = str(row.get('overlay_schema_version', '') or '')
                source_frame_id = str(row.get('frame_id', row_index + 1) or '')
                merged_frame_id = f'merge_{copied_images:06d}'
                timestamp_utc = str(row.get('ts', '') or '')

                label_record = {
                    'frame': image_rel,
                    'steering': steering,
                    'throttle': throttle,
                    'timestamp_utc': timestamp_utc,
                    'source_frame_seq': copied_images,
                    'session_id': target_name,
                    'merged_from_session': str(session_name),
                    'source_frame_id': source_frame_id,
                    'overlay_settings': overlay_settings,
                    'overlay_schema_version': overlay_schema_version,
                }
                full_record = {
                    'frame_id': merged_frame_id,
                    'image': image_rel,
                    'frame': image_rel,
                    'session': target_name,
                    'session_id': target_name,
                    'steering': steering,
                    'throttle': throttle,
                    'timestamp_utc': timestamp_utc,
                    'source_frame_seq': copied_images,
                    'merged_from_session': str(session_name),
                    'source_frame_id': source_frame_id,
                    'source_image': str(source_image),
                    'merge_index': copied_images,
                    'overlay_settings': overlay_settings,
                    'overlay_schema_version': overlay_schema_version,
                    'training_label': label_record,
                }
                merged_records.append(full_record)
                merged_labels.append(label_record)

        if not merged_records:
            shutil.rmtree(target_dir, ignore_errors=True)
            return False, 'No usable image records were found in the selected sessions.', {
                'source_sessions': len(selected),
                'copied_records': 0,
                'skipped_records': skipped_records,
            }

        with output_records_jsonl.open('w', encoding='utf-8') as handle:
            for record in merged_records:
                handle.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + '\n')
        with output_labels_jsonl.open('w', encoding='utf-8') as handle:
            for record in merged_labels:
                handle.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + '\n')

        message = (
            f"Merged {len(selected)} sessions into '{target_name}' with "
            f"{len(merged_records)} frame(s); skipped {skipped_records}."
        )
        details: dict[str, int | str] = {
            'target_session': target_name,
            'source_sessions': len(selected),
            'source_records': total_source_records,
            'copied_records': len(merged_records),
            'skipped_records': skipped_records,
        }
        return True, message, details
    except Exception as exc:
        shutil.rmtree(target_dir, ignore_errors=True)
        return False, f'Merge failed: {exc}', {}
