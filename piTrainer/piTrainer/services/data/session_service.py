from __future__ import annotations

from pathlib import Path


SKIP_SESSION_DIR_NAMES = {"single_captures", "snapshots", "snapshot", "captures", "frames", "images", "__pycache__"}
MAX_FALLBACK_SCAN_DEPTH = 4


def _candidate_roots(records_root: Path) -> list[Path]:
    """Return roots that may contain PiTrainer/PiSD session folders."""
    root = Path(records_root).expanduser().resolve()
    roots = [root]
    recordings_root = root / "recordings"
    if recordings_root.exists() and recordings_root.is_dir():
        roots.insert(0, recordings_root)
    return roots


def _looks_like_training_session(session_dir: Path) -> bool:
    if not session_dir.is_dir():
        return False
    if session_dir.name in SKIP_SESSION_DIR_NAMES:
        return False

    labels_path = session_dir / "labels.jsonl"
    records_path = session_dir / "records.jsonl"
    has_frames = (session_dir / "frames").is_dir()
    has_images = (session_dir / "images").is_dir()

    # Current PiSD format: labels.jsonl + frames/.
    if labels_path.exists() and has_frames:
        return True

    # Older piTrainer/PiCar-style format: records.jsonl + images/.
    if records_path.exists() and has_images:
        return True

    # PiSD fallback/debug format: records.jsonl can still point at frames/.
    if records_path.exists() and has_frames:
        return True

    return False


def _iter_likely_session_dirs(scan_root: Path):
    """Yield likely session folders without walking every frame image.

    PiSD can have many JPG files under frames/. A blind rglob over the whole
    recording tree becomes slow as datasets grow. This walker checks the known
    layouts first and prunes heavy image folders.
    """
    scan_root = Path(scan_root)

    # Direct session folder.
    yield scan_root

    # Latest PiSD: recordings/YYYY-MM-DD/session_id/ or YYYY-MM-DD/session_id/
    for day_dir in sorted(scan_root.iterdir() if scan_root.exists() else []):
        if not day_dir.is_dir() or day_dir.name in SKIP_SESSION_DIR_NAMES:
            continue
        yield day_dir
        for session_dir in sorted(day_dir.iterdir()):
            if session_dir.is_dir() and session_dir.name not in SKIP_SESSION_DIR_NAMES:
                yield session_dir

    # Legacy/direct roots: root/session_id/
    for session_dir in sorted(scan_root.iterdir() if scan_root.exists() else []):
        if session_dir.is_dir() and session_dir.name not in SKIP_SESSION_DIR_NAMES:
            yield session_dir


def _bounded_fallback_dirs(scan_root: Path):
    """Fallback scan for unusual roots, with depth and folder pruning."""
    root_depth = len(scan_root.parts)
    stack = [scan_root]
    while stack:
        current = stack.pop()
        yield current
        depth = len(current.parts) - root_depth
        if depth >= MAX_FALLBACK_SCAN_DEPTH:
            continue
        try:
            children = list(current.iterdir())
        except OSError:
            continue
        for child in reversed(children):
            if not child.is_dir():
                continue
            if child.name in SKIP_SESSION_DIR_NAMES:
                continue
            stack.append(child)


def _session_display_name(scan_root: Path, entry: Path) -> str:
    return entry.relative_to(scan_root).as_posix()


def list_sessions(records_root: Path) -> list[str]:
    """List loadable training sessions under a records root.

    Supports both older direct session folders and the latest PiSD layout:

        PiSD/recordings/YYYY-MM-DD/YYYYMMDD_HHMMSS_manual_drive_xxxxxxxx/
          frames/
          labels.jsonl
          records.jsonl

    Single-capture/snapshot buckets are skipped by default because they are not
    continuous drive sessions for behavioural cloning.
    """
    root = Path(records_root).expanduser().resolve()
    if not root.exists() or not root.is_dir():
        return []

    found: dict[str, Path] = {}
    for scan_root in _candidate_roots(root):
        if not scan_root.exists() or not scan_root.is_dir():
            continue
        root_recordings = root / "recordings"
        checked: set[Path] = set()
        for iterator in (_iter_likely_session_dirs(scan_root), _bounded_fallback_dirs(scan_root)):
            for entry in iterator:
                try:
                    entry = entry.resolve()
                except OSError:
                    continue
                if entry in checked:
                    continue
                checked.add(entry)
                if not entry.is_dir():
                    continue
                try:
                    rel_parts = entry.relative_to(scan_root).parts
                except ValueError:
                    continue
                if scan_root == root and root_recordings.exists() and rel_parts and rel_parts[0] == "recordings":
                    continue
                if any(part in SKIP_SESSION_DIR_NAMES for part in rel_parts):
                    continue
                if _looks_like_training_session(entry):
                    found.setdefault(_session_display_name(scan_root, entry), entry)

    return sorted(found)


def resolve_session_dir(records_root: Path, session_name: str) -> Path:
    """Resolve a displayed session name back to its real folder."""
    root = Path(records_root).expanduser().resolve()
    clean_name = str(session_name).strip().strip("/\\")
    candidates = [root / clean_name, root / "recordings" / clean_name]
    for candidate in candidates:
        if candidate.exists() and candidate.is_dir():
            return candidate.resolve()
    return candidates[0].resolve()
