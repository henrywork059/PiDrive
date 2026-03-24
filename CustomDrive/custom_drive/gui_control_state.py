from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any


@dataclass
class GuiControlState:
    app_name: str = "CustomDrive GUI Control"
    active_page: str = "manual"
    banner: str = "GUI shell ready. Add real controls panel by panel."
    notes: list[str] = field(default_factory=lambda: [
        "PiServer-style GUI scaffold loaded.",
        "Old runtime-heavy web page is bypassed for now.",
        "Use this page as the new GUI control base.",
    ])
    created_at: float = field(default_factory=time.time)

    def set_page(self, page: str | None) -> str:
        value = str(page or "manual").strip().lower() or "manual"
        self.active_page = value
        return self.active_page

    def snapshot(self) -> dict[str, Any]:
        uptime = max(0.0, time.time() - float(self.created_at))
        return {
            "ok": True,
            "app_name": self.app_name,
            "active_page": self.active_page,
            "banner": self.banner,
            "notes": list(self.notes),
            "gui_ready": True,
            "preview": "placeholder",
            "runtime_mode": "gui-shell",
            "uptime_s": round(uptime, 1),
            "panels": {
                "status": "ready",
                "viewer": "empty",
                "drive": "empty",
                "debug": "empty",
                "settings": "theme-local",
            },
        }
