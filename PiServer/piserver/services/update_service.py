from __future__ import annotations

import subprocess
from pathlib import Path


class UpdateService:
    def __init__(self, repo_root: str | Path, service_name: str = "pi_server.service"):
        self.repo_root = Path(repo_root)
        self.service_name = service_name

    def _run(self, args: list[str]) -> tuple[bool, str]:
        try:
            proc = subprocess.run(
                args,
                cwd=str(self.repo_root),
                capture_output=True,
                text=True,
                timeout=60,
            )
            text = (proc.stdout or "") + ("\n" + proc.stderr if proc.stderr else "")
            return proc.returncode == 0, text.strip()
        except Exception as exc:
            return False, str(exc)

    def git_status(self) -> dict:
        git_dir = self.repo_root / ".git"
        if not git_dir.exists():
            return {"ok": False, "message": "This folder is not a Git repository."}
        ok_branch, branch = self._run(["git", "rev-parse", "--abbrev-ref", "HEAD"])
        ok_commit, commit = self._run(["git", "rev-parse", "--short", "HEAD"])
        ok_dirty, dirty = self._run(["git", "status", "--short"])
        return {
            "ok": ok_branch and ok_commit,
            "branch": branch.strip() if ok_branch else "unknown",
            "commit": commit.strip() if ok_commit else "unknown",
            "dirty": bool(dirty.strip()) if ok_dirty else False,
            "message": "" if ok_branch and ok_commit else "Unable to read Git status.",
        }

    def git_pull(self) -> tuple[bool, str]:
        git_dir = self.repo_root / ".git"
        if not git_dir.exists():
            return False, "This folder is not a Git repository."
        ok, text = self._run(["git", "pull", "--ff-only"])
        return ok, text or ("Git pull finished." if ok else "Git pull failed.")

    def restart_service(self) -> tuple[bool, str]:
        ok, text = self._run(["systemctl", "restart", self.service_name])
        return ok, text or ("Restart requested." if ok else "Service restart failed.")
