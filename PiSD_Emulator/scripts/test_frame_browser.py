"""Live Chromium regression against the real emulator and PiSD Flask servers."""
import os
import socket
import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path
from unittest.mock import patch

from flask import Flask
from playwright.sync_api import sync_playwright, expect
from werkzeug.serving import make_server

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / "PiSD"), str(ROOT / "PiSD_Emulator")]
from pisd.app import create_app
from pisd_emulator.runtime import PiSDRuntime
from pisd_emulator.control_app import create_control_app


def free_port():
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def eventually(check, seconds=12):
    end = time.monotonic() + seconds
    while time.monotonic() < end:
        if check():
            return
        time.sleep(.1)
    raise AssertionError("Condition not reached")


class FrameTest(unittest.TestCase):
    def test_runtime_and_real_browser(self):
        with tempfile.TemporaryDirectory() as temp, patch.dict(os.environ, {"PISD_ACCESS_TOKEN": ""}):
            control_port, pisd_port = free_port(), free_port()
            while pisd_port == control_port:
                pisd_port = free_port()
            control = f"http://127.0.0.1:{control_port}"
            pisd = f"http://127.0.0.1:{pisd_port}"
            runtime = PiSDRuntime(ROOT, workspace=Path(temp) / "emulator", port=pisd_port, control_port=control_port)
            self.addCleanup(runtime.close)
            app = create_control_app(runtime)
            client = app.test_client()
            self.assertEqual(client.get("/", base_url=control).headers["X-Frame-Options"], "DENY")
            for headers in ({"Origin": pisd}, {"Sec-Fetch-Site": "same-site"}):
                self.assertEqual(client.post("/api/runtime/start", base_url=control, json={}, headers=headers).status_code, 403)
            self.assertEqual(client.get("/api/status", base_url="http://evil.test").status_code, 403)
            self.assertFalse(runtime.status()["running"])
            with self.assertRaises(ValueError):
                create_app(emulator_frame_port=control_port)
            with self.assertRaises(ValueError):
                create_app(hardware_enabled=True, emulator=runtime, emulator_frame_port=control_port)
            normal = create_app(runtime_root=Path(temp) / "normal")
            try:
                self.assertEqual(normal.test_client().get("/manual-drive").headers["X-Frame-Options"], "DENY")
            finally:
                for name, method in (("camera", "stop"), ("motor", "close"), ("ai_drive", "close"), ("recording", "close")):
                    getattr(normal.config["pisd_services"][name], method)()
            server = make_server("127.0.0.1", control_port, app, threaded=True)
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            self.addCleanup(server.server_close)
            self.addCleanup(server.shutdown)
            with sync_playwright() as pw:
                browser = pw.chromium.launch()
                try:
                    page = browser.new_page(viewport={"width": 1600, "height": 1000})
                    page.goto(control)
                    page.locator("#pisdPort").fill(str(pisd_port))
                    page.locator("#startButton").click()
                    frame = page.frame_locator("#pisdFrame")
                    expect(frame.locator("#manualDriveShell")).to_be_visible(timeout=20000)
                    response = page.request.get(pisd + "/manual-drive")
                    self.assertEqual(response.headers["content-security-policy"], "frame-ancestors " + control)
                    self.assertNotIn("x-frame-options", response.headers)
                    self.assertEqual(page.request.post(pisd + "/api/control/manual", headers={"Origin": control}, data={"throttle": .5}).status, 403)
                    expect(page.locator("#cameraImage")).to_be_visible(timeout=15000)
                    page.wait_for_function("document.querySelector('#cameraImage').naturalWidth > 0")
                    self.assertEqual(runtime.status()["hardware_enabled"], False)
                    # Exercise the actual PiSD pages in multiple same-origin
                    # contexts, not a mocked UI or a different controller origin.
                    settings_reads = []
                    def capture_settings_read(request):
                        if request.method == "GET" and request.url.split("?", 1)[0] == pisd + "/api/settings":
                            settings_reads.append(request.url)
                    page.context.on("request", capture_settings_read)
                    direct = page.context.new_page()
                    editor = page.context.new_page()
                    direct.goto(pisd + "/manual-drive")
                    editor.goto(pisd + "/panel-presentation")
                    expect(direct.locator("#manualDriveShell")).to_be_visible()
                    expect(editor.locator("#ppFeedback")).to_have_text("Panel presentation settings ready.", timeout=15000)
                    # Explicitly settle initial presentation reads. These are
                    # not part of the quiet-window measurement.
                    for view in (direct, editor):
                        view.evaluate("() => window.PiSDPanelPresentation.loadFromBackend()")
                    page.wait_for_timeout(1000)
                    startup_reads = len(settings_reads)
                    page.wait_for_timeout(1000)
                    self.assertEqual(len(settings_reads), startup_reads, "settings echo continued after startup")
                    original_theme = editor.locator("#ppTheme").input_value()
                    original_autosave = editor.locator("#ppAutoSave").is_checked()
                    changed_theme = "light" if original_theme != "light" else "dark"
                    editor.locator("#ppAutoSave").uncheck()
                    editor.locator("#ppTheme").select_option(changed_theme)
                    editor.locator("#ppSave").click()
                    expect(editor.locator("#ppSavedState")).to_have_text("saved backend", timeout=15000)
                    expect(direct.locator("body")).to_have_attribute("data-pisd-theme", changed_theme)
                    expect(frame.locator("body")).to_have_attribute("data-pisd-theme", changed_theme)
                    self.assertEqual(editor.request.get(pisd + "/api/settings").json()["settings"]["panel_presentation"]["theme"], changed_theme)
                    # Simulate a runtime-cache notification with no presentation
                    # change. The stored timestamp must not bounce between tabs.
                    direct.evaluate("""() => {
                        const key = 'pisd.runtimeSettings.v2';
                        const data = JSON.parse(localStorage.getItem(key));
                        data.saved_at = 'settings-flood-regression';
                        localStorage.setItem(key, JSON.stringify(data));
                    }""")
                    page.wait_for_timeout(1000)
                    self.assertEqual(direct.evaluate("() => JSON.parse(localStorage.getItem('pisd.runtimeSettings.v2')).saved_at"), "settings-flood-regression")
                    self.assertEqual(len(settings_reads), startup_reads, "save or unrelated storage notification echoed a GET")
                    # Restore the original presentation through the actual
                    # save control; leave all other fixture settings intact.
                    editor.locator("#ppTheme").select_option(original_theme)
                    editor.locator("#ppAutoSave").evaluate("(el, checked) => { el.checked = checked; }", original_autosave)
                    editor.locator("#ppSave").click()
                    expect(editor.locator("#ppSavedState")).to_have_text("saved backend", timeout=15000)
                    expect(direct.locator("body")).to_have_attribute("data-pisd-theme", original_theme)
                    self.assertEqual(editor.request.get(pisd + "/api/settings").json()["settings"]["panel_presentation"]["theme"], original_theme)
                    page.bring_to_front()
                    page.wait_for_timeout(1000)
                    self.assertEqual(len(settings_reads), startup_reads, "restoring settings echoed a GET")
                    quiet_start = len(settings_reads)
                    page.wait_for_timeout(60000)
                    self.assertEqual(len(settings_reads), quiet_start, "autonomous settings GET during 60-second quiet window")
                    frame.locator("#mdrvLiveCamera").click()
                    expect(frame.locator("#mdrvPreview")).to_have_attribute("data-preview-mode", "live", timeout=10000)
                    frame.locator("#mdrvArm").check()
                    frame.locator("#mdrvDragPad").focus()
                    page.keyboard.press("ArrowUp")
                    page.keyboard.press("ArrowUp")
                    eventually(lambda: abs(runtime.status()["engine"]["motor"]["left_intended"]) > .01)
                    eventually(lambda: abs(runtime.status()["engine"]["vehicle"]["y_m"]) > .01)
                    frame.locator("#mdrvStopTop").click()
                    eventually(lambda: abs(runtime.status()["engine"]["motor"]["left_intended"]) < .001 and abs(runtime.status()["engine"]["motor"]["right_intended"]) < .001)
                    # Keep both additional tabs open through real manual drive
                    # and STOP. No late nonzero virtual motor command may
                    # appear after STOP, even beyond the lease expiry.
                    page.wait_for_timeout(1000)
                    self.assertLess(abs(runtime.status()["engine"]["motor"]["left_intended"]), .001)
                    self.assertLess(abs(runtime.status()["engine"]["motor"]["right_intended"]), .001)
                    self.assertEqual(len(settings_reads), quiet_start, "manual drive or STOP echoed a settings GET")
                    print(f"Settings synchronization: {startup_reads} startup/explicit browser GETs; zero quiet/save/drive/STOP GET echoes", flush=True)
                    direct.close()
                    editor.close()
                    page.context.remove_listener("request", capture_settings_read)
                    for button in page.locator(".viewport").all():
                        button.click()
                        expect(frame.locator("#manualDriveShell")).to_be_visible()
                    frame.locator("#manualDriveShell").evaluate("(el) => el.dataset.beforeRestart = 'yes'")
                    generation = runtime.status()["generation"]
                    page.locator("#restartButton").click()
                    eventually(lambda: runtime.status()["generation"] > generation)
                    expect(frame.locator("#manualDriveShell")).to_be_visible(timeout=20000)
                    expect(frame.locator("#manualDriveShell")).not_to_have_attribute("data-before-restart", "yes", timeout=20000)
                    # Different local origin must not gain framing authority.
                    other = Flask("untrusted")
                    @other.get("/")
                    def index():
                        return f'<iframe src="{pisd}/manual-drive"></iframe>'
                    alien = make_server("127.0.0.1", 0, other, threaded=True)
                    threading.Thread(target=alien.serve_forever, daemon=True).start()
                    try:
                        hostile = browser.new_page()
                        with hostile.expect_event("console", predicate=lambda msg: "frame-ancestors" in msg.text.lower(), timeout=15000):
                            hostile.goto(f"http://127.0.0.1:{alien.server_port}/")
                        expect(hostile.frame_locator("iframe").locator("#manualDriveShell")).to_have_count(0, timeout=5000)
                        hostile.close()
                    finally:
                        alien.shutdown()
                        alien.server_close()
                finally:
                    browser.close()
            runtime.close()


if __name__ == "__main__":
    unittest.main(verbosity=2)
