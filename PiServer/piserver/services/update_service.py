from __future__ import annotations

import subprocess
import time
from pathlib import Path


class UpdateService:
    def __init__(self, project_dir: str | Path, service_name: str = "pi_server.service"):
        self.project_dir = Path(project_dir).resolve()
        self.service_name = service_name
        self._git_cache = {"ts": 0.0, "data": {"ok": False, "message": "Git status not loaded yet."}}
        self._git_cache_ttl = 5.0

    def _run(self, args: list[str], cwd: str | Path | None = None) -> tuple[bool, str]:
        try:
            proc = subprocess.run(
                args,
                cwd=str(cwd or self.project_dir),
                capture_output=True,
                text=True,
                timeout=60,
            )
            text = (proc.stdout or "") + ("\n" + proc.stderr if proc.stderr else "")
            return proc.returncode == 0, text.strip()
        except Exception as exc:
            return False, str(exc)

    def _resolve_git_paths(self) -> tuple[bool, Path | None, str]:
        ok_inside, inside = self._run(["git", "rev-parse", "--is-inside-work-tree"])
        if not ok_inside or inside.strip().lower() != "true":
            return False, None, (
                "PiServer is not inside a Git checkout. Standalone zip installs cannot use Update from Git. "
                "Run PiServer from /home/pi/PiDrive/PiServer or another real clone of the PiDrive repo."
            )

        ok_root, root_text = self._run(["git", "rev-parse", "--show-toplevel"])
        if not ok_root:
            return False, None, "Git checkout found, but the repo root could not be resolved."

        return True, Path(root_text.strip()).resolve(), ""

    def git_status(self, force: bool = False) -> dict:
        now = time.time()
        if not force and (now - float(self._git_cache.get("ts", 0.0))) < self._git_cache_ttl:
            return dict(self._git_cache["data"])

        ok_repo, git_root, repo_message = self._resolve_git_paths()
        if not ok_repo or git_root is None:
            data = {
                "ok": False,
                "message": repo_message,
                "project_dir": str(self.project_dir),
                "git_root": None,
                "project_rel": None,
                "branch": "-",
                "commit": "-",
                "dirty": False,
            }
            self._git_cache = {"ts": now, "data": data}
            return dict(data)

        ok_branch, branch = self._run(["git", "rev-parse", "--abbrev-ref", "HEAD"], cwd=git_root)
        ok_commit, commit = self._run(["git", "rev-parse", "--short", "HEAD"], cwd=git_root)
        ok_dirty, dirty = self._run(["git", "status", "--short", "--", str(self.project_dir)], cwd=git_root)
        try:
            rel_project = str(self.project_dir.relative_to(git_root)) or "."
        except ValueError:
            rel_project = str(self.project_dir)

        data = {
            "ok": ok_branch and ok_commit,
            "branch": branch.strip() if ok_branch else "unknown",
            "commit": commit.strip() if ok_commit else "unknown",
            "dirty": bool(dirty.strip()) if ok_dirty else False,
            "message": "" if ok_branch and ok_commit else "Unable to read Git status.",
            "project_dir": str(self.project_dir),
            "git_root": str(git_root),
            "project_rel": rel_project,
        }
        self._git_cache = {"ts": now, "data": data}
        return dict(data)

    def git_pull(self) -> tuple[bool, str]:
        ok_repo, git_root, repo_message = self._resolve_git_paths()
        if not ok_repo or git_root is None:
            return False, repo_message

        ok_remote, remote_text = self._run(["git", "remote", "get-url", "origin"], cwd=git_root)
        if not ok_remote:
            return False, "Git checkout found, but no origin remote is configured for updates."

        ok, text = self._run(["git", "pull", "--ff-only", "origin"], cwd=git_root)
        self._git_cache["ts"] = 0.0
        prefix = f"Repo root: {git_root}\nProject: {self.project_dir}\nOrigin: {remote_text.strip()}\n"
        return ok, prefix + (text or ("Git pull finished." if ok else "Git pull failed."))

    def restart_service(self) -> tuple[bool, str]:
        ok, text = self._run(["systemctl", "restart", self.service_name], cwd=self.project_dir)
        return ok, text or ("Restart requested." if ok else "Service restart failed.")
