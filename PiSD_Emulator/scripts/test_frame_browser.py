"""Live Chromium regression against the real emulator and PiSD Flask servers."""
import os
import hashlib
import json
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
                    page = browser.new_context(viewport={"width": 1600, "height": 1000}).new_page()
                    page.goto(control)
                    # Enabled primary styling belongs to the offline runtime state.
                    # Use real outer viewport widths, without starting a session.
                    offline_captures = []
                    initial_viewport = page.viewport_size
                    for mode, bg, accent in (("light","rgb(244, 246, 250)","rgb(49, 95, 209)"),
                                             ("dark","rgb(20, 23, 28)","rgb(100, 149, 255)")):
                        page.locator("#emulatorTheme").select_option(mode)
                        expect(page.locator("#startButton")).to_be_enabled()
                        expect(page.locator("#startButton")).to_have_css("background-color", accent)
                        expect(page.locator("body")).to_have_css("background-color", bg)
                        assert page.evaluate("""async () => {
                            const faces = await Promise.all([
                                document.fonts.load('13px "PiDrive Inter"'),
                                document.fonts.load('13px "PiDrive Plex Mono"')
                            ]);
                            return faces.every(list => list.length > 0 && list.every(f => f.status === 'loaded'));
                        }""")
                        for width, height in ((390,844),(768,1024),(1440,900)):
                            page.set_viewport_size({"width":width,"height":height})
                            expect(page.locator("#startButton")).to_be_enabled()
                            expect(page.locator("#frameEmpty")).to_be_visible()
                            expect(page.locator("#pisdFrame")).to_be_hidden()
                            surface = "rgb(255, 255, 255)" if mode == "light" else "rgb(32, 37, 45)"
                            foreground = "rgb(32, 37, 45)" if mode == "light" else "rgb(237, 241, 247)"
                            expect(page.locator("#frameShell")).to_have_css("background-color", surface)
                            expect(page.locator("#frameEmpty")).to_have_css("background-color", surface)
                            expect(page.locator("#frameEmpty")).to_have_css("color", foreground)
                            self.assertFalse(runtime.status()["hardware_enabled"])
                            evidence_dir = os.environ.get("PISD_EMULATOR_EVIDENCE_DIR")
                            if evidence_dir:
                                output = Path(evidence_dir)
                                output.mkdir(parents=True, exist_ok=True)
                                path = output / f"workspace-offline-{mode}-{width}.png"
                                page.screenshot(path=str(path), full_page=True)
                                offline_captures.append({"file":path.name,"sha256":hashlib.sha256(path.read_bytes()).hexdigest(),
                                                         "theme":mode,"viewport":[width,height],"runtime":"offline"})
                    page.set_viewport_size(initial_viewport)
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
                    # Widen the real iframe without restarting or changing authorization.
                    frame.locator("#manualDriveShell").evaluate("(el) => el.dataset.cockpitContinuity = 'yes'")
                    before_width = page.locator("#pisdFrame").bounding_box()["width"]
                    before_generation = runtime.status()["generation"]
                    before_arm = frame.locator("#mdrvArm").is_checked()
                    expect(page.locator("#wideWorkspaceToggle")).to_have_text("Wide workspace")
                    assert page.locator("#wideWorkspaceToggle").evaluate("el => getComputedStyle(el,'::before').maskImage").startswith('url("data:image/svg+xml,')
                    page.locator("#wideWorkspaceToggle").click()
                    expect(page.locator("#wideWorkspaceToggle")).to_have_attribute("aria-pressed", "true")
                    eventually(lambda: page.locator("#pisdFrame").bounding_box()["width"] > before_width)
                    expect(frame.locator("#manualDriveShell")).to_have_attribute("data-cockpit-continuity", "yes")
                    self.assertEqual(runtime.status()["generation"], before_generation)
                    self.assertEqual(frame.locator("#mdrvArm").is_checked(), before_arm)
                    frame.locator("#drivingCockpitToggle").click()
                    expect(frame.locator("body")).to_have_attribute("data-pisd-cockpit", "immersive")
                    self.assertEqual(frame.locator("#mdrvArm").is_checked(), before_arm)
                    frame.locator("#mdrvLiveCamera").click()
                    expect(frame.locator("#mdrvPreview")).to_have_attribute("data-preview-mode", "live", timeout=10000)
                    def live_alignment():
                        return frame.locator("#mdrvPreviewFrame").evaluate("""el => {
                            const image=el.querySelector("img"), overlay=el.querySelector(".mdrv-drive-overlay");
                            const a=image.getBoundingClientRect(), b=overlay.getBoundingClientRect();
                            return image.naturalWidth > 0 && a.height > 0 && Math.abs(a.width/a.height-image.naturalWidth/image.naturalHeight)<.03 && ["x","y","width","height"].every(k=>Math.abs(a[k]-b[k])<=2) && getComputedStyle(image).objectFit==="contain";
                        }""")
                    eventually(live_alignment)
                    evidence_dir = os.environ.get("PISD_EMULATOR_EVIDENCE_DIR")
                    evidence = {"revision": os.environ.get("PISD_EMULATOR_EVIDENCE_REVISION"), "hardware_enabled": runtime.status()["hardware_enabled"], "generation": before_generation, "iframe_width_before": before_width, "iframe_width_wide": page.locator("#pisdFrame").bounding_box()["width"], "authorization_before": before_arm, "authorization_after_toggle": frame.locator("#mdrvArm").is_checked(), "live_alignment": live_alignment(), "captures": offline_captures}
                    def capture_evidence(name):
                        if not evidence_dir:
                            return
                        output = Path(evidence_dir)
                        output.mkdir(parents=True, exist_ok=True)
                        path = output / (name + ".png")
                        page.screenshot(path=str(path))
                        evidence["captures"].append({"file": path.name, "sha256": hashlib.sha256(path.read_bytes()).hexdigest()})
                        (output / "manifest.json").write_text(json.dumps(evidence, indent=2), encoding="utf-8")
                    evidence["geometry"] = frame.locator("#mdrvPreviewFrame").evaluate("""el => {
                        const image=el.querySelector("img"), overlay=el.querySelector(".mdrv-drive-overlay");
                        const a=image.getBoundingClientRect(), b=overlay.getBoundingClientRect();
                        return {natural:[image.naturalWidth,image.naturalHeight], image:[a.x,a.y,a.width,a.height], overlay:[b.x,b.y,b.width,b.height], fit:getComputedStyle(image).objectFit, preview_state:el.dataset.previewState};
                    }""")
                    capture_evidence("live-cockpit")
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
                    evidence["stopped_motor"] = {key: runtime.status()["engine"]["motor"][key] for key in ("left_intended","right_intended")}
                    evidence["settings_get_echoes"] = len(settings_reads) - quiet_start
                    # The outer monitor is a separate poll of virtual telemetry.
                    expect(page.locator("#leftOutput")).to_have_text("0.00", timeout=10000)
                    expect(page.locator("#rightOutput")).to_have_text("0.00", timeout=10000)
                    expect(page.locator("#leftOutput")).to_have_css("font-variant-numeric", "tabular-nums")
                    expect(page.locator("#rightOutput")).to_have_css("font-variant-numeric", "tabular-nums")
                    expect(page.locator(".motor-readout .meter-label")).to_have_count(2)
                    expect(page.locator(".camera-meta")).to_have_css("flex-wrap", "wrap")
                    expect(page.locator(".monitor-panel .state-chip")).to_have_text("VIRTUAL ONLY")
                    expect(page.get_by_role("group", name="Controller poll feedback")).to_be_visible()
                    expect(page.locator("#pollStatus")).to_have_css("font-variant-numeric", "tabular-nums")
                    evidence["controller_poll"] = page.locator("#pollStatus").inner_text()
                    evidence["monitor_readback"] = {
                        "left": page.locator("#leftOutput").inner_text(),
                        "right": page.locator("#rightOutput").inner_text(),
                        "left_wheel": page.locator("#leftWheel").inner_text(),
                        "right_wheel": page.locator("#rightWheel").inner_text(),
                    }
                    capture_evidence("after-stop")
                    # Change only the outer workspace; preserve the same live iframe,
                    # authorization and viewport. Actual font faces must load locally.
                    original_src = page.locator("#pisdFrame").get_attribute("src")
                    original_arm = frame.locator("#mdrvArm").is_checked()
                    original_width = page.locator("#pisdFrame").bounding_box()["width"]
                    for mode, bg, accent in (("light","rgb(244, 246, 250)","rgb(49, 95, 209)"),
                                             ("dark","rgb(20, 23, 28)","rgb(100, 149, 255)")):
                        page.locator("#emulatorTheme").select_option(mode)
                        expect(page.locator("body")).to_have_css("background-color", bg)
                        # Start must remain disabled while PiSD is running.
                        expect(page.locator("#startButton")).to_be_disabled()
                        expect(page.locator("#startButton")).to_have_css("background-color",
                            "rgb(255, 255, 255)" if mode == "light" else "rgb(25, 29, 36)")
                        expect(page.locator("#startButton")).to_have_css("color",
                            "rgb(86, 97, 113)" if mode == "light" else "rgb(165, 175, 191)")
                        expect(page.locator("#startButton")).to_have_css("opacity", "1")
                        assert page.evaluate("""async () => {
                            const faces = await Promise.all([
                                document.fonts.load('13px "PiDrive Inter"'),
                                document.fonts.load('13px "PiDrive Plex Mono"')
                            ]);
                            return faces.every(list => list.length > 0 && list.every(f => f.status === 'loaded'));
                        }""")
                        assert page.locator("#pisdFrame").get_attribute("src") == original_src
                        assert page.locator("#pisdFrame").bounding_box()["width"] == original_width
                        assert frame.locator("#mdrvArm").is_checked() == original_arm
                        self.assertEqual(runtime.status()["generation"], before_generation)
                        self.assertFalse(runtime.status()["hardware_enabled"])
                        expect(page.locator("#leftOutput")).to_have_text("0.00")
                        expect(page.locator("#rightOutput")).to_have_text("0.00")
                        capture_evidence("workspace-" + mode)
                    self.assertEqual(len(settings_reads), quiet_start)
                    frame.locator("#drivingCockpitToggle").click()
                    expect(frame.locator("#drivingCockpitToggle")).to_have_attribute("aria-pressed", "false")
                    page.locator("#wideWorkspaceToggle").click()
                    expect(page.locator("#wideWorkspaceToggle")).to_have_attribute("aria-pressed", "false")
                    expect(frame.locator("#manualDriveShell")).to_have_attribute("data-cockpit-continuity", "yes")
                    self.assertEqual(runtime.status()["generation"], before_generation)
                    self.assertFalse(runtime.status()["hardware_enabled"])
                    direct.close()
                    editor.close()
                    page.context.remove_listener("request", capture_settings_read)
                    for button in page.locator(".viewport[data-width]").all():
                        button.click()
                        expect(button).to_have_attribute("aria-pressed", "true")
                        expect(page.locator('.viewport[data-width][aria-pressed="true"]')).to_have_count(1)
                        expect(button).to_have_css("text-decoration-line", "underline")
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
