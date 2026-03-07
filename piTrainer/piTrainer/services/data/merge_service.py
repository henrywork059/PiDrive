from __future__ import annotations

import json
import shutil
from pathlib import Path

from ...utils.path_utils import ensure_dir, safe_filename
from .record_loader_service import IMAGE_KEYS, coalesce_value


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

    target_dir = records_root / target_name
    if target_dir.exists():
        return False, f"Target session '{target_name}' already exists.", {}

    records_root.mkdir(parents=True, exist_ok=True)
    images_dir = ensure_dir(target_dir / 'images')
    output_jsonl = target_dir / 'records.jsonl'

    merged_rows: list[dict] = []
    copied_images = 0
    skipped_records = 0
    total_source_records = 0

    try:
        for session_name in selected:
            session_dir = records_root / session_name
            jsonl_path = session_dir / 'records.jsonl'
            if not jsonl_path.exists():
                continue

            with jsonl_path.open('r', encoding='utf-8') as handle:
                for line_index, line in enumerate(handle):
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        record = json.loads(line)
                    except json.JSONDecodeError:
                        skipped_records += 1
                        continue

                    total_source_records += 1
                    image_rel = str(coalesce_value(record, IMAGE_KEYS, '') or '')
                    if not image_rel:
                        skipped_records += 1
                        continue

                    source_image = (session_dir / image_rel).resolve()
                    if not source_image.exists() or not source_image.is_file():
                        skipped_records += 1
                        continue

                    suffix = source_image.suffix or '.jpg'
                    source_frame_id = str(record.get('frame_id', record.get('id', f'{line_index + 1:06d}')) or '')
                    merged_index = len(merged_rows) + 1
                    image_name = f'{merged_index:06d}_{safe_filename(session_name, default="session")}{suffix}'
                    target_image = images_dir / image_name
                    while target_image.exists():
                        merged_index += 1
                        image_name = f'{merged_index:06d}_{safe_filename(session_name, default="session")}{suffix}'
                        target_image = images_dir / image_name

                    shutil.copy2(source_image, target_image)
                    copied_images += 1

                    merged_record = dict(record)
                    merged_record['image'] = f'images/{image_name}'
                    merged_record['frame_id'] = f'merge_{copied_images:06d}'
                    merged_record['session'] = target_name
                    merged_record['merged_from_session'] = session_name
                    merged_record['source_frame_id'] = source_frame_id
                    merged_record['source_image'] = image_rel
                    merged_record['merge_index'] = copied_images
                    merged_rows.append(merged_record)

        if not merged_rows:
            shutil.rmtree(target_dir, ignore_errors=True)
            return False, 'No usable image records were found in the selected sessions.', {
                'source_sessions': len(selected),
                'copied_records': 0,
                'skipped_records': skipped_records,
            }

        with output_jsonl.open('w', encoding='utf-8') as handle:
            for record in merged_rows:
                handle.write(json.dumps(record, ensure_ascii=False) + '\n')

        message = (
            f"Merged {len(selected)} sessions into '{target_name}' with "
            f"{len(merged_rows)} frame(s); skipped {skipped_records}."
        )
        details: dict[str, int | str] = {
            'target_session': target_name,
            'source_sessions': len(selected),
            'source_records': total_source_records,
            'copied_records': len(merged_rows),
            'skipped_records': skipped_records,
        }
        return True, message, details
    except Exception as exc:
        shutil.rmtree(target_dir, ignore_errors=True)
        return False, f'Merge failed: {exc}', {}
