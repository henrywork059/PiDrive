"""V17 M0: matched, real-browser baseline only; no driving authorization.

Run inside the existing isolated emulator acceptance test. Never use with a
hardware-enabled runtime. This measures the existing pages, not V17 readiness.
"""
import hashlib
import json
import time
from collections import Counter
from pathlib import Path
from urllib.parse import urlsplit

from playwright.sync_api import expect


def capture_v17_baseline(browser, runtime, origin, output, revision):
    report = {"revision": revision, "scope": "virtual hardware only; existing routes; no motor authorization", "cases": []}
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)

    def write_report():
        (output / "v17-m0-baseline.json").write_text(
            json.dumps(report, indent=2), encoding="utf-8")

    def assert_neutral():
        state = runtime.status()
        assert state["hardware_enabled"] is False, "V17 probe must be virtual only"
        assert state["running"], "V17 probe requires running emulator"
        motor = state["engine"]["motor"]
        assert abs(motor["left_intended"]) < .001 and abs(motor["right_intended"]) < .001, motor

    assert_neutral()
    for mode, route, shell, arm, live, frame_id in (
        ("manual", "/manual-drive", "#manualDriveShell", "#mdrvArm", "#mdrvLiveCamera", "#mdrvPreviewFrame"),
        ("ai", "/ai-mode", "#aiModeShell", "#aiEnableMotor", "#aiLive", "#aiPreviewFrame"),
    ):
        for width, height in ((1440, 900), (390, 844)):
            case = {"mode": mode, "viewport": [width, height], "errors": []}
            report["cases"].append(case)
            context = browser.new_context(viewport={"width": width, "height": height})
            try:
                page = context.new_page()
                page.bring_to_front()
                events = []
                origin_parts = urlsplit(origin)

                def observe(request):
                    parsed = urlsplit(request.url)
                    if (parsed.scheme, parsed.netloc) != (origin_parts.scheme, origin_parts.netloc):
                        return
                    if parsed.path.startswith("/api/") or parsed.path == "/video_feed":
                        events.append((request.method, parsed.path))

                page.on("request", observe)
                page.on("pageerror", lambda error: case["errors"].append(str(error)))
                started = time.monotonic()
                page.goto(origin + route, wait_until="domcontentloaded")
                expect(page.locator(shell)).to_be_visible()
                expect(page.locator(arm)).not_to_be_checked()
                case["navigation_to_shell_ms"] = (time.monotonic() - started) * 1000
                assert_neutral()
                frame = page.locator(frame_id)
                image = frame.locator("img").first
                if frame.get_attribute("data-preview-mode") != "live":
                    started = time.monotonic()
                    page.locator(live).click()
                    expect(frame).to_have_attribute("data-preview-mode", "live", timeout=15000)
                    case["start_live_to_mode_ms"] = (time.monotonic() - started) * 1000
                else:
                    case["start_live_to_mode_ms"] = None
                started = time.monotonic()
                expect(image).to_have_attribute("data-preview-mode", "live", timeout=15000)
                page.wait_for_function(
                    "(selector) => { const img=document.querySelector(selector+' img'); return img && new URL(img.currentSrc || img.src, location.href).pathname==='/video_feed' && img.naturalWidth>0 && img.naturalHeight>0; }",
                    arg=frame_id, timeout=15000)
                case["live_decode_wait_ms"] = (time.monotonic() - started) * 1000
                assert_neutral()
                toggle = page.locator("#drivingCockpitToggle")
                started = time.monotonic()
                toggle.click()
                expect(toggle).to_have_attribute("aria-pressed", "true")
                page.wait_for_function("""selector => {
                    const f=document.querySelector(selector), i=f.querySelector('img'), o=f.querySelector('.mdrv-drive-overlay');
                    const a=i.getBoundingClientRect(), b=o.getBoundingClientRect();
                    return i.naturalWidth>0 && a.height>0 && getComputedStyle(i).objectFit==='contain'
                        && Math.abs(a.width/a.height-i.naturalWidth/i.naturalHeight)<.03
                        && ['x','y','width','height'].every(k=>Math.abs(a[k]-b[k])<=2);
                }""", arg=frame_id, timeout=15000)
                case["cockpit_toggle_to_aligned_ms"] = (time.monotonic() - started) * 1000
                case["geometry"] = frame.evaluate("""f => {
                    const i=f.querySelector('img'), o=f.querySelector('.mdrv-drive-overlay');
                    const rect=e=>{const r=e.getBoundingClientRect();return [r.x,r.y,r.width,r.height]};
                    return {image:rect(i),overlay:rect(o),natural:[i.naturalWidth,i.naturalHeight],
                        viewport:[innerWidth,innerHeight],scroll_y:scrollY,fit:getComputedStyle(i).objectFit};
                }""")
                # Exclude startup, explicit camera action and presentation toggle.
                page.wait_for_timeout(2000)
                offset = len(events)
                started = time.monotonic()
                page.wait_for_timeout(6000)
                case["quiet_window_ms"] = (time.monotonic() - started) * 1000
                case["quiet_requests"] = dict(Counter(f"{method} {path}" for method, path in events[offset:]))
                case["startup_and_action_requests"] = dict(Counter(f"{method} {path}" for method, path in events[:offset]))
                assert_neutral()
                expect(page.locator(arm)).not_to_be_checked()
                case["motor_neutral"] = True
                case["screenshot"] = f"v17-m0-{mode}-{width}.png"
                path = output / case["screenshot"]
                page.screenshot(path=str(path), full_page=True)
                case["screenshot_sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
                assert not case["errors"], case["errors"]
            except Exception as exc:
                case["failure"] = str(exc)
                raise
            finally:
                context.close()
                write_report()
            assert_neutral()
    return report
