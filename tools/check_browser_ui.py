"""Real Chromium, actual Flask templates and read-only simulation fixtures.

All network requests are intercepted. No mutation reaches any backend.
Only run with synthetic, disposable settings; no external browser origin.
"""
import argparse
import json
import os
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
        ("manual", "/manual-drive", "#mdrvStopTop", "#mdrvDragPad", "#mdrvPreviewFrame", "#mdrvOverlaySettingsOpen"),
        ("ai", "/ai-mode", "#aiStopAll", "#aiSaveConfig", "#aiPreviewFrame", "#aiWorkflowSettingsOpen"),
        ("settings", "/settings", "#stStopAll", "#stSaveSettings", None, None),
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
                    page = context.new_page()
                    mutations = []
                    errors = []
                    def route_request(route):
                        req = route.request
                        parsed = urlsplit(req.url)
                        if f"{parsed.scheme}://{parsed.netloc}" != ORIGIN:
                            route.abort()
                            return
                        if req.method != "GET":
                            mutations.append(parsed.path)
                            route.fulfill(status=503, content_type="application/json",
                                          body='{"ok":false,"message":"Synthetic rejected mutation"}')
                            return
                        if parsed.path in {"/video_feed", "/api/camera/frame.jpg"}:
                            route.fulfill(status=204, body="")
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
                        if name == "ai":
                            expect(page.locator("#aiModelSelect")).to_have_value("")
                            expect(page.locator("#aiModelSelect option")).to_contain_text("No models")
                        if name == "dashboard":
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
                        # Start keyboard modality then focus STOP without activating it.
                        page.keyboard.press("Tab")
                        target = page.locator(stop)
                        target.focus()
                        expect(target).to_be_focused()
                        assert target.evaluate("(el) => el.matches(':focus-visible') && getComputedStyle(el).outlineStyle !== 'none'"), "STOP lacks keyboard focus ring"
                        assert target.inner_text().strip(), "STOP has no text"
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
                            # Verify both ends of the actual native Tab order.
                            first.focus()
                            page.keyboard.press("Shift+Tab")
                            expect(save).to_be_focused()
                            page.keyboard.press("Tab")
                            expect(first).to_be_focused()
                            page.keyboard.press("Escape")
                            expect(dialog).to_be_hidden()
                            expect(control).to_be_focused()
                        if name == "settings":
                            target = page.locator("#stSaveSettings")
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
