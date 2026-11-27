"""Git-backed, changed-file-only candidate packaging. Never applies an archive."""
import argparse
import ast
import hashlib
import json
import re
import stat
import subprocess
import sys
from pathlib import Path
from zipfile import BadZipFile, ZIP_DEFLATED, ZipFile

COMPONENTS = {
    "PiSD": ("PiSD.py", "pisd/__init__.py", "__version__", (0, 11), {"pisd", "scripts", "docs", "PATCH_NOTES"}),
    "PiServer": ("server.py", "piserver/app.py", "APP_VERSION", (0, 4), {"piserver", "tests", "boot", "PATCH_NOTES"}),
    "piTrainer": ("main.py", "piTrainer/version.py", "APP_VERSION", (0, 11), {"piTrainer", "tests", "DOCS", "PACKAGING", "PATCH_NOTES"}),
}
# Owner-authorized major-family transition; keep legacy versions readable.
V1_BASELINES = {"PiSD": (0, 11, 49), "PiServer": (0, 4, 56), "piTrainer": (0, 11, 36)}
V1_FAMILY = (1, 0)
MANIFEST = "PATCH_MANIFEST.json"
ROOT_FILES = {"README.md", "AGENTS.md", "UI_DESIGN_TOKENS.md", "requirement.txt",
              "run_camera_settings_diagnostic.py", "run_windows.bat", "run_linux_mac.sh"}
EXTENSIONS = {".py", ".md", ".txt", ".js", ".cjs", ".css", ".html", ".sh", ".bat", ".ps1", ".spec", ".service"}
BLOCKED = {"config", "models", "recordings", "training_runs", "test_outputs", "cache",
           "caches", "__pycache__", "credentials", "secrets", "datasets", "exports", "frames",
           "checkpoints", "logs", "venv", "node_modules", "dist", "build"}
MAX_FILE = 10 * 1024 * 1024


def require(condition, message):
    if not condition:
        raise ValueError(message)


def git(root, *args):
    return subprocess.run(["git", "-C", str(root), *args], check=True,
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE).stdout


def digest(data):
    return hashlib.sha256(data).hexdigest()


def check_commit(root, sha):
    require(re.fullmatch(r"[0-9a-f]{40}", sha), "Use an explicitly trusted full commit SHA")
    require(git(root, "rev-parse", "--verify", sha + "^{commit}").decode().strip() == sha,
            "Not an exact commit")


def allowed(component, path):
    parts = path.split("/")
    if len(parts) < 2 or parts[0] != component:
        return False
    if any(not re.fullmatch(r"[A-Za-z0-9_][A-Za-z0-9_.-]*", p)
           or p.endswith(".") or p.lower() in BLOCKED
           or any(w in p.lower() for w in ("secret", "credential", "password", "private_key"))
           or p.split(".")[0].upper() in {"CON", "PRN", "AUX", "NUL", *("COM"+str(i) for i in range(1,10)), *("LPT"+str(i) for i in range(1,10))}
           for p in parts):
        return False
    if len(parts) == 2:
        return parts[1] in ROOT_FILES | {COMPONENTS[component][0]} or bool(
            re.fullmatch(r"requirements(?:-[a-z]+)?\.txt", parts[1]))
    # The trainer stylesheet requires one reviewed static checkmark asset.
    # Do not admit arbitrary SVGs or relax any path, history or blob checks.
    if component == "piTrainer" and path == "piTrainer/piTrainer/ui/checkbox_check.svg":
        return True
    return parts[1] in COMPONENTS[component][4] and Path(path).suffix in EXTENSIONS


def blob(root, sha, path):
    entry = git(root, "ls-tree", "-z", sha, "--", path)
    require(bool(entry), "Missing tracked file: " + path)
    meta, actual = entry.rstrip(b"\0").split(b"\t", 1)
    mode, kind, oid = meta.decode().split()
    require(actual.decode() == path and kind == "blob" and mode in {"100644", "100755"},
            "Not a regular Git file: " + path)
    size = int(git(root, "cat-file", "-s", oid))
    require(size <= MAX_FILE, "File exceeds package limit: " + path)
    return git(root, "cat-file", "blob", oid), mode


