"""Bounded capture and real Chromium controller/PiSD lifecycle evidence."""
import json
import os
from pathlib import Path
import tempfile
import threading
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from playwright.sync_api import sync_playwright, expect
from werkzeug.serving import make_server
from test_frame_browser import ROOT, PiSDRuntime, create_control_app, free_port, eventually
from pisd_emulator.browser_observer import BrowserObserver


class ObserverTests(unittest.TestCase):
    def test_bounds_and_privacy(self):
        observer = BrowserObserver(8760, 5050, capacity=2)
        page = SimpleNamespace(url="http://127.0.0.1:8760/?secret=never-export")
        for origin in ("https://127.0.0.1:5050/", "http://127.0.0.1:5051/",
                       "http://evil.example/", "http://user@127.0.0.1:5050/"):
            observer.console(SimpleNamespace(page=page, location={"url": origin}, type="log"))
        self.assertEqual(observer.report()["total"], 0)
        for _ in range(3):
            observer.console(SimpleNamespace(page=page, location={"url": "http://127.0.0.1:5050/a?token=private"},
                                             type="warning", text="secret-value"))
        report = observer.report()
        self.assertEqual(report["total"], 3)
        self.assertEqual(report["dropped"], 1)
        self.assertEqual([e["sequence"] for e in report["events"]], [2, 3])
        self.assertTrue(all(e["scope"] == "pisd" for e in report["events"]))
        self.assertNotIn("secret-value", json.dumps(report))
        self.assertNotIn("token=private", json.dumps(report))

    def test_live_browser(self):
        evidence = Path(os.environ.get("PISD_BROWSER_OBSERVER_EVIDENCE", "emulator-browser-observer-evidence"))
        evidence.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory() as temp, patch.dict(os.environ, {"PISD_ACCESS_TOKEN": ""}):
            cp, pp = free_port(), free_port()
            while cp == pp:
                pp = free_port()
            control, pisd = f"http://127.0.0.1:{cp}", f"http://127.0.0.1:{pp}"
            runtime = PiSDRuntime(ROOT, workspace=Path(temp), port=pp, control_port=cp)
            server = make_server("127.0.0.1", cp, create_control_app(runtime), threaded=True)
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            observer = BrowserObserver(cp, pp)
            try:
                with sync_playwright() as pw:
                    browser = pw.chromium.launch()
                    try:
                        context = browser.new_context(viewport={"width": 1440, "height": 900})
                        observer.attach(context)
                        page = context.new_page()
                        page.goto(control)
                        page.locator("#pisdPort").fill(str(pp))
                        page.locator("#startButton").click()
                        frame = page.frame_locator("#pisdFrame")
                        expect(frame.locator("#manualDriveShell")).to_be_visible(timeout=20000)
                        self.assertFalse(runtime.status()["hardware_enabled"])
                        self.assertFalse(runtime.status()["gpio_access"])
                        page.wait_for_function("document.querySelector('#cameraImage').naturalWidth > 0", timeout=20000)
                        for width, height in ((1440, 900), (768, 1024), (390, 844)):
                            page.set_viewport_size({"width": width, "height": height})
                            expect(frame.locator("#manualDriveShell")).to_be_visible()
                            page.screenshot(path=str(evidence/f"workspace-{width}.png"), full_page=True)
                        direct = context.new_page()
                        direct.goto(pisd + "/manual-drive")
                        expect(direct.locator("#manualDriveShell")).to_be_visible()
                        # Deliberate fixture events, not discovered application errors.
                        page.evaluate("console.warn('fixture-private-controller')")
                        direct.evaluate("console.error('fixture-private-pisd')")
                        direct.evaluate("setTimeout(() => { throw new Error('fixture-private-exception'); }, 0)")
                        direct.wait_for_timeout(750)
                        report = observer.report()
                        self.assertTrue(any(e["scope"] == "controller" and e["level"] == "warning" for e in report["events"]))
                        self.assertTrue(any(e["scope"] == "pisd" and e["kind"] == "console" and e["level"] == "error" for e in report["events"]))
                        self.assertTrue(any(e["scope"] == "pisd" and e["kind"] == "uncaught_exception" for e in report["events"]))
                        self.assertNotIn("fixture-private", json.dumps(report))
                        direct.close()
                        page.set_viewport_size({"width": 1440, "height": 900})
                        page.locator("#restartButton").click()
                        eventually(lambda: runtime.status()["generation"] >= 2)
                        expect(frame.locator("#manualDriveShell")).to_be_visible(timeout=20000)
                        page.locator("#stopButton").click()
                        eventually(lambda: not runtime.status()["running"])
                        self.assertFalse(runtime.status()["hardware_enabled"])
                        self.assertLess(abs(runtime.status()["engine"]["motor"]["left_intended"]), .001)
                        self.assertLess(abs(runtime.status()["engine"]["motor"]["right_intended"]), .001)
                        report = observer.report()
                        report["qualification"] = {"fixture_events_injected": True, "viewport_widths": [1440, 768, 390],
                                                   "runtime_stopped": True, "physical_hardware": False}
                        (evidence/"browser-observer.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
                    finally:
                        browser.close()
            finally:
                runtime.close()
                server.shutdown()
                server.server_close()
                thread.join(timeout=5)


if __name__ == "__main__":
    unittest.main(verbosity=2)
