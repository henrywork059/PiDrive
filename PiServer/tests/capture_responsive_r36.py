#!/usr/bin/env python3
"""R36 passive viewport screenshot/geometry audit for active PiDrive web UIs.

Run from a desktop against the CURRENT checked-out branch and its running
web server. The script itself never POSTs camera/motor/mission/scan/Save
commands. Rendering a page may have its normal runtime side effects, and
visiting PiBooter from a recognized client may activate its existing setup
session. It only clicks non-mutating presentation dialogs.
It deliberately makes no claim that a static HTML fixture is the live runtime.

Install for development: python -m pip install playwright
                         python -m playwright install chromium
Example:
 python PiServer/tests/capture_responsive_r36.py --suite piserver --url http://127.0.0.1:8080/ --label baseline --revision <git-sha>
 python PiServer/tests/capture_responsive_r36.py --suite piserver --url http://127.0.0.1:8080/ --label patched --revision <git-sha>

Use the same output root for comparable baseline/patch shots. Do not click
physical drive/STOP/arm controls during unattended screenshot collection.
Screenshots may reveal private Wi-Fi names, LAN IPs or camera views: keep these
output folders local and do not commit them as PR artifacts without redaction.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

WIDTHS = (390, 768, 1024, 1440)
HEIGHTS = {390: 844, 768: 1024, 1024: 768, 1440: 900}

# Selectors come from the actual reviewed R35/R33 templates, not guessed IDs.
# A missing essential control is a failure, not a screenshot success.
SUITES = {
    "pisd-manual": {
        "essential": {"stop_top": "#mdrvStopTop", "stop_big": "#mdrvStopBig",
                      "stop_pad": "#mdrvStopPad", "drag_pad": "#mdrvDragPad",
                      "preview": ".mdrv-preview-frame"},
        "square": "drag_pad", "camera": "preview",
        "dialog": ("#mdrvOverlaySettingsOpen", ".mdrv-overlay-settings-card", "#mdrvOverlaySettingsApply"),
    },
    "pisd-ai": {
        "essential": {"stop": "#aiStopAll", "save_ai": "#aiSaveConfig",
                      "preview": ".mdrv-preview-frame", "manual_pad": "#aiManualDrivePad"},
        "square": None, "camera": "preview",
        "dialog": ("#aiWorkflowSettingsOpen", ".mdrv-overlay-settings-card", "#aiWorkflowSettingsApply"),
    },
    "piserver": {
        "essential": {"estop": "#estopToggle", "drag_pad": "#joystickArea",
                      "preview": ".viewer-frame", "save_tuning": "#saveRuntimeBtn"},
        "square": "drag_pad", "camera": None,
        "dialog": ("#openStyleSettingsBtn", ".style-modal-card", "#saveStyleSettingsBtn"),
    },
    "customdrive-gui": {
        "essential": {"manual_stop": "#manualStopBtn", "estop": "#estopToggle",
                      "drag_pad": "#joystickArea", "preview": ".viewer-frame"},
        "square": "drag_pad", "camera": None,
        "dialog": ("#openDriveSettingsBtn", "#driveSettingsModal .modal-window", "#saveDriveSettingsBtn"),
    },
    "customdrive-mission1": {
        "essential": {"mission_stop": "#stopBtn", "save_config": "#saveConfigBtn",
                      "preview": ".viewer-stage", "timeline": "#missionTimeline"},
        "square": None, "camera": "preview", "dialog": None,
    },
    "pibooter": {
        "essential": {"connect": "form[action='/connect'] button[type='submit']",
                      "setup": "#setup-content"},
        "square": None, "camera": None, "dialog": None,
        "optional": {"choose_wifi": ".scan-network-table button",
                     "forget_wifi": ".saved-profile-table button"},
    },
}

def geometry(locator, viewport_width: int):
    """Return raw geometry and a conservative horizontal clipping check."""
    return locator.evaluate("""(el, width) => {
      const rect = el.getBoundingClientRect();
      const css = getComputedStyle(el);
      const range = document.createRange();
      range.selectNodeContents(el);
      const textRects = Array.from(range.getClientRects());
      const textClipped = ['hidden', 'clip'].includes(css.overflowX)
        && textRects.some(x => x.right > rect.right + 3);
      return {
        x: Math.round(rect.x), y: Math.round(rect.y),
        width: Math.round(rect.width), height: Math.round(rect.height),
        in_horizontal_view: rect.left >= -2 && rect.right <= width + 2,
        visible: css.visibility !== 'hidden' && css.display !== 'none'
          && rect.width > 0 && rect.height > 0,
        text_clipped: textClipped,
        scroll_width: el.scrollWidth, client_width: el.clientWidth
      };
    }""", viewport_width)


def capture_case(browser, config, suite: str, url: str, width: int,
                 out: Path, baseline: Path | None):
    height = HEIGHTS[width]
    context = browser.new_context(
        viewport={"width": width, "height": height},
        device_scale_factor=1, reduced_motion="reduce")
    page = context.new_page()
    result = {"width": width, "height": height, "url": url,
              "checks": {}, "errors": [], "warnings": [], "screenshots": []}
    try:
        response = page.goto(url, wait_until="domcontentloaded", timeout=25000)
        if response is None or response.status >= 400:
            result["errors"].append("Page did not load successfully")
            result["result"] = "fail"
            return result
        page.wait_for_timeout(350)
        result["document"] = page.evaluate("""() => ({
          scroll_width: document.documentElement.scrollWidth,
          viewport_width: window.innerWidth,
          scroll_height: document.documentElement.scrollHeight,
          viewport_height: window.innerHeight
        })""")
        if width <= 1024 and result["document"]["scroll_width"] > width + 3:
            result["errors"].append("Horizontal page overflow")
        shot = out / f"{suite}_{width}.png"
        page.screenshot(path=str(shot), full_page=True, animations="disabled")
        result["screenshots"].append(str(shot))
        for name, selector in config["essential"].items():
            node = page.locator(selector).first
            if node.count() == 0:
                result["errors"].append(f"Required control missing: {name} {selector}")
                continue
            try:
                node.scroll_into_view_if_needed(timeout=4000)
                g = geometry(node, width)
                result["checks"][name] = g
                if not g["visible"] or not g["in_horizontal_view"]:
                    result["errors"].append(f"Control unreachable horizontally: {name}")
                if (("stop" in name or "save" in name or name in ("estop", "connect"))
                        and g["text_clipped"]):
                    result["errors"].append(f"Action label clipped: {name}")
            except Exception as error:
                result["errors"].append(f"Could not inspect {name}: {error}")
        for name, selector in config.get("optional", {}).items():
            node = page.locator(selector).first
            if node.count():
                node.scroll_into_view_if_needed(timeout=4000)
                g = geometry(node, width)
                result["checks"][name] = g
                if not g["in_horizontal_view"] or not g["visible"]:
                    result["errors"].append(f"Optional action inaccessible: {name}")
            else:
                result["warnings"].append(f"{name}: not rendered; supply a scan/profile fixture to test")
        if config["square"] and config["square"] in result["checks"]:
            g = result["checks"][config["square"]]
            if abs(g["width"] - g["height"]) > 4:
                result["errors"].append("Manual drag pad no longer square")
        if config["camera"] and config["camera"] in result["checks"]:
            g = result["checks"][config["camera"]]
            if g["height"] and abs(g["width"] / g["height"] - 16/9) > 0.14:
                result["warnings"].append("Preview does not approximate 16:9; verify configured camera aspect")
        if config["dialog"]:
            opener, card, save = config["dialog"]
            opener_node = page.locator(opener).first
            if opener_node.count():
                # Only click a local settings opener, never an action that moves hardware.
                opener_node.click(timeout=5000)
                panel = page.locator(card).first
                save_node = page.locator(save).first
                if panel.count() == 0 or save_node.count() == 0:
                    result["errors"].append("Settings modal or Save control missing")
                else:
                    try:
                        save_node.scroll_into_view_if_needed(timeout=5000)
                        card_g = geometry(panel, width)
                        save_g = geometry(save_node, width)
                        result["checks"]["dialog"] = card_g
                        result["checks"]["dialog_save"] = save_g
                        if not card_g["in_horizontal_view"] or card_g["height"] > height + 2:
                            result["errors"].append("Settings dialog exceeds viewport")
                        if not save_g["in_horizontal_view"] or not save_g["visible"]:
                            result["errors"].append("Settings Save cannot be reached")
                        dialog_shot = out / f"{suite}_{width}_dialog.png"
                        page.screenshot(path=str(dialog_shot), animations="disabled")
                        result["screenshots"].append(str(dialog_shot))
                    except Exception as error:
                        result["errors"].append(f"Settings Save inspection failed: {error}")
            else:
                result["errors"].append("Settings opener missing")
        result["result"] = "fail" if result["errors"] else "review"
    except Exception as error:
        result["errors"].append(f"Capture failed: {error}")
        result["result"] = "fail"
    finally:
        context.close()
    # Screenshots of camera feeds/status are dynamic; even a pixel-perfect diff
    # cannot replace inspection of the STOP/Save reachability and layout.
    if baseline is not None:
        prior = baseline / f"{suite}_{width}.png"
        if not prior.exists():
            result["warnings"].append(f"No baseline screenshot at {prior}")
        else:
            result["warnings"].append(f"Review patched screenshot against {prior} manually")
    return result


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--suite", choices=sorted(SUITES), required=True)
    p.add_argument("--url", required=True, help="Live UI base URL; do not use stale template snapshots")
    p.add_argument("--output", default="r36_screenshots", help="Output directory for screenshot artifacts")
    p.add_argument("--label", choices=("baseline", "patched"), required=True)
    p.add_argument("--revision", required=True, help="Exact running git commit/tag; recorded in matrix")
    p.add_argument("--baseline-dir", type=Path, help="Directory with previous baseline PNGs for review")
    p.add_argument("--acknowledge-booter-visit", action="store_true",
                   help="Required for PiBooter: visiting from a permitted client may hold its setup session open")
    args = p.parse_args()
    if args.suite == "pibooter" and not args.acknowledge_booter_visit:
        p.error("PiBooter GET may activate the existing first-client session; pass --acknowledge-booter-visit only when authorized")
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("Missing Playwright; install 'pip install playwright' then 'python -m playwright install chromium'",
              file=sys.stderr)
        return 2
    folder = Path(args.output) / args.suite / args.label
    folder.mkdir(parents=True, exist_ok=True)
    records = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        try:
            for width in WIDTHS:
                records.append(capture_case(browser, SUITES[args.suite], args.suite,
                                            args.url, width, folder, args.baseline_dir))
        finally:
            browser.close()
    report = {"suite": args.suite, "label": args.label, "revision": args.revision,
              "captured_at_utc": datetime.now(timezone.utc).isoformat(),
              "widths": list(WIDTHS), "results": records,
              "visual_review": "required; camera and status are dynamic"}
    target = folder / "matrix.json"
    target.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"Saved {target}")
    for item in records:
        print(f"{item['width']:4d}px | {item['result']:6} | "
              f"{len(item['errors'])} errors, {len(item['warnings'])} warnings")
    return 1 if any(x["errors"] for x in records) else 0


if __name__ == "__main__":
    raise SystemExit(main())