def version(root, sha, component):
    _, marker, name, family, _ = COMPONENTS[component]
    tree = ast.parse(blob(root, sha, component + "/" + marker)[0])
    values = [ast.literal_eval(n.value) for n in tree.body if isinstance(n, ast.Assign)
              and any(isinstance(t, ast.Name) and t.id == name for t in n.targets)]
    require(len(values) == 1 and isinstance(values[0], str), "Missing version marker")
    raw = values[0].replace("_", ".")
    require(re.fullmatch(r"\d+\.\d+\.\d+", raw), "Invalid version marker")
    v = tuple(map(int, raw.split(".")))
    require(v[:2] in (family, V1_FAMILY), "Wrong version family")
    if component == "piTrainer":
        patch = [ast.literal_eval(n.value) for n in tree.body if isinstance(n, ast.Assign)
                 and any(isinstance(t, ast.Name) and t.id == "PATCH_VERSION" for t in n.targets)]
        require(patch == ["piTrainer_" + raw.replace(".", "_")], "Trainer version mismatch")
    return v


def note_path(component, v):
    return f"{component}/PATCH_NOTES/PATCH_NOTES_{component}_{'_'.join(map(str,v))}.md"


def authorized_transition(root, component, base, target, old, new):
    """Permit only the owner-authorized 1.0.0 migration, with an exact baseline note."""
    if old[:2] == new[:2]:
        return False
    if old != V1_BASELINES[component] or new != (1, 0, 0):
        return False
    note = blob(root, target, note_path(component, new))[0].decode("utf-8")
    previous = ".".join(map(str, old))
    return (note.splitlines().count("Package baseline: " + base) == 1
            and note.splitlines().count("Release transition: " + previous + " -> 1.0.0") == 1)


def expected(root, component, base, target):
    require(component in COMPONENTS, "Inactive or unknown component")
    require(git(root, "rev-parse", "--is-shallow-repository").decode().strip() == "false",
            "Full Git history required for rollback checks")
    check_commit(root, base)
    check_commit(root, target)
    require(base != target, "Empty forward patch")
    require(git(root, "merge-base", base, target).decode().strip() == base, "Not a forward descendant")
    old, new = version(root, base, component), version(root, target, component)
    require(new > old, "Target version must advance")
    require(old[:2] == new[:2] or authorized_transition(root, component, base, target, old, new),
            "Unauthorized release family transition")
    blob(root, target, component + "/" + COMPONENTS[component][0])
    # Previous notes are immutable; review their content separately before approval.
    notes = sorted((p for p in git(root, "ls-tree", "-r", "--name-only", base, "--",
                                  component + "/PATCH_NOTES").decode().splitlines()
                    if re.fullmatch(re.escape(component + "/PATCH_NOTES/PATCH_NOTES_" + component) +
                                    r"_\d+_\d+_\d+\.md", p)),
                   key=lambda p: tuple(map(int, p[:-3].rsplit("_", 3)[1:])), reverse=True)
    reviewed = [p for p in notes if tuple(map(int, p[:-3].rsplit("_",3)[1:])) <= old][:4]
    require(note_path(component, old) in reviewed, "Baseline version note missing")
    history = {}
    for p in reviewed:
        data, _ = blob(root, base, p)
        require(blob(root, target, p)[0] == data, "Historical note changed: " + p)
        history[p] = digest(data)
    diff = git(root, "diff", "--name-status", "--no-renames", "-z", base, target, "--", component)
    items = diff.decode().rstrip("\0").split("\0")
    require(items != [""] and len(items) % 2 == 0, "Empty or malformed component diff")
    records, payload = {}, {}
    for status, path in zip(items[::2], items[1::2]):
        require(status in {"A", "M"} and allowed(component, path), "Forbidden change: " + path)
        require(path.casefold() not in {p.casefold() for p in records}, "Case collision")
        data, mode = blob(root, target, path)
        before = None
        if status == "M":
            prev, prev_mode = blob(root, base, path)
            require(prev_mode == mode, "Mode changes not supported")
            require(prev != data, "Unchanged file")
            before = digest(prev)
            # Catch exact reintroduction of a prior file snapshot (not just stale archives).
            history_commits = git(root, "log", "-5", "--format=%H", base, "--", path).decode().splitlines()
            for earlier in history_commits:
                if git(root, "ls-tree", "-z", earlier, "--", path):
                    historical, _ = blob(root, earlier, path)
                    require(historical == prev or historical != data,
                            "Exact historical file rollback: " + path)
        records[path] = {"operation": status, "before_sha256": before,
                         "sha256": digest(data), "size": len(data), "mode": mode}
        payload[path] = data
    require(records.get(note_path(component, new), {}).get("operation") == "A",
            "New target patch note required")
    manifest = {"schema": 1, "component": component, "baseline": base, "target_commit": target,
                "baseline_version": ".".join(map(str, old)), "target_version": ".".join(map(str, new)),
                "prior_note_hashes": history, "files": records}
    return manifest, payload


