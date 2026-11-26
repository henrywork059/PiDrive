"""Real Chromium, actual Flask templates and read-only simulation fixtures.

All network requests are intercepted. No mutation reaches any backend.
Only run with synthetic, disposable settings; no external browser origin.
"""
import argparse
import json
import os
import re
import sys
import tempfile
from contextlib import ExitStack
from pathlib import Path
from unittest.mock import patch
from urllib.parse import urlsplit

from playwright.sync_api import sync_playwright, expect

WIDTHS = (390, 768, 1024, 1440)
HEIGHTS = (844, 1024, 768, 900)
ORIGIN = "http://127.0.0.1:8765"
PAGES = {
    "PiSD": [
        ("front", "/", "#fpStopAll", "#frontModeManualDrive", None, None),
        ("manual", "/manual-drive", "#mdrvStopTop", "#mdrvDragPad", "#mdrvPreviewFrame", "#mdrvOverlaySettingsOpen"),
        ("ai", "/ai-mode", "#aiStopAll", "#aiSaveConfig", "#aiPreviewFrame", "#aiWorkflowSettingsOpen"),
        ("settings", "/settings", "#stStopAll", "#stSaveSettings", None, None),
        ("testing", "/testing", "#stopAllBtn", "#customSendBtn", None, None),
        ("panel_lab", "/panel-testing", "#ptStopAll", "#ptRunAllChecks", None, None),
        ("motor_tuning", "/motor-tuning", None, ".mtun-back", None, None),
        ("presentation", "/panel-presentation", None, "#ppApply", None, None),
    ],
    "PiServer": [
        ("dashboard", "/", "#estopToggle", "#saveRuntimeBtn", ".viewer-frame", "#openStyleSettingsBtn"),
    ],
}


def fixture(component, temp, stack):
    stack.enter_context(patch.dict(os.environ, {"PISD_ACCESS_TOKEN": "", "PISERVER_ACCESS_TOKEN": "", "PISERVER_HOST": "127.0.0.1"}))
    if component == "PiSD":
        from pisd import app as module
        stack.enter_context(patch.object(module, "PROJECT_ROOT", temp))
        stack.enter_context(patch.object(module, "RUNTIME_SETTINGS_PATH", temp / "runtime.json"))
        # Non-default synthetic settings expose partial/aborted page startup.
        (temp / "runtime.json").write_text(json.dumps({"manual_drive": {
            "speed": 0.43, "max_speed_limit": 0.63,
            "overlay": {"path_length_scale": 1.35},
        }}), encoding="utf-8")
        app = module.create_app(hardware_enabled=False)
        s = app.config["pisd_services"]
        stack.callback(s["camera"].stop)
        stack.callback(s["motor"].close)
        stack.callback(s["ai_drive"].close)
    else:
        from piserver import app as module
        from piserver.services import motor_service, camera_service
        if motor_service.GPIO_AVAILABLE or camera_service.Picamera2 is not None:
            raise RuntimeError("Browser fixture refuses a hardware-capable PiServer environment")
        stack.enter_context(patch.object(module, "BASE_DIR", temp))
        # Never open a physical USB camera or start control loop in this fixture.
        stack.enter_context(patch.object(module.CameraService, "start", lambda self: None))
        stack.enter_context(patch.object(module.ControlService, "start", lambda self: None))
        app = module.create_app()
        s = app.config["services"]
        stack.callback(s["camera"].stop)
        stack.callback(s["motor"].close)
    return app.test_client()


