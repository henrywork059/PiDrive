"""Static import inventory for active checked-in code; validate the installed profile."""
import argparse
import ast
import importlib.util
import subprocess
import sys
from collections import defaultdict
from pathlib import Path

PROFILES = {
    "PiSD": ("PiSD.py", "pisd", {"RPi", "picamera2", "libcamera", "tflite_runtime", "ai_edge_litert", "tensorflow"}),
    "PiServer": ("server.py", "piserver", {"RPi", "picamera2", "libcamera", "tflite_runtime", "tensorflow"}),
    "piTrainer": ("main.py", "piTrainer", set()),
}


def imported(path):
    for node in ast.walk(ast.parse(path.read_bytes(), filename=str(path))):
        if isinstance(node, ast.Import):
            yield from (a.name.split(".")[0] for a in node.names)
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            yield node.module.split(".")[0]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("component", choices=PROFILES)
    parser.add_argument("--desktop-only", action="store_true")
    args = parser.parse_args()
    launcher, package, optional = PROFILES[args.component]
    optional = set(optional)
    if args.desktop_only:
        if args.component != "piTrainer":
            parser.error("--desktop-only applies only to piTrainer")
        optional.update({"tensorflow", "tflite_runtime", "absl"})
    elif args.component == "piTrainer":
        optional.add("tflite_runtime")  # fallback, TensorFlow is the full install
    root = Path(__file__).resolve().parents[1]
    prefix = args.component + "/"
    tracked = subprocess.check_output(["git", "-C", str(root), "ls-files", "-z", "--", args.component])
    paths = [p for p in tracked.decode().split("\0") if p.endswith(".py")]
    local = {package, *(Path(p).stem for p in paths)}
    groups = {"runtime": defaultdict(set), "development/other": defaultdict(set)}
    for name in paths:
        rel = name[len(prefix):]
        group = "runtime" if rel == launcher or rel.startswith(package + "/") else "development/other"
        for dep in imported(root / name):
            if dep not in sys.stdlib_module_names and dep not in local:
                groups[group][dep].add(rel)
    missing = []
    for group, dependencies in groups.items():
        print(group + ":")
        for dep, locations in sorted(dependencies.items()):
            present = importlib.util.find_spec(dep) is not None
            status = "optional" if dep in optional else ("available" if present else "not installed")
            print(f"  {dep}: {status} ({len(locations)} source files)")
            if group == "runtime" and dep not in optional and not present:
                missing.append((dep, sorted(locations)))
    if missing:
        for dep, files in missing:
            print("Missing runtime import:", dep, ", ".join(files), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
