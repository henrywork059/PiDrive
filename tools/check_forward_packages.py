"""Exercise each real candidate component patch in a disposable baseline worktree."""
import argparse
import re
import subprocess
import tempfile
from pathlib import Path

from patch_package import COMPONENTS, blob, build, check_commit, git, note_path, validate, version



def package_base(root, target, component):
    """Resolve a stacked candidate's declared base, or actual version change.

    A marker file can contain ordinary code (PiServer app.py). A touch to it
    is not itself a version bump. For a staged milestone, the new immutable
    note declares the previous candidate before *any* milestone changes.
    All existing build/validate ancestry, note, path and hash checks remain.
    """
    check_commit(root, target)
    current = version(root, target, component)
    note = blob(root, target, note_path(component, current))[0].decode("utf-8")
    declared = [line for line in note.splitlines() if line.startswith("Package baseline:")]
    if declared:
        if len(declared) != 1 or not re.fullmatch(r"Package baseline: [0-9a-f]{40}", declared[0]):
            raise ValueError("Invalid package baseline declaration: " + component)
        base = declared[0].split()[-1]
        check_commit(root, base)
        if base not in git(root, "rev-list", "--first-parent", target).decode().splitlines():
            raise ValueError("Package baseline must be a first-parent ancestor: " + component)
    else:
        marker = component + "/" + COMPONENTS[component][1]
        commits = git(root, "log", "--first-parent", "--format=%H", target, "--", marker).decode().splitlines()
        base = None
        for commit in commits:
            parents = git(root, "rev-list", "--parents", "-n", "1", commit).decode().split()
            if len(parents) < 2:
                break
            parent = parents[1]
            if version(root, commit, component) != version(root, parent, component):
                base = parent
                break
        if base is None:
            raise ValueError("No actual version-changing commit: " + component)
    previous = version(root, base, component)
    if current != (previous[0], previous[1], previous[2] + 1):
        raise ValueError("No one-step forward component version: " + component)
    return base


def component_target(root, target, component, inherited_from=None):
    """Reuse a previously qualified component source only if its tree is identical.

    A merged stacked PR can move its package baseline off main's first-parent
    chain. Do not weaken package_base: validate the original exact source
    revision for an unchanged component, never an altered component.
    """
    check_commit(root, target)
    if inherited_from is None:
        return target
    check_commit(root, inherited_from)
    if git(root, "merge-base", inherited_from, target).decode().strip() != inherited_from:
        raise ValueError("Inherited package source must be an ancestor")
    if (git(root, "rev-parse", target + ":" + component)
            == git(root, "rev-parse", inherited_from + ":" + component)):
        return inherited_from
    return target


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--target", required=True, help="Trusted full candidate commit SHA")
    parser.add_argument("--inherited-from", help="Exact previously qualified ancestor; identical component trees only")
    args = parser.parse_args()
    root = Path(git(Path.cwd(), "rev-parse", "--show-toplevel").decode().strip())
    for component in COMPONENTS:
        target = component_target(root, args.target, component, args.inherited_from)
        base = package_base(root, target, component)
        with tempfile.TemporaryDirectory(prefix="pidrive-package-") as temp:
            archive = Path(temp) / "patch.zip"
            checkout = Path(temp) / "baseline"
            manifest = build(root, component, base, target, archive)
            git(root, "worktree", "add", "--detach", str(checkout), base)
            try:
                assert validate(checkout, component, base, target, archive) == manifest
                assert git(checkout, "status", "--porcelain") == b""
            finally:
                git(root, "worktree", "remove", "--force", str(checkout))
            print(component, "package source", target, manifest["baseline_version"], "->", manifest["target_version"],
                  len(manifest["files"]), "changed files: dry-run passed", flush=True)


if __name__ == "__main__":
    main()
