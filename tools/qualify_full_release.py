"""Build and verify exact-Git full source candidate archives, never publish."""
import argparse
import hashlib
import json
import re
import subprocess
import zipfile
from pathlib import Path, PurePosixPath

COMPONENTS = {"PiSD": "PiSD.py", "PiServer": "server.py", "piTrainer": "main.py"}
BASE = "7f8fcf5a5cec1a246e970a679d00cb9a3b0d169c"
EXTENSIONS = {".py", ".md", ".css", ".js", ".html", ".txt", ".cjs", ".service", ".ps1", ".spec", ".svg", ".sh", ".bat", ".json"}
CONFIG = {"PiSD/config/defaults.json", "piTrainer/config/version_gate.json"}
# These exact reviewed tracked files are synthetic test input / documentation, not user data.
REVIEWED_FIXTURES = {
    "PiSD/scripts/fixtures/steering_replay.jsonl": "311f9cf1a97f6319cc12e770097c5eace3c3adf9",
    "PiSD/test_outputs/README.md": "eaaba9a019b0889dcc0f7c5164dabc67f41bcc04",
}
EXCLUDED_PARTS = {"__pycache__", "test_outputs", "models", "recordings", "datasets", "dist", "dist_exe", "build", "build_exe", "exports", "logs", ".venv", "cache"}
SECRET = re.compile(rb"-----BEGIN (?:RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----|gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{40,}|AKIA[0-9A-Z]{16}")

def git(*args):
    return subprocess.check_output(["git", *args])

def digest(data):
    return hashlib.sha256(data).hexdigest()

def inventory(revision, component):
    included, excluded = {}, {}
    for entry in git("ls-tree", "-r", "-z", revision, "--", component).split(b"\0"):
        if not entry:
            continue
        meta, raw_path = entry.split(b"\t", 1)
        mode, kind, oid = meta.decode().split()
        path = raw_path.decode("utf-8")
        p = PurePosixPath(path)
        if not path.startswith(component + "/") or p.is_absolute() or ".." in p.parts or "\\" in path:
            raise ValueError("Unsafe source path: " + path)
        if mode not in ("100644", "100755") or kind != "blob":
            raise ValueError("Unsupported Git entry: " + path)
        reason = None
        if path in REVIEWED_FIXTURES:
            if oid != REVIEWED_FIXTURES[path]:
                raise ValueError("Reviewed fixture changed; re-review before packaging: " + path)
        elif any(x.lower() in EXCLUDED_PARTS for x in p.parts[1:]) or p.suffix in {".pyc", ".jsonl"}:
            reason = "generated/cache/data"
        elif "config" in p.parts and p.suffix == ".json" and path not in CONFIG:
            reason = "local runtime configuration"
        elif p.suffix not in EXTENSIONS or p.name.startswith(".") or re.search(r"(?i)(?:^|[._-])(secret|credential|password|private_key)(?:[._-]|$)", p.name):
            raise ValueError("Unreviewed archive path: " + path)
        if reason:
            excluded[path] = reason
            continue
        data = git("cat-file", "blob", oid)
        if SECRET.search(data):
            raise ValueError("Potential credential in tracked source: " + path)
        included[path] = (data, mode, oid)
    if component + "/" + COMPONENTS[component] not in included:
        raise ValueError("Missing canonical launcher")
    for path in REVIEWED_FIXTURES:
        if path.startswith(component + "/") and path not in included:
            raise ValueError("Missing reviewed test fixture: " + path)
    return included, excluded

def build(output, revision):
    if git("rev-parse", "HEAD").decode().strip() != revision:
        raise ValueError("Exact checkout required")
    subprocess.run(["git", "merge-base", "--is-ancestor", BASE, revision], check=True)
    output.mkdir(parents=True, exist_ok=False)
    index = {"revision": revision, "status": "provisional", "archives": []}
    for component in COMPONENTS:
        included, excluded = inventory(revision, component)
        name = component + "_1_0_0_candidate.zip"
        archive = output / name
        manifest = {"revision": revision, "component": component, "version": "1.0.0",
                    "files": {p: {"sha256": digest(d), "size": len(d), "mode": m, "git_blob": o}
                              for p, (d,m,o) in included.items()}, "excluded": excluded}
        with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as z:
            for p, (data, mode, _) in sorted(included.items()):
                info = zipfile.ZipInfo(p, (1980,1,1,0,0,0))
                info.create_system = 3
                info.external_attr = int(mode, 8) << 16
                info.compress_type = zipfile.ZIP_DEFLATED
                z.writestr(info, data)
        with zipfile.ZipFile(archive) as z:
            if z.testzip() is not None or sorted(z.namelist()) != sorted(included):
                raise ValueError("Archive CRC or member mismatch")
            for p, (_, mode, oid) in included.items():
                got = z.read(p)
                if digest(got) != manifest["files"][p]["sha256"] or got != git("cat-file", "blob", oid):
                    raise ValueError("Archive byte mismatch: " + p)
                if z.getinfo(p).external_attr >> 16 != int(mode, 8):
                    raise ValueError("Archive mode mismatch: " + p)
        (output / (name+".manifest.json")).write_text(json.dumps(manifest, indent=2)+"\n", encoding="utf-8")
        index["archives"].append({"name": name, "sha256": digest(archive.read_bytes()), "files": len(included), "excluded": len(excluded)})
    (output / "index.json").write_text(json.dumps(index, indent=2)+"\n", encoding="utf-8")
    (output / "SHA256SUMS").write_text("".join(a["sha256"]+"  "+a["name"]+"\n" for a in index["archives"]), encoding="utf-8")
    print(json.dumps(index, indent=2))

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--revision", required=True)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    build(args.output, args.revision)
