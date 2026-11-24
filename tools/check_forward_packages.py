"""Exercise each real candidate component patch in a disposable baseline worktree."""
import argparse
import subprocess
import tempfile
from pathlib import Path

from patch_package import COMPONENTS, build, git, validate, version


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--target", required=True, help="Trusted full candidate commit SHA")
    args = parser.parse_args()
    root = Path(git(Path.cwd(), "rev-parse", "--show-toplevel").decode().strip())
    for component, (_, marker, _, _, _) in COMPONENTS.items():
        # Find the version-changing commit on the candidate's first-parent chain.
        marker_commit = git(root, "log", "--first-parent", "-1", "--format=%H",
                            args.target, "--", component + "/" + marker).decode().strip()
        base = git(root, "rev-parse", marker_commit + "^").decode().strip()
        if version(root, args.target, component) <= version(root, base, component):
            raise ValueError("No forward component version: " + component)
        with tempfile.TemporaryDirectory(prefix="pidrive-package-") as temp:
            archive = Path(temp) / "patch.zip"
            checkout = Path(temp) / "baseline"
            manifest = build(root, component, base, args.target, archive)
            git(root, "worktree", "add", "--detach", str(checkout), base)
            try:
                assert validate(checkout, component, base, args.target, archive) == manifest
                assert git(checkout, "status", "--porcelain") == b""
            finally:
                git(root, "worktree", "remove", "--force", str(checkout))
            print(component, manifest["baseline_version"], "->", manifest["target_version"],
                  len(manifest["files"]), "changed files: dry-run passed", flush=True)


if __name__ == "__main__":
    main()
