from __future__ import annotations

import subprocess
import time
from pathlib import Path


class UpdateService:
    def __init__(self, project_dir: str | Path, service_name: str = "pi_server.service", cache_ttl: float = 3.0):
        self.project_dir = Path(project_dir).resolve()
        self.service_name = service_name
        self.cache_ttl = max(0.0, float(cache_ttl))
        self.repo_root = self._discover_repo_root(self.project_dir)
        self._git_cache: dict | None = None
        self._git_cache_at = 0.0

    def _discover_repo_root(self, start_dir: Path) -> Path | None:
        start_dir = Path(start_dir).resolve()
        for candidate in [start_dir, *start_dir.parents]:
            if (candidate / ".git").exists():
                return candidate
        try:
            proc = subprocess.run(
                ["git", "rev-parse", "--show-toplevel"],
                cwd=str(start_dir),
                capture_output=True,
                text=True,
                timeout=15,
            )
            if proc.returncode == 0:
                root = (proc.stdout or "").strip()
                return Path(root).resolve() if root else None
        except Exception:
            pass
        return None

    def _refresh_repo_root(self) -> Path | None:
        self.repo_root = self._discover_repo_root(self.project_dir)
        return self.repo_root

    def _run(self, args: list[str], cwd: Path | None = None, timeout: int = 60) -> tuple[bool, str]:
        try:
            proc = subprocess.run(
                args,
                cwd=str((cwd or self.project_dir).resolve()),
                capture_output=True,
                text=True,
                timeout=timeout,
            )
            text = (proc.stdout or "") + ("\n" + proc.stderr if proc.stderr else "")
            return proc.returncode == 0, text.strip()
        except Exception as exc:
            return False, str(exc)

    def git_status(self, force: bool = False) -> dict:
        now = time.monotonic()
        if not force and self._git_cache is not None and (now - self._git_cache_at) <= self.cache_ttl:
            return dict(self._git_cache)

        repo_root = self._refresh_repo_root()
        if repo_root is None:
            status = {
                "ok": False,
                "project_dir": str(self.project_dir),
                "repo_root": "",
                "project_relpath": "",
                "branch": "unknown",
                "commit": "unknown",
                "remote": "",
                "dirty": False,
                "message": "No Git repository was found for this PiServer folder.",
            }
            self._git_cache = status
            self._git_cache_at = now
            return dict(status)

        ok_branch, branch = self._run(["git", "rev-parse", "--abbrev-ref", "HEAD"], cwd=repo_root, timeout=15)
        ok_commit, commit = self._run(["git", "rev-parse", "--short", "HEAD"], cwd=repo_root, timeout=15)
        ok_dirty, dirty = self._run(["git", "status", "--short"], cwd=repo_root, timeout=20)
        ok_remote, remote = self._run(["git", "config", "--get", "remote.origin.url"], cwd=repo_root, timeout=15)
        try:
            relpath = str(self.project_dir.relative_to(repo_root))
        except ValueError:
            relpath = ""

        ok = ok_branch and ok_commit
        message = "" if ok else "Unable to read Git status."
        if ok and repo_root != self.project_dir:
            message = f"PiServer is running inside parent repo: {repo_root.name}"
        elif ok:
            message = "PiServer is running at the repo root."

        status = {
            "ok": ok,
            "project_dir": str(self.project_dir),
            "repo_root": str(repo_root),
            "project_relpath": relpath,
            "branch": branch.strip() if ok_branch else "unknown",
            "commit": commit.strip() if ok_commit else "unknown",
            "remote": remote.strip() if ok_remote else "",
            "dirty": bool(dirty.strip()) if ok_dirty else False,
            "message": message,
        }
        self._git_cache = status
        self._git_cache_at = now
        return dict(status)

    def git_pull(self) -> tuple[bool, str]:
        status = self.git_status(force=True)
        if not status.get("ok"):
            return False, status.get("message") or "This folder is not a Git repository."
        if status.get("dirty"):
            return False, "Git has local modified files. Commit, stash, or discard them before updating."
        repo_root = Path(status["repo_root"])
        ok, text = self._run(["git", "pull", "--ff-only"], cwd=repo_root, timeout=120)
        self.git_status(force=True)
        if ok:
            final = text or "Git pull finished."
            if repo_root != self.project_dir:
                final += f"\nUpdated parent repo: {repo_root}"
            return True, final
        return False, text or "Git pull failed."

    def restart_service(self) -> tuple[bool, str]:
        ok, text = self._run(["systemctl", "restart", self.service_name], cwd=self.project_dir, timeout=60)
        return ok, text or ("Restart requested." if ok else "Service restart failed.")
