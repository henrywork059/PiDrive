from __future__ import annotations

import os
import subprocess
import sys
import threading
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
        self._restart_lock = threading.Lock()
        self._restart_pending = False
        self._restart_requested_at = 0.0
        self._restart_error = ""

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
        before_commit = status.get("commit", "unknown")
        ok, text = self._run(["git", "pull", "--ff-only"], cwd=repo_root, timeout=120)
        after_status = self.git_status(force=True)
        after_commit = after_status.get("commit", "unknown")
        if ok:
            final = text or "Git pull finished."
            if repo_root != self.project_dir:
                final += f"\nUpdated parent repo: {repo_root}"
            if before_commit != after_commit:
                final += f"\nCommit: {before_commit} -> {after_commit}"
                final += "\nRestart Server to load the updated code."
            else:
                final += "\nNo new commit was applied."
            return True, final
        return False, text or "Git pull failed."

    def restart_status(self) -> dict:
        with self._restart_lock:
            pending = self._restart_pending
            requested_at = self._restart_requested_at
            error = self._restart_error
        message = error or "Restart re-launches the current PiServer process."
        return {
            "ok": True,
            "supported": True,
            "mode": "self-exec",
            "pending": pending,
            "requested_at": requested_at,
            "message": message,
        }

    def _perform_process_restart(self) -> None:
        server_script = (self.project_dir / "server.py").resolve()
        argv = [sys.executable, str(server_script)]
        os.chdir(self.project_dir)
        os.execv(sys.executable, argv)

    def _delayed_restart(self, delay: float) -> None:
        time.sleep(max(0.0, delay))
        try:
            self._perform_process_restart()
        except Exception as exc:
            with self._restart_lock:
                self._restart_pending = False
                self._restart_error = f"Restart failed: {exc}"

    def restart_service(self, delay: float = 0.8) -> tuple[bool, str]:
        with self._restart_lock:
            if self._restart_pending:
                return False, "Restart is already pending."
            self._restart_pending = True
            self._restart_requested_at = time.time()
            self._restart_error = ""

        thread = threading.Thread(target=self._delayed_restart, args=(delay,), daemon=True)
        thread.start()
        return True, "Restart scheduled. The page should reconnect automatically in a few seconds."
