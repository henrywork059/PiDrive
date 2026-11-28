"""Compare actual transfer ZIP to built onedir, then extract for frozen EXE test."""
import hashlib
import json
import sys
import zipfile
from pathlib import Path, PurePosixPath

def sha(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()

def main(archive, source, dest, report):
    expected = {"PiTrainer/" + p.relative_to(source).as_posix(): p for p in source.rglob("*") if p.is_file()}
    if "PiTrainer/PiTrainer.exe" not in expected:
        raise ValueError("Missing executable")
    with zipfile.ZipFile(archive) as z:
        names = [i.filename for i in z.infolist() if not i.is_dir()]
        if len(names) != len(set(n.casefold() for n in names)) or set(names) != set(expected):
            raise ValueError("Transfer archive membership differs from build")
        hashes = {}
        for name in names:
            p = PurePosixPath(name)
            if p.is_absolute() or ".." in p.parts or "\\" in name or ":" in name:
                raise ValueError("Unsafe ZIP path")
            if (z.getinfo(name).external_attr >> 16) & 0o170000 == 0o120000:
                raise ValueError("Symlink ZIP member")
            with z.open(name) as stream:
                actual = hashlib.file_digest(stream, "sha256").hexdigest()
            if actual != sha(expected[name]):
                raise ValueError("File hash mismatch: " + name)
            hashes[name] = actual
        if dest.exists():
            raise ValueError("Extraction destination must be new")
        z.extractall(dest)
    for name, value in hashes.items():
        if sha(dest / name) != value:
            raise ValueError("Extracted bytes mismatch: " + name)
    report.write_text(json.dumps({"archive_sha256": sha(archive), "files": hashes}, indent=2), encoding="utf-8")

if __name__ == "__main__":
    main(*map(Path, sys.argv[1:]))
