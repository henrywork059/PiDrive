"""Opt-in, bounded Chromium console metadata capture; never records message text."""
from collections import deque
from datetime import datetime, timezone
import time
from urllib.parse import urlsplit

LEVELS = frozenset({"log", "debug", "info", "error", "warning", "dir", "dirxml",
                    "table", "trace", "clear", "startGroup", "startGroupCollapsed",
                    "endGroup", "assert", "profile", "profileEnd", "count", "timeEnd"})


class BrowserObserver:
    def __init__(self, control_port, pisd_port, capacity=400):
        if (type(control_port) is not int or type(pisd_port) is not int
                or not 1 <= control_port <= 65535 or not 1 <= pisd_port <= 65535
                or control_port == pisd_port):
            raise ValueError("Distinct local ports required.")
        if type(capacity) is not int or not 1 <= capacity <= 400:
            raise ValueError("Capacity must be 1–400.")
        self._ports = {control_port: "controller", pisd_port: "pisd"}
        self._events = deque(maxlen=capacity)
        self._started = time.monotonic()
        self._total = 0

    def _scope(self, url):
        try:
            parsed = urlsplit(url)
            if (parsed.scheme == "http" and parsed.hostname == "127.0.0.1"
                    and parsed.username is None and parsed.password is None):
                return self._ports.get(parsed.port or 80)
        except (TypeError, ValueError):
            pass
        return None

    def _append(self, scope, kind, level, attribution):
        self._total += 1
        self._events.append({"sequence": self._total, "elapsed_s": round(time.monotonic()-self._started, 3),
                             "scope": scope, "kind": kind, "level": level, "attribution": attribution})

    def console(self, message):
        page = message.page
        page_scope = self._scope(page.url) if page else None
        if not page_scope:
            return
        source = message.location.get("url", "")
        source_scope = self._scope(source) if source else None
        if source and not source_scope:
            return
        self._append(source_scope or page_scope, "console",
                     message.type if message.type in LEVELS else "other",
                     "source" if source_scope else "top_level_page")

    def web_error(self, event):
        # Playwright exposes the associated Page, not the failing frame.
        # Do not attribute an iframe exception to a specific source.
        page = event.page
        scope = self._scope(page.url) if page else None
        if scope:
            self._append(scope, "uncaught_exception", "error", "top_level_page")

    def attach(self, context):
        context.on("console", self.console)
        context.on("weberror", self.web_error)

    def report(self):
        return {"schema": 1, "exported_utc": datetime.now(timezone.utc).isoformat(),
                "total": self._total, "capacity": self._events.maxlen,
                "dropped": self._total-len(self._events), "events": list(self._events),
                "scope": "Observer-owned browser context, configured loopback ports only. "
                         "Exception attribution is top-level page, not source frame. "
                         "No console text, stack traces, URLs, arguments, credentials or screenshots."}