def check_geometry(locator, width, height, label):
    expect(locator).to_be_visible(timeout=8000)
    locator.scroll_into_view_if_needed(timeout=8000)
    r = locator.bounding_box()
    assert r is not None and r["width"] > 0 and r["height"] > 0, label
    assert r["x"] >= -3 and r["x"] + r["width"] <= width + 3, (label, r, width)
    assert r["y"] < height and r["y"] + r["height"] > 0, (label, r, height)
    return {k: round(v, 1) for k, v in r.items()}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("component", choices=PAGES)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--revision", required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    cases = []
    with tempfile.TemporaryDirectory() as tmp, ExitStack() as stack:
        client = fixture(args.component, Path(tmp), stack)
        with sync_playwright() as pw:
            browser = pw.chromium.launch()
            for name, url, stop, primary, preview, opener in PAGES[args.component]:
                for width, height in zip(WIDTHS, HEIGHTS):
                    context = browser.new_context(viewport={"width": width, "height": height},
                        reduced_motion="reduce", has_touch=width == 390, device_scale_factor=1,
                        service_workers="block")
                    if name in ("front", "dashboard"):
                        context.add_init_script("Object.defineProperty(navigator, 'clipboard', {configurable:true,value:{writeText:async text=>{window.__copiedEvents=text;}}})")
                    page = context.new_page()
                    mutations = []
                    errors = []
                    # UX75: the real dashboard must start and recover while
                    # its initial read-only APIs are temporarily unavailable.
                    # This is synthetic and never reaches a physical device.
                    bootstrap_offline = [name == "dashboard"]
                    stalled_initial_model = [name == "dashboard"]
                    stalled_status = [False]
                    hold_status = [False]
                    held_status = []
                    acknowledge_stop = [False]
                    model_reply = [None]
                    model_workspace = [False]
                    camera_workspace = [False]
                    synthetic_recording = [None]
                    reject_folder_read = [False]
                    folder_workspace = [False]
                    folder_reply = [None]
                    folder_downloads = []
                    hold_folder = [False]
                    held_folders = []
                    acknowledge_folder_delete = [False]
                    stall_settings = [name == "settings"]
                    reject_settings_read = [False]
                    hold_settings = [False]
                    held_settings = []
                    pisd_folders = [None]
                    stall_pisd_folders = [False]
                    def route_request(route):
                        req = route.request
                        parsed = urlsplit(req.url)
                        if f"{parsed.scheme}://{parsed.netloc}" != ORIGIN:
                            route.abort()
                            return
                        if req.method != "GET":
                            mutations.append(parsed.path)
                            if acknowledge_folder_delete[0] and parsed.path == "/api/record/delete":
                                assert req.post_data_json == {"session": "fixture-b", "confirm": True}
                                snapshot = dict(client.get("/api/status", base_url=ORIGIN).get_json(), current_page="training")
                                route.fulfill(status=200, json={"ok": True, "message": "Deleted fixture-b.",
                                                               "sessions": folder_reply[0]["sessions"], "state": snapshot})
                                return
                            if synthetic_recording[0] is not None and parsed.path in {"/api/record/toggle", "/api/record/capture_once"}:
                                if parsed.path == "/api/record/toggle":
                                    synthetic_recording[0] = not synthetic_recording[0]
                                snapshot = dict(client.get("/api/status", base_url=ORIGIN).get_json(),
                                                recording=synthetic_recording[0])
                                route.fulfill(status=200, json={"ok": True, "recording": synthetic_recording[0],
                                                               "message": "Synthetic recording acknowledgement", "state": snapshot})
                                return
                            if acknowledge_stop[0] and parsed.path == "/api/system/estop":
                                assert req.post_data_json == {"enabled": True}
                                assert len(held_status) == 1
                                snapshot = dict(held_status[0][1], safety_stop=True,
                                                system_message="Synthetic STOP acknowledgement",
                                                applied_steering=0, applied_throttle=0,
                                                motor_left=0, motor_right=0)
                                # Synthetic success only; no backend mutation.
                                route.fulfill(status=200, json={"ok": True, "state": snapshot})
                                return
                            route.fulfill(status=503, content_type="application/json",
                                          body='{"ok":false,"message":"Synthetic rejected mutation"}')
                            return
                        if name in ("manual", "ai") and parsed.path == "/api/recording/items":
                            if stall_pisd_folders[0]:
                                stall_pisd_folders[0] = False
                                return
                            if pisd_folders[0] is not None:
                                status, payload = pisd_folders[0]
                                route.fulfill(status=status, json=payload)
                                return
                        if name == "settings" and parsed.path == "/api/settings":
                            if stall_settings[0]:
                                stall_settings[0] = False
                                return
                            if reject_settings_read[0]:
                                route.fulfill(status=503, json={"ok": False, "message": "Synthetic settings read rejection"})
                                return
                            if hold_settings[0]:
                                hold_settings[0] = False
                                held_settings.append((route, client.get("/api/settings", base_url=ORIGIN).get_json()))
                                return
                        if name in ("front", "dashboard") and parsed.path == "/api/recent-events":
                            route.fulfill(status=200, json={"ok": True, "capacity": 128, "events": [
                                {"timestamp_utc": "2026-01-01T00:00:00Z", "title": "Motor STOP requested", "outcome": "acknowledged"}
                            ]})
                            return
                        if parsed.path in {"/video_feed", "/api/camera/frame.jpg"}:
                            route.fulfill(status=204, body="")
                            return
                        if stalled_initial_model[0] and parsed.path == "/api/model/list":
                            # Leave the real browser GET pending until its own
                            # AbortController cancels it; this isn't an HTTP 503.
                            stalled_initial_model[0] = False
                            return
                        if stalled_status[0] and parsed.path == "/api/status":
                            return
                        if hold_status[0] and parsed.path == "/api/status":
                            hold_status[0] = False
                            snapshot = client.get("/api/status", base_url=ORIGIN).get_json()
                            held_status.append((route, snapshot))
                            return
                        if bootstrap_offline[0] and parsed.path in {
                            "/api/status", "/api/model/list", "/api/record/sessions",
                            "/api/camera/config", "/api/motor/config",
                        }:
                            route.fulfill(status=503, content_type="application/json",
                                          body='{"ok":false,"message":"Synthetic disconnected backend"}')
                            return
                        if folder_workspace[0] and parsed.path == "/api/record/download":
                            # Synthetic empty ZIP: never read or download a real recording.
                            folder_downloads.append(parsed.query)
                            route.fulfill(status=200, content_type="application/zip",
                                          headers={"Content-Disposition": 'attachment; filename="fixture-b.zip"'},
                                          body=bytes.fromhex("504b0506" + "00" * 18))
                            return
                        if hold_folder[0] and parsed.path == "/api/record/sessions":
                            hold_folder[0] = False
                            held_folders.append((route, folder_reply[0]))
                            return
                        if folder_reply[0] is not None and parsed.path == "/api/record/sessions":
                            route.fulfill(status=200, json=folder_reply[0])
                            return
                        if folder_workspace[0] and parsed.path == "/api/status":
                            snapshot = client.get("/api/status", base_url=ORIGIN).get_json()
                            route.fulfill(status=200, json=dict(snapshot, current_page="training"))
                            return
                        if reject_folder_read[0] and parsed.path == "/api/record/sessions":
                            route.fulfill(status=503, json={"ok": False, "message": "Synthetic folder refresh failure"})
                            return
                        if synthetic_recording[0] is not None and parsed.path == "/api/status":
                            snapshot = client.get("/api/status", base_url=ORIGIN).get_json()
                            route.fulfill(status=200, json=dict(snapshot, recording=synthetic_recording[0]))
                            return
                        if parsed.path == "/api/model/list" and model_reply[0] is not None:
                            status, payload = model_reply[0]
                            route.fulfill(status=status, json=payload)
                            return
                        if (model_workspace[0] or camera_workspace[0]) and parsed.path == "/api/status":
                            snapshot = client.get("/api/status", base_url=ORIGIN).get_json()
                            route.fulfill(status=200, json=dict(snapshot, current_page="camera" if camera_workspace[0] else "auto"))
                            return
                        result = client.get(parsed.path + ("?" + parsed.query if parsed.query else ""),
                                            base_url=ORIGIN)
                        route.fulfill(status=result.status_code, content_type=result.content_type,
                                      body=result.get_data())
                    context.route("**/*", route_request)
                    page.on("pageerror", lambda error: errors.append(str(error)))
                    case = {"page": name, "width": width, "height": height, "geometry": {}, "errors": []}
                    try:
                        page.goto(ORIGIN + url, wait_until="domcontentloaded")
                        if stop:
                            expect(page.locator(stop)).to_be_visible(timeout=8000)
                        if name == "manual":
                            expect(page.locator("#mdrvSpeed")).to_have_value("0.43", timeout=8000)
                            expect(page.locator("#mdrvSpeed")).to_have_attribute("max", "0.63")
                            assert page.locator("#mdrvOverlayLengthScale").evaluate("(el) => Number(el.value)") == 1.35
                        page.screenshot(path=str(args.output / f"{name}-{width}.png"), full_page=True, animations="disabled")
                        for label, selector in (("stop", stop), ("primary", primary), ("preview", preview)):
                            if selector:
                                case["geometry"][label] = check_geometry(page.locator(selector).first, width, height, label)
                        # Empty libraries are genuine fixture GET results, not hard-coded HTML.
                        if name in ("manual", "ai"):
                            prefix = "mdrv" if name == "manual" else "ai"
                            expect(page.locator(f"#{prefix}FileSummary")).to_have_attribute("data-state", "empty")
                            expect(page.locator(f"#{prefix}DownloadZip")).to_be_disabled()
                            expect(page.locator(f"#{prefix}DeleteFolder")).to_be_disabled()
                            # Real page controls: recover populated library, retain selected
                            # identity on failure, and disable actions until readback.
                            folder = page.locator(f"#{prefix}FileSelect")
                            notice = page.locator(f"#{prefix}FilesNotice")
                            refresh = page.locator(f"#{prefix}RefreshFiles")
                            delete = page.locator(f"#{prefix}DeleteFolder")
                            download = page.locator(f"#{prefix}DownloadZip")
                            # Require visible real controls, never a hidden-handler click.
                            def activate_library(control):
                                expect(control).to_be_visible()
                                expect(control).to_be_enabled()
                                if width == 390:
                                    control.tap()
                                else:
                                    control.focus()
                                    expect(control).to_be_focused()
                                    control.press("Space")
                            def refresh_folders():
                                activate_library(refresh)
                            valid = {"ok": True, "code": "PISD-OK-000", "collections": {
                                "recordings": [{"id": "fixture/a", "label": "A", "frame_count": 3},
                                               {"id": "fixture/b", "label": "B", "frame_count": 4}], "snapshots": []}}
                            pisd_folders[0] = (200, valid)
                            refresh_folders()
                            expect(folder).to_have_value("fixture/a")
                            expect(delete).to_be_enabled()
                            if name == "ai":
                                kind = page.locator("#aiFileKind")
                                expect(kind).to_have_accessible_name("Recording library type")
                                expect(folder).to_have_accessible_name("Recording library folder")
                                kind.focus()
                                page.keyboard.press("Tab")
                                expect(folder).to_be_focused()
                                before = list(mutations)
                                if width == 390:
                                    # Native OS select popups are not touch-automatable here.
                                    folder.tap()
                                    folder.press("Escape")
                                    folder.select_option("fixture/b")
                                else:
                                    page.keyboard.press("ArrowDown")
                                expect(folder).to_have_value("fixture/b")
                                expect(notice).to_contain_text("fixture/b")
                                assert mutations == before, "Selecting a folder invoked a mutation"
                                page.keyboard.press("Tab")
                                expect(refresh).to_be_focused()
                                page.keyboard.press("Tab")
                                expect(download).to_be_focused()
                                page.keyboard.press("Tab")
                                expect(delete).to_be_focused()
                                activate_library(delete)
                                confirm_group = page.get_by_role("group", name="Confirm destructive action")
                                expect(confirm_group).to_contain_text("fixture/b")
                                cancel = confirm_group.get_by_role("button", name="Cancel")
                                expect(cancel).to_be_focused()
                                expect(page.locator("#aiStopAll")).to_be_enabled()
                                activate_library(cancel)
                                expect(confirm_group).to_have_count(0)
                                expect(delete).to_be_focused()
                                assert mutations == before, "Cancel invoked a mutation"
                            else:
                                folder.select_option("fixture/b")
                            stall_pisd_folders[0] = True
                            refresh_folders()
                            expect(delete).to_be_disabled()
                            expect(download).to_be_disabled()
                            expect(notice).to_contain_text("timed out", timeout=8000)
                            expect(folder).to_have_value("fixture/b")
                            expect(page.locator(f"#{prefix}FileSummary")).to_have_attribute("data-state", "unverified")
                            pisd_folders[0] = (503, {"ok": False, "message": "Synthetic folder failure"})
                            refresh_folders()
                            expect(notice).to_contain_text("Synthetic folder failure")
                            expect(delete).to_be_disabled()
                            pisd_folders[0] = (200, valid)
                            refresh_folders()
                            expect(folder).to_have_value("fixture/b")
                            expect(delete).to_be_enabled()
                            # Restore a fresh empty collection for subsequent checks.
                            pisd_folders[0] = (200, {"ok": True, "collections": {"recordings": [], "snapshots": []}})
                            refresh_folders()
                            expect(folder).to_have_value("")
                            expect(delete).to_be_disabled()
                            expect(download).to_be_disabled()
                        if name == "ai":
                            expect(page.locator("#aiModelSelect")).to_have_value("")
                            expect(page.locator("#aiModelSelect option")).to_contain_text("No models")
                        if name == "dashboard":
                            # All four viewport widths exercise a cold disconnected
                            # startup and a confirmed recovery using real page code.
                            expect(page.locator("#maintenanceBadge")).to_have_text("offline")
                            expect(page.locator("#metricDriveState")).to_have_text("Unverified")
                            expect(page.locator("#estopToggle")).to_have_attribute("aria-pressed", "mixed")
                            expect(page.locator("#statusBanner")).to_contain_text("unverified")
                            assert page.locator("#statusBanner").get_attribute("role") == "status"
                            # Clicking emergency STOP while status is unknown must
                            # never submit rearm {enabled:false}, even if a previous
                            # status sample had indicated an engaged E-STOP.
                            with page.expect_request(lambda req: req.method == "POST"
                                    and urlsplit(req.url).path == "/api/system/estop") as stop_request:
                                page.locator(stop).click()
                            assert stop_request.value.post_data_json == {"enabled": True}, (
                                "unverified E-STOP must only request engagement"
                            )
                            bootstrap_offline[0] = False
                            page.evaluate("""async () => {
                                await refreshModels();
                                await refreshSessions(false);
                                await loadCameraConfig();
                                await loadMotorConfig();
                                await pollStatus();
                            }""")
                            expect(page.locator("#maintenanceBadge")).not_to_have_text("offline")
                            expect(page.locator("#metricDriveState")).not_to_have_text("Unverified")
                            assert page.locator("#estopToggle").get_attribute("aria-pressed") in ("true", "false")
                            # UX75: a pending status GET must time out and free the
                            # single-flight guard; it must not leave stale motor
                            # telemetry looking verified or permit an unverified
                            # rearm. The route deliberately never fulfills.
                            page.evaluate("""() => {
                                if (state.statusTimer) clearTimeout(state.statusTimer);
                                state.statusTimer = null;
                            }""")
                            stalled_status[0] = True
                            page.evaluate("() => pollStatus()")
                            expect(page.locator("#maintenanceBadge")).to_have_text("offline")
                            expect(page.locator("#metricDriveState")).to_have_text("Unverified")
                            expect(page.locator("#estopToggle")).to_have_attribute("aria-pressed", "mixed")
                            expect(page.locator("#statusBanner")).to_contain_text("timed out")
                            assert page.evaluate("() => !state.statusInFlight && state.statusTimer !== null"), (
                                "timeout must release single-flight guard and schedule retry"
                            )
                            with page.expect_request(lambda req: req.method == "POST"
                                    and urlsplit(req.url).path == "/api/system/estop") as timed_out_stop:
                                page.locator(stop).click()
                            assert timed_out_stop.value.post_data_json == {"enabled": True}, (
                                "stalled status must never trigger an unverified rearm"
                            )
                            stalled_status[0] = False
                            page.evaluate("() => pollStatus()")
                            expect(page.locator("#maintenanceBadge")).not_to_have_text("offline")
                            expect(page.locator("#metricDriveState")).not_to_have_text("Unverified")
                            # UX75: deliver a pre-STOP status sample AFTER a newer
                            # synthetic STOP acknowledgement. The old sample must
                            # not overwrite the confirmed stop or telemetry.
                            page.wait_for_function("() => !state.statusInFlight")
                            expect(page.locator(stop)).to_have_attribute("aria-pressed", "false")
                            hold_status[0] = True
                            with page.expect_request(lambda req: req.method == "GET"
                                    and urlsplit(req.url).path == "/api/status"):
                                page.evaluate("""() => {
                                    if (state.statusTimer) clearTimeout(state.statusTimer);
                                    state.statusTimer = null;
                                    void pollStatus();
                                }""")
                            acknowledge_stop[0] = True
                            page.locator(stop).click()
                            expect(page.locator(stop)).to_have_attribute("aria-pressed", "true")
                            expect(page.locator("#metricDriveState")).to_have_text("E-stop active")
                            acknowledge_stop[0] = False
                            assert len(held_status) == 1
                            old_route, old_snapshot = held_status.pop()
                            assert old_snapshot["safety_stop"] is False
                            old_route.fulfill(status=200, json=old_snapshot)
                            page.wait_for_function("() => !state.statusInFlight")
                            expect(page.locator(stop)).to_have_attribute("aria-pressed", "true")
                            expect(page.locator("#metricDriveState")).to_have_text("E-stop active")
                            assert page.evaluate("() => state.statusTimer !== null")
                            # The next new status request remains authoritative.
                            # Fixture backend was never stopped; it still reports OFF.
                            page.evaluate("() => pollStatus()")
                            expect(page.locator(stop)).to_have_attribute("aria-pressed", "false")
                            # R36: even when the dock is short/narrow, metric rows must
                            # contain their labels and values rather than clipping them.
                            metrics = page.locator(".dock-panel[data-panel='status'] .status-metric-grid > .metric-card")
                            assert metrics.count() >= 8, "Status dock lost its metrics"
                            for index in range(metrics.count()):
                                card = metrics.nth(index)
                                size = card.evaluate("(el) => ({content: el.scrollHeight, box: el.clientHeight})")
                                assert size["content"] <= size["box"] + 2, (
                                    "Status value clipped", index, size, width
                                )
                            expect(page.locator("#modelSelect option")).to_contain_text("No .tflite models")
                            # PiServer deliberately creates a snapshots directory even
                            # before the first capture. Empty data means zero images,
                            # not zero folders; preserve its actual storage contract.
                            expect(page.locator("#sessionSelect option")).to_have_count(1)
                            expect(page.locator("#sessionSelect")).to_have_value("snapshots")
                            expect(page.locator("#sessionSelect option")).to_contain_text("snapshot folder")
                            expect(page.locator("#sessionImageCount")).to_have_text("0")
                            # Real Refresh control: failed read, retry, retain user's
                            # selection even when server reports another active model.
                            model_workspace[0] = True
                            page.locator('.tab-btn[data-page="auto"]').click()
                            active_page = page.locator('#pageTabs [data-page="auto"]')
                            inactive_page = page.locator('#pageTabs [data-page="manual"]')
                            expect(active_page).to_have_attribute("aria-pressed", "true")
                            for colors in ("none", "active"):
                                page.emulate_media(forced_colors=colors)
                                expect(active_page).to_have_css("text-decoration-line", "underline")
                                expect(inactive_page).to_have_css("text-decoration-line", "none")
                                active_page.focus()
                                page.keyboard.press("Tab")
                                page.keyboard.press("Shift+Tab")
                                expect(active_page).to_be_focused()
                                expect(active_page).to_have_css("outline-style", "solid")
                            page.emulate_media(forced_colors="none")
                            # Exercise decorative flash CSS without requesting a snapshot.
                            assert page.locator("#snapshotFlash").evaluate("""node => {
                                const wasActive = node.classList.contains('active');
                                node.classList.add('active');
                                const hidden = getComputedStyle(node).animationName === 'none' &&
                                               getComputedStyle(node).opacity === '0';
                                node.classList.toggle('active', wasActive);
                                return hidden;
                            }"""), "Reduced motion must suppress decorative flash"
                            refresh = page.locator("#refreshModelsBtn")
                            select = page.locator("#modelSelect")
                            message = page.locator("#modelMessage")
                            load_model = page.locator("#loadModelBtn")
                            delete_model = page.locator("#deleteModelBtn")
                            def activate_safe(control):
                                expect(control).to_be_visible()
                                expect(control).to_be_enabled()
                                if width == 390:
                                    control.tap()
                                else:
                                    control.focus()
                                    control.press("Enter")
                            expect(page.locator("#modelFile")).to_have_accessible_name("Upload model")
                            expect(page.locator("#modelManifestFile")).to_have_accessible_name("Optional matching .manifest.json")
                            expect(page.locator("#uploadModelBtn")).to_have_accessible_name("Upload model")
                            expect(refresh).to_have_accessible_name("Refresh models")
                            expect(select).to_have_accessible_name("Models")
                            expect(load_model).to_have_accessible_name("Load selected model")
                            expect(delete_model).to_have_accessible_name("Delete selected model")
                            model_reply[0] = (200, {"models": ["a.tflite", "b.tflite"], "active": "a.tflite"})
                            activate_safe(refresh)
                            expect(message).to_have_text("Model list refreshed.")
                            model_before = list(mutations)
                            refresh.focus()
                            page.keyboard.press("Tab")
                            expect(select).to_be_focused()
                            expect(select).to_have_css("outline-style", "solid")
                            select.press("End")
                            expect(select).to_have_value("b.tflite")
                            page.keyboard.press("Tab")
                            expect(load_model).to_be_focused()
                            page.keyboard.press("Tab")
                            expect(delete_model, "Native Tab reaches Delete selected model").to_be_focused()
                            delete_model.press("Enter")
                            confirm_model = page.get_by_role("group", name="Confirm destructive action")
                            expect(confirm_model).to_contain_text("b.tflite")
                            cancel_model = confirm_model.get_by_role("button", name="Cancel")
                            expect(cancel_model).to_be_focused()
                            cancel_model.press("Escape")
                            expect(confirm_model).to_have_count(0)
                            expect(delete_model, "Escape cancellation restores Delete focus").to_be_focused()
                            expect(page.locator("#styleSettingsModal")).to_be_hidden()
                            delete_model.press("Escape")
                            expect(delete_model, "Unclaimed Escape outside closed style dialog preserves focus").to_be_focused()
                            if width == 390:
                                delete_model.tap()
                                expect(confirm_model).to_contain_text("b.tflite")
                                cancel_model.tap()
                                expect(confirm_model).to_have_count(0)
                                expect(delete_model, "Touch cancellation restores Delete focus").to_be_focused()
                            expect(select).to_have_value("b.tflite")
                            assert mutations == model_before, "Model selection/cancel invoked mutation"
                            model_reply[0] = (503, {"ok": False, "message": "Synthetic model list failure"})
                            activate_safe(refresh)
                            expect(message).to_contain_text("Cannot refresh models")
                            expect(select).to_have_value("b.tflite")
                            expect(refresh).to_be_enabled()
                            model_reply[0] = (200, {"models": ["a.tflite", "b.tflite"], "active": "a.tflite"})
                            activate_safe(refresh)
                            expect(message).to_have_text("Model list refreshed.")
                            expect(select).to_have_value("b.tflite")
                            assert message.get_attribute("role") == "status"
                            model_reply[0] = (200, {"models": ["a.tflite"], "active": "a.tflite"})
                            activate_safe(refresh)
                            expect(select).to_have_value("a.tflite")
                            model_reply[0] = None
                            activate_safe(refresh)
                            expect(select.locator("option")).to_contain_text("No .tflite models")
                            assert mutations == model_before, "Model refresh invoked mutation"
                            model_workspace[0] = False
                            camera_workspace[0] = True
                            # Existing navigation sends an intercepted control update; only
                            # the subsequent draft-only camera interactions must be read-only.
                            with page.expect_response(lambda response: response.request.method == "GET"
                                    and urlsplit(response.url).path == "/api/camera/config"):
                                activate_safe(page.locator('.tab-btn[data-page="camera"]'))
                            expect(page.locator("body")).to_have_attribute("data-page", "camera")
                            expect(page.locator("#cameraMessage")).to_contain_text("Stream")
                            # Await the readback explicitly before editing the draft.
                            page.evaluate("() => loadCameraConfig()")
                            preset = page.locator("#cameraResolutionPreset")
                            camera_width = page.locator("#cameraWidth")
                            camera_height = page.locator("#cameraHeight")
                            quality = page.locator("#cameraStreamQuality")
                            awb = page.locator("#cameraAwb")
                            apply_camera = page.locator("#cameraApplyBtn")
                            retry_camera = page.locator("#cameraRetryApply")
                            camera_phase = page.locator("#cameraApplyState")
                            camera_detail = page.locator("#cameraApplyDetail")
                            for control, label in ((preset, "Preset resolution"), (camera_width, "Width"),
                                    (camera_height, "Height"), (quality, "Stream quality"),
                                    (page.locator("#cameraAutoExposure"), "Auto exposure"),
                                    (awb, "Auto white balance"), (apply_camera, "Apply + restart camera")):
                                expect(control).to_have_accessible_name(label)
                            camera_before = list(mutations)
                            preset.focus()
                            preset.press("End")
                            expect(preset).to_have_value("1280x720")
                            expect(camera_width).to_have_value("1280")
                            expect(camera_height).to_have_value("720")
                            page.keyboard.press("Tab")
                            expect(camera_width).to_be_focused()
                            expect(camera_width).to_have_css("outline-style", "solid")
                            camera_width.press("ArrowUp")
                            expect(camera_width).to_have_value("1281")
                            page.keyboard.press("Tab")
                            expect(camera_height).to_be_focused()
                            expect(preset).to_have_value("custom")
                            quality.focus()
                            quality.press("Home")
                            expect(quality).to_have_value("low_latency")
                            expect(page.locator("#cameraPreviewFps")).to_have_value("10")
                            expect(page.locator("#cameraPreviewQuality")).to_have_value("40")
                            awb_before = awb.is_checked()
                            awb.focus()
                            awb.press("Space")
                            assert awb.is_checked() != awb_before
                            if width == 390:
                                awb.tap()
                                assert awb.is_checked() == awb_before
                            expect(camera_phase).to_have_text("Unsaved")
                            expect(camera_detail).to_contain_text("not yet confirmed")
                            expect(apply_camera).to_have_accessible_description("Changes are not yet confirmed.")
                            assert mutations == camera_before, "Camera draft invoked mutation"
                            # Explicit Apply and Retry are synthetic rejected requests, never
                            # forwarded to the camera service or hardware.
                            for control in (apply_camera, retry_camera):
                                with page.expect_response(lambda response: response.request.method == "POST"
                                        and urlsplit(response.url).path == "/api/camera/apply"):
                                    activate_safe(control)
                                expect(camera_phase).to_have_text("Failed")
                                expect(camera_detail).to_contain_text("Synthetic rejected mutation")
                                expect(retry_camera).to_have_accessible_name("Retry apply camera settings")
                                expect(retry_camera).to_have_accessible_description("Synthetic rejected mutation")
                                expect(page.locator(stop)).to_be_enabled()
                            assert mutations[len(camera_before):] == ["/api/camera/apply", "/api/camera/apply"], mutations
                            camera_workspace[0] = False
                            page.locator('.tab-btn[data-page="manual"]').click()
                            # Confirmed recording commands must not be reversed by
                            # a later failed read of the saved-folder list.
                            synthetic_recording[0] = False
                            reject_folder_read[0] = True
                            record = page.locator("#recordToggleBtn")
                            for expected in ("true", "false"):
                                record.click()
                                expect(page.locator("#statusBanner")).to_contain_text("Recording command acknowledged; folder refresh failed")
                                expect(record).to_have_attribute("aria-pressed", expected)
                                expect(record).to_be_enabled()
                                expect(page.locator("#sessionExportMessage")).to_contain_text("Cannot refresh folders")
                            page.locator("#captureOnceBtn").click()
                            expect(page.locator("#statusBanner")).to_contain_text("Snapshot saved; folder refresh failed")
                            expect(page.locator("#captureOnceBtn")).to_be_enabled()
                            synthetic_recording[0] = None
                            reject_folder_read[0] = False
                            # Rejected mutation still reports failure and restores OFF.
                            record.click()
                            expect(page.locator("#statusBanner")).to_contain_text("Synthetic rejected mutation")
                            expect(record).to_have_attribute("aria-pressed", "false")
                            expect(record).to_be_enabled()
                            # Exercise the actual Training folder workspace with
                            # held GETs and a synthetic exact-target acknowledgement.
                            folder_workspace[0] = True
                            page.locator('.tab-btn[data-page="training"]').click()
                            folder_a = {"name": "fixture-a", "kind": "session", "image_count": 2}
                            folder_b = {"name": "fixture-b", "kind": "session", "image_count": 3}
                            folder_reply[0] = {"ok": True, "sessions": [folder_a, folder_b]}
                            folder_refresh = page.locator("#refreshSessionsBtn")
                            folder_select = page.locator("#sessionSelect")
                            folder_message = page.locator("#sessionExportMessage")
                            folder_download = page.locator("#downloadSessionBtn")
                            folder_delete = page.locator("#deleteSessionBtn")
                            for control, label in ((folder_select, "Folder"),
                                    (folder_refresh, "Refresh saved folders"),
                                    (folder_download, "Download selected folder"),
                                    (folder_delete, "Delete selected folder")):
                                expect(control).to_have_accessible_name(label)
                            activate_safe(folder_refresh)
                            expect(folder_select).to_have_value("fixture-a")
                            expect(folder_select.locator("option")).to_have_count(2)
                            folder_before = list(mutations)
                            # The Training workspace also exposes the manual drive pad.
                            # Native selector arrows and button Space must not drive it.
                            folder_select.focus()
                            page.keyboard.press("Shift+Tab")
                            page.keyboard.press("Tab")
                            expect(folder_select).to_be_focused()
                            expect(folder_select).to_have_css("outline-style", "solid")
                            page.keyboard.down("ArrowDown")
                            try:
                                expect(folder_select).to_have_value("fixture-b")
                                assert page.evaluate("() => Object.values(state.stepInputs).every(value => !value)")
                            finally:
                                page.keyboard.up("ArrowDown")
                            expect(page.locator("#sessionImageCount")).to_have_text("3")
                            for control in (folder_refresh, folder_download, folder_delete):
                                page.keyboard.press("Tab")
                                expect(control).to_be_focused()
                                expect(control).to_have_css("outline-style", "solid")
                            folder_delete.press("Space")
                            cancel_group = page.get_by_role("group", name="Confirm destructive action")
                            expect(cancel_group).to_contain_text("fixture-b")
                            cancel_folder = cancel_group.get_by_role("button", name="Cancel")
                            expect(cancel_folder).to_be_focused()
                            expect(page.locator(stop)).to_be_enabled()
                            cancel_folder.press("Escape")
                            expect(cancel_group).to_have_count(0)
                            expect(folder_delete).to_be_focused()
                            if width == 390:
                                folder_delete.tap()
                                expect(cancel_group).to_contain_text("fixture-b")
                                cancel_folder.tap()
                                expect(cancel_group).to_have_count(0)
                                expect(folder_delete).to_be_focused()
                            with page.expect_download() as exported:
                                activate_safe(folder_download)
                            assert exported.value.suggested_filename == "fixture-b.zip"
                            assert exported.value.failure() is None
                            assert folder_downloads == ["session=fixture-b"]
                            expect(folder_message).to_have_text("Downloading fixture-b.zip")
                            assert mutations == folder_before, "Training export selection, cancel or download mutated state"
                            assert page.evaluate("() => Object.values(state.stepInputs).every(value => !value)")
                            # Restore initial selection before the existing held-GET race.
                            folder_select.focus()
                            folder_select.press("Home")
                            expect(folder_select).to_have_value("fixture-a")
                            assert mutations == folder_before
                            hold_folder[0] = True
                            folder_reply[0] = {"ok": True, "sessions": [folder_a, dict(folder_b, image_count=9)]}
                            # Store the actual async function promise so the assertions
                            # occur after the held response was processed, not after a sleep.
                            with page.expect_request(lambda req: urlsplit(req.url).path == "/api/record/sessions" and req.method == "GET"):
                                page.evaluate("() => { window.__heldFolderRefresh = refreshSessionsWithFeedback(); }")
                            folder_select.select_option("fixture-b")
                            assert len(held_folders) == 1
                            old_route, old_list = held_folders.pop()
                            old_route.fulfill(status=200, json=old_list)
                            page.evaluate("() => window.__heldFolderRefresh")
                            expect(folder_select).to_have_value("fixture-b")
                            expect(page.locator("#sessionImageCount")).to_have_text("9")
                            # Confirmed deletion supersedes a previously pending list.
                            hold_folder[0] = True
                            with page.expect_request(lambda req: urlsplit(req.url).path == "/api/record/sessions" and req.method == "GET"):
                                page.evaluate("() => { window.__heldFolderRefresh = refreshSessionsWithFeedback(); }")
                            page.locator("#deleteSessionBtn").click()
                            confirm_group = page.get_by_role("group", name="Confirm destructive action")
                            expect(confirm_group).to_contain_text("fixture-b")
                            expect(confirm_group.get_by_role("button", name="Cancel")).to_be_focused()
                            folder_reply[0] = {"ok": True, "sessions": [folder_a]}
                            acknowledge_folder_delete[0] = True
                            confirm_group.get_by_role("button", name="Delete permanently").click()
                            expect(folder_message).to_have_text("Deleted fixture-b.")
                            expect(folder_select).to_have_value("fixture-a")
                            acknowledge_folder_delete[0] = False
                            assert len(held_folders) == 1
                            old_route, old_list = held_folders.pop()
                            old_route.fulfill(status=200, json=old_list)
                            page.evaluate("() => window.__heldFolderRefresh")
                            expect(folder_select.locator("option")).to_have_count(1)
                            expect(folder_message).to_have_text("Deleted fixture-b.")
                            assert folder_message.get_attribute("role") == "status"
                            folder_reply[0] = None
                            folder_refresh.click()
                            expect(folder_select).to_have_value("snapshots")
                            folder_workspace[0] = False
                            page.locator('.tab-btn[data-page="manual"]').click()
                            expect(page.locator("body")).to_have_attribute("data-page", "manual")
                            # Preview/cancel must not change browser storage or safety.
                            storage_key = "PiServerLayout:v0_3_21:manual"
                            saved_before = page.evaluate("(key) => localStorage.getItem(key)", storage_key)
                            boxes_before = page.evaluate("() => JSON.stringify(currentLayout())")
                            page.locator("#previewLayoutBtn").click()
                            expect(page.locator("#layoutPreviewMessage")).to_contain_text("Unsaved preview")
                            expect(page.locator("#cancelLayoutPreviewBtn")).to_be_visible()
                            assert page.evaluate("(key) => localStorage.getItem(key)", storage_key) == saved_before
                            expect(page.locator(stop)).to_be_enabled()
                            page.locator("#cancelLayoutPreviewBtn").click()
                            assert page.evaluate("() => JSON.stringify(currentLayout())") == boxes_before
                            assert page.evaluate("(key) => localStorage.getItem(key)", storage_key) == saved_before
                            page.locator("#previewLayoutBtn").click()
                            page.locator("#saveLayoutBtn").click()
                            assert page.evaluate("(key) => localStorage.getItem(key)", storage_key) is not None
                            expect(page.locator("#cancelLayoutPreviewBtn")).to_be_hidden()
                            # Real pointer click must reach the control; no force/evaluate mutation.
                            page.locator("#essentialsOnly").check(timeout=8000)
                            expect(page.locator("#metricError")).to_be_visible()
                            expect(page.locator("#metricApplied")).to_be_visible()
                            expect(page.locator("#metricWheels")).to_be_hidden()
                            expect(page.locator("#overlayToggleBtn")).to_be_visible()
                            page.locator("#essentialsOnly").focus()
                            page.locator("#essentialsOnly").press("Space")
                            expect(page.locator("#essentialsOnly")).not_to_be_checked()
                            expect(page.locator("#metricWheels")).to_be_visible()
                            # Restore synthetic browser-local test state before remaining checks.
                            page.locator("#resetLayoutBtn").click()
                            # R35: native diagnostic keys must never drive the manual pad.
                            preflight = page.locator("[data-preflight-root] summary")
                            events = page.locator("[data-recent-events-root]")
                            summary = events.locator("summary")
                            page.keyboard.press("Tab")
                            preflight.focus()
                            expect(preflight).to_be_focused()
                            assert preflight.evaluate("(el) => el.matches(':focus-visible') && getComputedStyle(el).outlineWidth === '3px' && getComputedStyle(el).outlineStyle === 'solid'")
                            page.keyboard.press("Space")
                            expect(page.locator("[data-preflight-root]")).to_have_attribute("open", "")
                            page.keyboard.press("Space")
                            expect(page.locator("[data-preflight-root]")).not_to_have_attribute("open", "")
                            page.keyboard.press("Tab")
                            expect(summary).to_be_focused()
                            assert summary.evaluate("(el) => el.matches(':focus-visible') && getComputedStyle(el).outlineWidth === '3px' && getComputedStyle(el).outlineStyle === 'solid'")
                            page.keyboard.press("Space")
                            expect(events).to_have_attribute("open", "")
                            output = events.locator("[data-recent-output]")
                            expect(output).to_contain_text("Motor STOP requested")
                            refresh = events.locator("[data-recent-refresh]")
                            copy = events.locator("[data-recent-copy]")
                            expect(refresh).to_be_enabled()
                            page.keyboard.press("Tab")
                            expect(refresh).to_be_focused()
                            page.keyboard.press("Tab")
                            expect(copy).to_be_focused()
                            page.keyboard.press("Space")
                            expect(events.locator("[data-recent-status]")).to_contain_text("copied")
                            page.keyboard.press("Tab")
                            expect(output).to_be_focused()
                            for key in ("ArrowDown", "ArrowUp", "w"):
                                page.keyboard.down(key)
                                try:
                                    assert page.evaluate("() => Object.values(state.stepInputs).every(value => !value)"), "Diagnostic key activated manual drive"
                                finally:
                                    page.keyboard.up(key)
                            if width == 390:
                                copy.tap()
                                expect(events.locator("[data-recent-status]")).to_contain_text("copied")
                            summary.focus()
                            summary.press("Space")
                            expect(events).not_to_have_attribute("open", "")
                        # Start keyboard modality then focus STOP without activating it.
                        page.keyboard.press("Tab")
                        target = page.locator(stop or primary)
                        target.focus()
                        expect(target).to_be_focused()
                        assert target.evaluate("(el) => el.matches(':focus-visible') && getComputedStyle(el).outlineStyle !== 'none'"), "Primary navigation/STOP lacks keyboard focus ring"
                        assert target.inner_text().strip(), "Primary navigation/STOP has no text"
                        if opener:
                            # Touch on the narrow viewport; otherwise real keyboard activation.
                            control = page.locator(opener)
                            if width == 390:
                                control.tap()
                            else:
                                control.focus()
                                control.press("Enter")
                            dialog = page.locator({
                                "manual": "#mdrvOverlaySettingsPopup",
                                "ai": "#aiWorkflowSettingsPopup",
                                "dashboard": ".style-modal-card",
                            }[name])
                            expect(dialog).to_be_visible(timeout=8000)
                            save = page.locator({
                                "manual": "#mdrvOverlaySettingsApply",
                                "ai": "#aiWorkflowSettingsApply",
                                "dashboard": "#saveStyleSettingsBtn",
                            }[name])
                            case["geometry"]["dialog_save"] = check_geometry(save, width, height, "dialog Save/Apply")
                            page.screenshot(path=str(args.output / f"{name}-{width}-dialog.png"), animations="disabled")
                            first = page.locator({
                                "manual": "#mdrvOverlaySettingsClose",
                                "ai": "#aiWorkflowSettingsClose",
                                "dashboard": "#closeStyleSettingsBtn",
                            }[name])
                            if name == "dashboard":
                                samples = dialog.locator(".style-preview-surface button, .style-preview-surface input")
                                assert samples.count() == 8
                                for sample in samples.all():
                                    assert sample.evaluate("(el) => el.inert")
                                # Traverse the actual browser tab sequence, not programmatic focus alone.
                                first.focus()
                                seen = set()
                                for _ in range(80):
                                    page.keyboard.press("Tab")
                                    active = page.evaluate("""() => ({
                                        id: document.activeElement.id,
                                        sample: !!document.activeElement.closest('.style-preview-surface')
                                    })""")
                                    assert not active["sample"], "Visual-only sample received keyboard focus"
                                    seen.add(active["id"])
                                    if active["id"] == "saveStyleSettingsBtn":
                                        break
                                else:
                                    raise AssertionError("Tab navigation did not reach real Save style")
                                assert {"styleBg", "styleFontScale", "resetStyleSettingsBtn"} <= seen
                            # Verify both ends of the actual native Tab order.
                            first.focus()
                            page.keyboard.press("Shift+Tab")
                            expect(save).to_be_focused()
                            page.keyboard.press("Tab")
                            expect(first).to_be_focused()
                            page.keyboard.press("Escape")
                            expect(dialog).to_be_hidden()
                            expect(control).to_be_focused()
                        if name == "front":
                            before = list(mutations)
                            panel = page.locator("[data-recent-events-root]")
                            summary = panel.locator("summary")
                            # Traverse the actual native tab order from the final mode card.
                            card = page.locator("#frontModeDashboard")
                            card.focus()
                            expect(card).to_be_focused()
                            assert card.evaluate("(el) => el.matches(':focus-visible') && getComputedStyle(el).transform === 'none'"), "Reduced-motion card moved"
                            preflight = page.locator("[data-preflight-root] summary")
                            page.keyboard.press("Tab")
                            expect(preflight).to_be_focused()
                            assert preflight.evaluate("(el) => el.matches(':focus-visible') && getComputedStyle(el).outlineWidth === '3px' && getComputedStyle(el).outlineStyle === 'solid'")
                            page.keyboard.press("Tab")
                            expect(summary).to_be_focused()
                            assert summary.evaluate("(el) => el.matches(':focus-visible') && getComputedStyle(el).outlineWidth === '3px' && getComputedStyle(el).outlineStyle === 'solid'")
                            page.keyboard.press("Space")
                            expect(panel).to_have_attribute("open", "")
                            expect(panel.locator("[data-recent-output]")).to_contain_text("Motor STOP requested")
                            refresh = panel.locator("[data-recent-refresh]")
                            copy = panel.locator("[data-recent-copy]")
                            expect(refresh).to_be_enabled()
                            page.keyboard.press("Tab")
                            expect(refresh).to_be_focused()
                            page.keyboard.press("Tab")
                            expect(copy).to_be_focused()
                            page.keyboard.press("Space")
                            expect(panel.locator("[data-recent-status]")).to_contain_text("copied")
                            page.keyboard.press("Shift+Tab")
                            expect(refresh).to_be_focused()
                            if width == 390:
                                copy.tap()
                                expect(panel.locator("[data-recent-status]")).to_contain_text("copied")
                            assert "Motor STOP requested" in page.evaluate("window.__copiedEvents")
                            assert mutations == before, "Read/copy diagnostics must not mutate state"
                            page.locator(stop).click()
                            expect(page.locator("#fpActionStatus")).to_contain_text("STOP request not confirmed")
                            expect(page.locator("#fpGlobalCode")).to_have_text("Unverified")
                        if name == "settings":
                            target = page.locator("#stSaveSettings")
                            load = page.locator("#stLoadSettings")
                            retry = page.locator("#stRetryApply")
                            detail = page.locator("#stApplyDetail")
                            state = page.locator("#stApplyState")
                            expect(state).to_have_text("Failed", timeout=8000)
                            expect(detail).to_contain_text("timed out")
                            expect(retry).to_have_text("Retry load")
                            expect(load).to_be_enabled()
                            expect(target).to_be_enabled()
                            def activate_settings(control):
                                expect(control).to_be_visible()
                                expect(control).to_be_enabled()
                                if width == 390:
                                    control.tap()
                                else:
                                    control.focus()
                                    control.press("Enter")
                            reject_settings_read[0] = True
                            activate_settings(retry)
                            expect(detail).to_contain_text("Synthetic settings read rejection")
                            expect(state).to_have_text("Failed")
                            expect(page.locator("#stGlobalCode")).to_have_attribute("data-state", "error")
                            reject_settings_read[0] = False
                            activate_settings(retry)
                            expect(detail).to_contain_text("Saved settings loaded")
                            expect(state).to_have_text("Unsaved")
                            expect(retry).to_be_hidden()
                            speed = page.locator('#stManualDriveForm input[name="speed"]')
                            expect(speed).to_have_value("0.43")
                            expect(speed).to_have_accessible_name("Speed")
                            speed_output = page.locator('#stManualDriveForm label').filter(
                                has=page.locator('input[name="speed"]')
                            ).locator("output")
                            expect(speed_output).to_have_text("0.43")
                            before = list(mutations)
                            speed.focus()
                            speed.press("ArrowRight")
                            expect(speed).to_have_value("0.44")
                            expect(speed).to_have_accessible_name("Speed")
                            expect(speed_output).to_have_text("0.44")
                            speed.press("ArrowLeft")
                            expect(speed).to_have_value("0.43")
                            response_log = page.locator("#stActionLog")
                            expect(response_log).to_have_accessible_name("Settings last response")
                            import_input = page.locator("#stImportSettings")
                            expect(import_input).to_have_accessible_name("Import settings JSON file")
                            import_label = page.locator(".st-import")
                            export_button = page.locator("#stExportSettings")
                            for colors in ("none", "active"):
                                page.emulate_media(forced_colors=colors)
                                export_button.focus()
                                page.keyboard.press("Tab")
                                expect(import_input).to_be_focused()
                                expect(import_label).to_have_css("outline-style", "solid")
                                page.keyboard.press("Shift+Tab")
                                expect(export_button).to_be_focused()
                                page.keyboard.press("Tab")
                                expect(import_input).to_be_focused()
                            page.emulate_media(forced_colors="none")
                            for key in ("Enter", "Space"):
                                export_button.focus()
                                page.keyboard.press("Tab")
                                expect(import_input).to_be_focused()
                                with page.expect_file_chooser() as chooser:
                                    import_input.press(key)
                                assert chooser.value.element.get_attribute("id") == "stImportSettings"
                                chooser.value.set_files([])
                            if width == 390:
                                with page.expect_file_chooser() as chooser:
                                    import_input.tap()
                                assert chooser.value.element.get_attribute("id") == "stImportSettings"
                                chooser.value.set_files([])
                            assert mutations == before, "Opening or dismissing Import invoked mutation"
                            response_log.focus()
                            page.keyboard.press("Shift+Tab")
                            page.keyboard.press("Tab")
                            expect(response_log).to_be_focused()
                            expect(response_log).to_have_css("outline-style", "solid")
                            response_log.press("Space")
                            response_log.press("ArrowDown")
                            assert mutations == before, "Read-only settings inspection invoked mutation"
                            # A slow load cannot overwrite an edit or allow overlapping Save.
                            hold_settings[0] = True
                            with page.expect_request(lambda req: req.method == "GET" and urlsplit(req.url).path == "/api/settings"):
                                activate_settings(load)
                            expect(state).to_have_text("Loading")
                            expect(load).to_be_disabled()
                            expect(target).to_be_disabled()
                            expect(page.locator("#stStopAll")).to_be_enabled()
                            speed.fill("0.52")
                            assert len(held_settings) == 1
                            route, snapshot = held_settings.pop()
                            route.fulfill(status=200, json=snapshot)
                            expect(target).to_be_enabled()
                            expect(speed).to_have_value("0.52")
                            expect(state).to_have_text("Unsaved")
                            target.focus()
                            with page.expect_response(lambda response: response.request.method == "POST"
                                    and urlsplit(response.url).path == "/api/settings"):
                                target.press("Enter")
                            expect(page.locator("#stApplyState")).to_have_text("Failed", timeout=8000)
                            expect(page.locator("#stRetryApply")).to_be_visible()
                            expect(page.locator("#stApplyDetail")).to_contain_text("Synthetic rejected mutation")
                            first_attempts = mutations.count("/api/settings")
                            assert first_attempts == 1, mutations
                            # A rejected save remains retryable; a second rejected response
                            # must not be presented as confirmation.
                            with page.expect_response(lambda response: response.request.method == "POST"
                                    and urlsplit(response.url).path == "/api/settings"):
                                page.locator("#stRetryApply").click()
                            expect(page.locator("#stApplyState")).to_have_text("Failed", timeout=8000)
                            assert mutations.count("/api/settings") == first_attempts + 1, mutations
                            expect(target).to_be_enabled()
                            # Emergency STOP remains operable after the settings failure.
                            # A rejected response must report an error rather than claim success
                            # or cause an unhandled JavaScript Promise rejection.
                            with page.expect_response(lambda response: response.request.method == "POST"
                                    and urlsplit(response.url).path == "/api/control/stop"):
                                page.locator("#stStopAll").click()
                            expect(page.locator("#stGlobalCode")).to_have_text("PISD-API-STOP-FAILED")
                            expect(page.locator("#stGlobalCode")).to_have_attribute("data-state", "error")
                            expect(page.locator("#stActionLog")).to_contain_text("STOP request not confirmed")
                        if name == "manual":
                            toggle = page.locator("#mdrvToggleLog")
                            panel = page.locator("#manualDriveLogPanel")
                            output = page.locator("#mdrvLog")
                            expect(toggle).to_have_attribute("aria-expanded", "false")
                            expect(panel).to_be_hidden()
                            before = list(mutations)
                            page.keyboard.press("Tab")
                            toggle.focus()
                            expect(toggle).to_be_focused()
                            page.keyboard.press("Space")
                            expect(toggle).to_have_attribute("aria-expanded", "true")
                            expect(toggle).to_have_text("Hide action log")
                            expect(panel).to_be_visible()
                            # Traverse actual Tab order (other recording controls may intervene).
                            for _ in range(20):
                                page.keyboard.press("Tab")
                                if output.evaluate("(el) => document.activeElement === el"):
                                    break
                            expect(output).to_be_focused()
                            expect(output).to_have_accessible_name("Manual Drive action log")
                            assert output.evaluate("(el) => el.matches(':focus-visible') && getComputedStyle(el).outlineStyle === 'solid'")
                            # These keys belong to the read-only log, not driving or capture.
                            for key in ("ArrowDown", "ArrowUp", "ArrowLeft", "ArrowRight", "Space", "r", "s"):
                                page.keyboard.press(key)
                            assert mutations == before, "Read-only action log invoked a mutation"
                            toggle.focus()
                            page.keyboard.press("Space")
                            expect(toggle).to_have_attribute("aria-expanded", "false")
                            expect(panel).to_be_hidden()
                            if width == 390:
                                toggle.tap()
                                expect(toggle).to_have_attribute("aria-expanded", "true")
                                toggle.tap()
                                expect(toggle).to_have_attribute("aria-expanded", "false")
                            assert mutations == before
                        if name in ("manual", "ai"):
                            # Space on a drive pad still dispatches the existing global STOP.
                            # No actual motor command is delivered by the fixture.
                            pad = page.locator("#mdrvDragPad" if name == "manual" else "#aiManualDrivePad")
                            if name == "ai":
                                expect(page.locator("#aiManualDriveTab")).to_have_attribute("aria-selected", "true")
                            pad.focus()
                            before = len(mutations)
                            with page.expect_request(lambda req: req.method == "POST" and urlsplit(req.url).path == "/api/control/stop"):
                                page.keyboard.press("Space")
                            # Wait for the intercepted network response, not a hardware acknowledgement.
                            page.wait_for_timeout(100)
                            assert "/api/control/stop" in mutations[before:]
                        if name == "testing":
                            before = list(mutations)
                            method = page.locator("#customMethod")
                            path = page.locator("#customPath")
                            body = page.locator("#customBody")
                            expect(method).to_have_accessible_name("API request method")
                            expect(path).to_have_accessible_name("API request path")
                            expect(body).to_have_accessible_name("API request JSON body")
                            chip = page.locator(".endpoint-chip").filter(has_text="GET /api/status").first
                            expect(chip).to_be_visible()
                            expect(chip).to_have_accessible_name("Prepare GET /api/status")
                            method.select_option("POST")
                            path.fill("/fixture-not-sent")
                            if width == 390:
                                chip.tap()
                            else:
                                chip.focus()
                                page.keyboard.press("Space")
                            expect(method).to_have_value("GET")
                            expect(path).to_have_value("/api/status")
                            assert mutations == before, "Preparing API request invoked a mutation"
                            for selector, label in (("#fpsTestPanel", "FPS test output"), ("#smokeTestPanel", "Smoke test output"),
                                                    ("#lastResponse", "Last API response"), ("#statusPanel", "Runtime status")):
                                output = page.locator(selector)
                                expect(output).to_have_accessible_name(label)
                                page.keyboard.press("Tab")
                                output.focus()
                                expect(output).to_be_focused()
                                assert output.evaluate("(el) => el.matches(':focus-visible') && getComputedStyle(el).outlineStyle === 'solid'")
                                page.keyboard.press("Space")
                            assert mutations == before, "Read-only output invoked a mutation"
                            expect(page.locator('#motorChannelForm input[name="enable_motor_output"]')).not_to_be_checked()
                            expect(page.locator("#stopAllBtn")).to_be_enabled()
                        if name == "panel_lab":
                            before = list(mutations)
                            checks = page.locator("#ptRunAllChecks")
                            checks.focus()
                            page.keyboard.press("Space")
                            report = page.locator("#ptPanelReport")
                            expect(report).to_contain_text("panel.structure_summary")
                            expect(report).to_have_accessible_name("Panel test output")
                            panel = page.locator(".pt-panel").first
                            size = panel.locator('[data-panel-size="large"]')
                            expect(size).to_have_accessible_name(re.compile("^Large size: .+"))
                            if width == 390:
                                size.tap()
                            else:
                                size.focus()
                                page.keyboard.press("Space")
                            expect(panel).to_have_attribute("data-size", "large")
                            expect(size).to_have_attribute("aria-pressed", "true")
                            expect(panel.locator('[data-panel-size="compact"]')).to_have_attribute("aria-pressed", "false")
                            # Actual selected-state rendering in normal and OS forced colors.
                            for colors in ("none", "active"):
                                page.emulate_media(forced_colors=colors)
                                expect(size).to_have_css("text-decoration-line", "underline")
                                expect(panel.locator('[data-panel-size="compact"]')).to_have_css("text-decoration-line", "none")
                                size.focus()
                                page.keyboard.press("Tab")
                                page.keyboard.press("Shift+Tab")
                                expect(size).to_be_focused()
                                expect(size).to_have_css("outline-style", "solid")
                            page.emulate_media(forced_colors="none")
                            # Sample bodies have no live buttons or tabbable controls.
                            mocks = page.locator(".pt-mock-body")
                            expect(mocks).to_have_count(7)
                            expect(page.locator(".pt-mock-body button")).to_have_count(0)
                            assert mocks.evaluate_all("(nodes) => nodes.every(node => node.inert)")
                            sample = page.locator(".pt-mock-body input").first
                            sample.evaluate("(node) => node.focus()")
                            assert not sample.evaluate("(node) => node === document.activeElement")
                            expect(page.locator("#manual-drive-panel [data-panel-test]")).to_be_enabled()
                            expect(page.locator("#ptRunPanelApiChecks")).to_be_enabled()
                            assert page.evaluate("() => matchMedia('(prefers-reduced-motion: reduce)').matches")
                            contract = panel.locator("[data-panel-contract]")
                            if width == 390:
                                contract.tap()
                            else:
                                contract.focus()
                                page.keyboard.press("Space")
                            expect(report).to_contain_text("CONTRACT")
                            page.keyboard.press("Tab")
                            report.focus()
                            expect(report).to_be_focused()
                            page.keyboard.press("Space")
                            assert mutations == before, "Structure/contract inspection invoked a mutation"
                            expect(page.locator("#ptStopAll")).to_be_enabled()
                        if name == "presentation":
                            # Check actual shared API and page startup before exercising the controls.
                            page.wait_for_function("() => Boolean(window.PiSDPanelPresentation)")
                            expect(page.locator("#ppFeedback")).to_have_text("Panel presentation settings ready.")
                            expect(page.locator("#ppPreviewGrid .pp-button-row")).to_have_attribute("inert", "")
                            expect(page.locator("#ppPreviewGrid .pp-console")).to_have_attribute("inert", "")
                            expect(page.locator("#ppPreviewGrid button")).to_have_count(0)
                            expect(page.get_by_role("button", name="Run", exact=True)).to_have_count(0)
                            expect(page.get_by_role("button", name="STOP", exact=True)).to_have_count(0)
                            auto = page.locator("#ppAutoSave")
                            expect(auto).to_have_accessible_name("Auto-save changes globally")
                            if auto.is_checked():
                                if width == 390:
                                    auto.tap()
                                else:
                                    auto.press("Space")
                            expect(auto).not_to_be_checked()
                            slider = page.locator("#ppFontScale")
                            expect(slider).to_have_accessible_name("Font scale")
                            slider.press("Home")
                            slider.press("ArrowRight")
                            expect(page.locator('[data-range-value-for="ppFontScale"]')).to_have_text("0.85")
                            expect(page.locator("#ppSavedState")).to_have_text("preview applied")
                            expect(page.locator("#ppFeedback")).to_have_text("Live preview applied only.")
                            auto.focus()
                            page.keyboard.press("Tab")
                            expect(page.locator("#ppExport")).to_be_focused()
                            page.keyboard.press("Tab")
                            expect(page.locator("#ppImportButton")).to_be_focused()
                            page.keyboard.press("Tab")
                            output = page.locator("#ppOutput")
                            expect(output).to_be_focused()
                            expect(output).to_have_accessible_name("Current presentation preset JSON")
                            page.keyboard.press("Space")
                            assert not mutations, "Preview/read-only controls invoked a mutation"
                            apply = page.locator("#ppApply")
                            if width == 390:
                                apply.tap()
                            else:
                                apply.press("Space")
                            expect(page.locator("#ppFeedback")).to_have_text("Applied preview settings.")
                            save = page.locator("#ppSave")
                            if width == 390:
                                save.tap()
                            else:
                                save.press("Space")
                            expect(page.locator("#ppSavedState")).to_have_text("save failed")
                            expect(page.locator("#ppFeedback")).to_contain_text("not confirmed saved")
                            assert mutations == ["/api/settings"], "Unexpected presentation mutation"
                        if name == "motor_tuning":
                            # Preserve the deliberately cleared tuning layout.
                            expect(page.get_by_role("heading", name="Motor tuning panels removed")).to_be_visible()
                            expect(page.locator("button, input, select, textarea")).to_have_count(0)
                            assert not mutations
                            back = page.locator(".mtun-back")
                            expect(back).to_have_accessible_name("Back to Front Page")
                            if width == 390:
                                back.tap()
                            else:
                                back.press("Enter")
                            expect(page).to_have_url(ORIGIN + "/")
                        if name == "dashboard":
                            # The E-STOP request is intercepted too; never treat a 503 as a physical stop.
                            with page.expect_request(lambda req: req.method == "POST" and urlsplit(req.url).path == "/api/system/estop"):
                                page.locator(stop).press("Enter")
                        case["page_errors"] = list(errors)
                        if errors:
                            raise AssertionError("Browser JavaScript errors: " + "; ".join(errors))
                    except Exception as exc:
                        case["errors"].append(str(exc))
                        page.screenshot(path=str(args.output / f"{name}-{width}-failure.png"), animations="disabled")
                    finally:
                        case["intercepted_mutations"] = mutations
                        cases.append(case)
                        context.close()
                    print(name, width, "FAIL" if case["errors"] else "PASS", case["errors"], flush=True)
            browser.close()
    (args.output / "matrix.json").write_text(json.dumps({"revision": args.revision, "component": args.component,
        "fixture": "actual templates, read-only simulation; all mutations intercepted", "visual_review": "pending", "cases": cases}, indent=2))
    return int(any(c["errors"] for c in cases))


if __name__ == "__main__":
    raise SystemExit(main())