def encoded(manifest):
    return (json.dumps(manifest, sort_keys=True, indent=2) + "\n").encode()


def build(root, component, base, target, archive):
    manifest, payload = expected(root, component, base, target)
    # Exclusive creation: never overwrite an existing archive.
    with ZipFile(archive, "x", compression=ZIP_DEFLATED) as z:
        z.writestr(MANIFEST, encoded(manifest))
        for path in sorted(payload):
            z.writestr(path, payload[path])
    return manifest


def validate(root, component, base, target, archive):
    manifest, payload = expected(root, component, base, target)
    require(git(root, "rev-parse", "HEAD").decode().strip() == base, "Stale installed baseline")
    require(Path(git(root, "rev-parse", "--show-toplevel").decode().strip()).resolve() == root.resolve(),
            "Use the checkout root")
    dirty = git(root, "diff", "--name-only", "--no-renames", "-z", "HEAD", "--", component)
    require(not any(allowed(component, p) for p in dirty.decode().split("\0")),
            "Locally modified component code")
    entries = {MANIFEST: encoded(manifest), **payload}
    with ZipFile(archive) as z:
        info = z.infolist()
        require(len(info) == len(entries) and {i.filename for i in info} == set(entries),
                "Missing, duplicate or unexpected archive paths")
        for item in info:
            mode = stat.S_IFMT(item.external_attr >> 16)
            require(mode in {0, stat.S_IFREG} and not item.is_dir(), "Non-regular archive entry")
            data = entries[item.filename]
            require(item.file_size == len(data) and z.read(item) == data,
                    "Invalid manifest or file hash: " + item.filename)
    for path, record in manifest["files"].items():
        local = root / path
        for part in [local, *local.parents]:
            if part == root:
                break
            require(not part.is_symlink(), "Symlink in destination: " + path)
            if part != local:
                require(not part.exists() or part.is_dir(), "Blocked destination: " + path)
        if record["operation"] == "A":
            require(not local.exists(), "New file already exists: " + path)
        else:
            require(local.is_file() and digest(local.read_bytes()) == record["before_sha256"],
                    "Baseline file differs: " + path)
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["build", "dry-run"])
    parser.add_argument("--repo", type=Path, default=Path.cwd())
    parser.add_argument("--component", choices=COMPONENTS, required=True)
    parser.add_argument("--base", required=True)
    parser.add_argument("--target", required=True)
    parser.add_argument("--archive", type=Path, required=True)
    args = parser.parse_args()
    try:
        result = (build if args.action == "build" else validate)(
            args.repo.resolve(), args.component, args.base, args.target, args.archive)
        print(f"{args.action}: {result['component']} {result['baseline_version']} -> "
              f"{result['target_version']}, {len(result['files'])} files; no patch applied")
    except (BadZipFile, ValueError, OSError, subprocess.CalledProcessError, KeyError, SyntaxError, RuntimeError) as exc:
        print(f"Rejected: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
