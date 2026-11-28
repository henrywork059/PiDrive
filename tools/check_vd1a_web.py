"""Actual templates in Chromium using isolated hardware-free Flask fixtures.
Only the explicit PiSD presentation-save POST reaches a disposable backend.
"""
import argparse
from contextlib import ExitStack
import hashlib
import json
import re
from pathlib import Path
import tempfile
from urllib.parse import urlsplit

from playwright.sync_api import expect, sync_playwright
from check_browser_ui import fixture, ORIGIN, PAGES


def luminance(rgb):
    channels = [int(x) / 255 for x in rgb.strip("rgb() ").split(",")[:3]]
    return sum(w * (x / 12.92 if x <= .04045 else ((x + .055) / 1.055) ** 2.4)
               for x, w in zip(channels, (.2126, .7152, .0722)))


def contrast(fg, bg):
    a, b = sorted((luminance(fg), luminance(bg)), reverse=True)
    return (a + .05) / (b + .05)


def inspect(page, selector, minimum=4.5):
    loc = page.locator(selector).first
    expect(loc).to_be_visible()
    values = loc.evaluate("""el => {
        const style = getComputedStyle(el);
        let node=el, bg=style.backgroundColor;
        while (node && (bg === 'rgba(0, 0, 0, 0)' || bg === 'transparent')) {
            node=node.parentElement;
            if(node) bg=getComputedStyle(node).backgroundColor;
        }
        return {foreground:style.color, background:bg};
    }""")
    assert values["foreground"].startswith("rgb(") and values["background"].startswith("rgb("), values
    values["contrast"] = contrast(values["foreground"], values["background"])
    assert values["contrast"] >= minimum, (selector, values)
    return values


def check_disabled_control(page, selector, surface, muted):
    """Inspect a temporary disabled presentation state; no click or API mutation."""
    loc = page.locator(selector).first
    expect(loc).to_be_visible()
    original = loc.evaluate("el => el.disabled")
    try:
        loc.evaluate("el => { el.disabled = true; }")
        expect(loc).to_be_disabled()
        expect(loc).to_have_css("background-color", surface)
        expect(loc).to_have_css("color", muted)
        expect(loc).to_have_css("opacity", "1")
        expect(loc).to_have_css("cursor", "not-allowed")
        return inspect(page, selector)
    finally:
        loc.evaluate("(el, value) => { el.disabled = value; }", original)


def check_action_feedback(page, selector):
    """Exercise a real pointer press, then cancel it outside the safe action."""
    loc = page.locator(selector).first
    expect(loc).to_be_enabled()
    loc.scroll_into_view_if_needed()
    loc.hover()
    expect(loc).to_have_css("box-shadow", re.compile(r"0px 0px 0px 1px inset"))
    hovered = loc.bounding_box()
    hover_contrast = inspect(page, selector)
    page.mouse.down()
    try:
        expect(loc).to_have_css("box-shadow", re.compile(r"0px 0px 0px 2px inset"))
        pressed = loc.bounding_box()
        assert hovered and pressed
        assert (hovered["width"], hovered["height"]) == (pressed["width"], pressed["height"])
        press_contrast = inspect(page, selector)
    finally:
        page.mouse.move(0, 0)
        page.mouse.up()
    return {"hover": hover_contrast, "pressed": press_contrast, "geometry_preserved": True}


def check_local_typography(page, numeric, technical):
    result = page.evaluate("""async () => {
        const faces = await Promise.all([
            document.fonts.load('400 16px "PiDrive Inter"'),
            document.fonts.load('400 16px "PiDrive Plex Mono"')
        ]);
        await document.fonts.ready;
        return faces.map(items => items.map(face => ({family: face.family, status: face.status})));
    }""")
    assert all(items and all(face["status"] == "loaded" for face in items) for items in result), result
    expect(page.locator("body")).to_have_css("font-family", re.compile("PiDrive Inter"))
    expect(page.locator(numeric).first).to_have_css("font-variant-numeric", "tabular-nums")
    expect(page.locator(technical).first).to_have_css("font-family", re.compile("PiDrive Plex Mono"))
    return result


def check_narrow_targets(page, selectors):
    boxes = []
    for selector in selectors:
        loc = page.locator(selector).first
        expect(loc).to_be_visible()
        loc.scroll_into_view_if_needed()
        box = loc.bounding_box()
        assert box and box["height"] >= 44 and box["width"] >= 44, (selector, box)
        assert box["x"] >= -1 and box["x"] + box["width"] <= page.viewport_size["width"] + 1, (selector, box)
        assert box["y"] >= -1 and box["y"] + box["height"] <= page.viewport_size["height"] + 1, (selector, box)
        # Trial performs Playwright's real hit-target/actionability checks
        # without triggering a setting mutation, reset or navigation.
        loc.click(trial=True)
        boxes.append({"selector": selector, **box, "hit_target_verified": True})
    return boxes


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("component", choices=("PiSD", "PiServer"))
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--revision", required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    report = {"revision": args.revision, "component": args.component, "captures": [], "persistence": []}
    try:
        with tempfile.TemporaryDirectory() as tmp, ExitStack() as stack, sync_playwright() as pw:
            client = fixture(args.component, Path(tmp), stack)
            browser = pw.chromium.launch()
            context = browser.new_context(viewport={"width": 1440, "height": 900},
                                          reduced_motion="reduce", service_workers="block")
            errors = []
            saves = []
            def route_request(route):
                req = route.request
                url = urlsplit(req.url)
                if f"{url.scheme}://{url.netloc}" != ORIGIN:
                    route.abort()
                    return
                target = url.path + ("?" + url.query if url.query else "")
                if req.method == "GET":
                    if url.path in ("/video_feed", "/api/camera/frame.jpg"):
                        route.fulfill(status=204, body="")
                        return
                    res = client.get(target, base_url=ORIGIN)
                elif args.component == "PiSD" and req.method == "POST" and url.path == "/api/settings":
                    payload = req.post_data_json
                    assert set(payload) == {"panel_presentation"}, payload.keys()
                    res = client.post(target, base_url=ORIGIN, json=payload, headers={"Origin": ORIGIN})
                    saves.append(res.status_code)
                else:
                    route.fulfill(status=503, json={"ok": False, "message": "Fixture rejects nonappearance mutation"})
                    return
                route.fulfill(status=res.status_code, content_type=res.content_type, body=res.get_data())
            context.route("**/*", route_request)
            page = context.new_page()
            page.on("pageerror", lambda error: errors.append(str(error)))

            def capture(name, mode, width, checks):
                target = args.output / f"{name}-{mode}-{width}.png"
                page.screenshot(path=str(target), full_page=True, animations="disabled")
                report["captures"].append({"page": name, "theme": mode, "width": width,
                    "file": target.name, "sha256": hashlib.sha256(target.read_bytes()).hexdigest(),
                    "computed_contrast": checks})

            if args.component == "PiSD":
                before = client.get("/api/settings", base_url=ORIGIN).get_json()["settings"]
                for mode, expected in (("light", "rgb(244, 246, 250)"), ("dark", "rgb(20, 23, 28)")):
                    page.goto(ORIGIN + "/panel-presentation")
                    expect(page.locator("#ppTheme")).to_have_value(before["panel_presentation"]["theme"] if not saves else ("light" if mode == "dark" else "dark"))
                    expect(page.locator("#ppButtonScale")).to_have_value(str(before["panel_presentation"]["buttonScale"]))
                    expect(page.locator("#ppPanelPadding")).to_have_value(str(before["panel_presentation"]["panelPadding"]))
                    # Disable auto-save via the real control, then save exactly once.
                    if page.locator("#ppAutoSave").is_checked():
                        page.locator("#ppAutoSave").uncheck()
                    page.locator("#ppTheme").select_option(mode)
                    page.locator("#ppSave").click()
                    expect(page.locator("#ppSavedState")).to_have_text("saved backend", timeout=8000)
                    after = client.get("/api/settings", base_url=ORIGIN).get_json()["settings"]
                    assert after["panel_presentation"]["theme"] == mode
                    assert after["manual_drive"] == before["manual_drive"]
                    for key, value in before["panel_presentation"].items():
                        if key not in ("theme", "autoSave"):
                            assert after["panel_presentation"][key] == value, key
                    persisted = json.loads((Path(tmp) / "runtime.json").read_text())
                    assert persisted["panel_presentation"]["theme"] == mode
                    # Reopen the confirmed theme before exercising its safe action feedback.
                    page.reload()
                    expect(page.locator("body")).to_have_attribute("data-pisd-theme", mode)
                    report.setdefault("local_typography", []).append({"theme": mode, "faces": check_local_typography(page, ".pp-range-value", ".pp-console")})
                    grouping = page.locator('#panelPresentationControls .pp-control-grid label:has(input[name$="Weight"])')
                    assert grouping.count() > 0
                    expect(grouping.first).to_have_css("border-top-width", "0px")
                    expect(grouping.first).to_have_css("background-color", "rgba(0, 0, 0, 0)")
                    expect(grouping.first.locator("input")).to_be_visible()
                    report.setdefault("borderless_groups", []).append({"theme": mode, "groups": grouping.count(), "borderless": True})
                    save_count = len(saves)
                    feedback = check_action_feedback(page, "#ppApply")
                    assert len(saves) == save_count
                    report.setdefault("action_feedback", []).append({"theme": mode, **feedback})
                    page.set_viewport_size({"width": 390, "height": 844})
                    expect(page.locator(".pp-control-grid")).to_have_css("grid-template-columns", re.compile(r"^[\d.]+px$"))
                    report.setdefault("narrow_targets", []).append({"theme": mode, "boxes": check_narrow_targets(page, ("#ppReset", "#ppApply", "#ppSave"))})
                    assert len(saves) == save_count
                    capture("presentation-targets", mode, 390, {"body": inspect(page, "body")})
                    page.set_viewport_size({"width": 1440, "height": 900})
                    report["persistence"].append({"theme": mode, "actual_backend_readback": True,
                                                  "persisted_json": True, "unrelated_manual_settings": True})
                    for width, height in ((1440, 900), (390, 844)):
                        page.set_viewport_size({"width": width, "height": height})
                        for name, route, stop, primary, preview, opener in PAGES["PiSD"]:
                            page.goto(ORIGIN + route, wait_until="domcontentloaded")
                            expect(page.locator("body")).to_have_attribute("data-pisd-theme", mode)
                            expect(page.locator("body")).to_have_css("background-color", expected)
                            checks = {"body": inspect(page, "body")}
                            if stop:
                                checks["stop"] = inspect(page, stop)
                            if page.locator("#aiDownloadZip").count() and page.locator("#aiDownloadZip").is_visible():
                                checks["disabled_action"] = check_disabled_control(
                                    page, "#aiDownloadZip",
                                    "rgb(231, 235, 241)" if mode == "light" else "rgb(41, 47, 57)",
                                    "rgb(86, 97, 113)" if mode == "light" else "rgb(165, 175, 191)")
                            capture(name, mode, width, checks)
                    # Preserve all original captures; add static synthetic scene evidence.
                    for width, height in ((1440, 900), (768, 1024), (390, 844), (844, 390)):
                        page.set_viewport_size({"width": width, "height": height})
                        for name, route, stop, frame, arm in (
                            ("manual", "/manual-drive", "#mdrvStopTop", "#mdrvPreviewFrame", "#mdrvArm"),
                            ("ai", "/ai-mode", "#aiStopAll", "#aiPreviewFrame", "#aiEnableMotor"),
                        ):
                            page.goto(ORIGIN + route, wait_until="domcontentloaded")
                            expect(page.locator("body")).to_have_attribute("data-pisd-theme", mode)
                            toggle = page.locator("#drivingCockpitToggle")
                            expect(toggle).to_have_attribute("aria-pressed", "false")
                            before_arm = page.locator(arm).is_checked()
                            before_saves = len(saves)
                            toggle.click()
                            expect(toggle).to_have_attribute("aria-pressed", "true")
                            expect(page.locator("body")).to_have_attribute("data-pisd-cockpit", "immersive")
                            assert page.locator(arm).is_checked() == before_arm
                            assert len(saves) == before_saves
                            stop_loc = page.locator(stop)
                            stop_loc.click(trial=True)
                            stop_box = stop_loc.bounding_box()
                            assert stop_box and stop_box["y"] >= -1 and stop_box["y"] + stop_box["height"] <= height + 1
                            if width <= 900:
                                assert stop_box["height"] >= 44
                            for scene, fill in (("bright", "#ffffff"), ("dark", "#05080b"), ("complex", "#d3a04b")):
                                geometry = page.locator(frame).evaluate("""async (frame, fill) => {
                                  const image=frame.querySelector('img');
                                  const pattern=fill==='#d3a04b' ? '<path d="M0 0H320V240H0ZM320 240H640V480H320Z" fill="#193c56"/><path d="M0 80H640M0 160H640M0 320H640M0 400H640" stroke="#fff" stroke-width="12"/>' : '';
                                  const svg='<svg xmlns="http://www.w3.org/2000/svg" width="640" height="480"><rect width="640" height="480" fill="'+fill+'"/>'+pattern+'<path d="M0 480 L320 120 L640 480" fill="none" stroke="#607080" stroke-width="15"/></svg>';
                                  image.src='data:image/svg+xml,'+encodeURIComponent(svg);
                                  await image.decode();
                                  await new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve)));
                                  const rect=el=>{const r=el.getBoundingClientRect();return {x:r.x,y:r.y,width:r.width,height:r.height}};
                                  return {image:rect(image), overlay:rect(frame.querySelector('.mdrv-drive-overlay')),
                                          fit:getComputedStyle(image).objectFit, ratio:image.naturalWidth/image.naturalHeight,
                                          state:frame.dataset.previewState,
                                          backing:getComputedStyle(frame.querySelector('.mdrv-overlay-hud')).backgroundColor,
                                          foreground:getComputedStyle(frame.querySelector('.mdrv-overlay-hud strong')).color,
                                          computedAspect:getComputedStyle(frame).aspectRatio,
                                          ratioHint:frame.style.getPropertyValue("--cockpit-camera-ratio")};
                                }""", fill)
                                # Retain failed geometry/screenshot evidence before asserting.
                                page.locator(frame).scroll_into_view_if_needed()
                                capture(f"cockpit-{name}-{scene}-{height}", mode, width, {"geometry": geometry, "stop": stop_box})
                                assert geometry["fit"] == "contain", geometry
                                assert abs(geometry["image"]["width"] / geometry["image"]["height"] - geometry["ratio"]) < .03, geometry
                                for key in ("x", "y", "width", "height"):
                                    assert abs(geometry["image"][key] - geometry["overlay"][key]) <= 2, geometry
                                assert geometry["backing"] == "rgb(20, 23, 28)", geometry
                                assert contrast(geometry["foreground"], geometry["backing"]) >= 4.5, geometry
                            toggle.click()
                            expect(toggle).to_have_attribute("aria-pressed", "false")
                            assert page.locator("body").get_attribute("data-pisd-cockpit") is None
                            assert page.locator(arm).is_checked() == before_arm
                            assert len(saves) == before_saves
                # Fresh browser context receives theme from the actual settings backend.
                fresh = browser.new_context()
                fresh.route("**/*", route_request)
                fresh_page = fresh.new_page()
                fresh_page.goto(ORIGIN + "/")
                expect(fresh_page.locator("body")).to_have_attribute("data-pisd-theme", "dark")
                fresh.close()
                # An explicit slider edit must still apply, without rewriting
                # other settings. Keep the original all-key checks above.
                page.goto(ORIGIN + "/panel-presentation")
                expect(page.locator("#ppSavedState")).not_to_have_text("saving")
                expect(page.locator("#ppAutoSave")).not_to_be_checked()
                page.locator("#ppButtonScale").fill("1.07")
                page.locator("#ppSave").click()
                expect(page.locator("#ppSavedState")).to_have_text("saved backend", timeout=8000)
                edited = client.get("/api/settings", base_url=ORIGIN).get_json()["settings"]
                assert edited["panel_presentation"]["buttonScale"] == 1.07
                for key, value in before["panel_presentation"].items():
                    if key not in ("theme", "autoSave", "buttonScale"):
                        assert edited["panel_presentation"][key] == value, key
                assert edited["manual_drive"] == before["manual_drive"]
                report["explicit_slider_edit"] = True
                assert saves and all(code == 200 for code in saves), saves
                report["save_http_codes"] = saves
            else:
                page.goto(ORIGIN + "/")
                legacy = page.evaluate("""() => {
                    const api=window.PiServerStyle;
                    api.saveCustomOverrides({"--panel-pad":"19px","--accent":"#112233"});
                    return localStorage.getItem("PiServerStyleCustom:v0_3_5");
                }""")
                for mode, expected in (("light", "rgb(244, 246, 250)"), ("obsidian", "rgb(20, 23, 28)")):
                    page.set_viewport_size({"width":1440,"height":900})
                    page.locator("#openStyleSettingsBtn").click()
                    page.locator("#styleThemePreset").select_option(mode)
                    expect(page.locator("body")).to_have_css("background-color", expected)
                    report.setdefault("local_typography", []).append({"theme": mode, "faces": check_local_typography(page, "#styleFontScaleValue", "#styleFontScaleValue")})
                    grouping = page.locator("#styleSettingsModal .style-settings-grid > .style-settings-section")
                    assert grouping.count() == 2
                    for section in grouping.all():
                        expect(section).to_have_css("border-top-width", "0px")
                        expect(section).to_have_css("background-color", "rgba(0, 0, 0, 0)")
                        expect(section).to_be_visible()
                    report.setdefault("borderless_groups", []).append({"theme": mode, "groups": grouping.count(), "borderless": True})
                    capture("style-dialog-preview", mode, 1440, {"body": inspect(page, "body")})
                    page.set_viewport_size({"width": 390, "height": 844})
                    expect(page.locator(".style-setting-row-range").first).to_have_css("grid-template-columns", re.compile(r"^[\d.]+px [\d.]+px$"))
                    report.setdefault("narrow_targets", []).append({"theme": mode, "boxes": check_narrow_targets(page, ("#saveStyleSettingsBtn", "#resetStyleSettingsBtn", "#closeStyleSettingsBtn"))})
                    expect(page.locator("#styleSettingsModal")).to_be_visible()
                    capture("style-dialog-targets", mode, 390, {"body": inspect(page, "body")})
                    page.set_viewport_size({"width": 1440, "height": 900})
                    page.keyboard.press("Escape")
                    expect(page.locator("#styleSettingsModal")).to_be_hidden()
                    assert page.evaluate("() => localStorage.getItem('PiServerTheme:v1')") != mode
                    page.locator("#openStyleSettingsBtn").click()
                    page.locator("#styleThemePreset").select_option(mode)
                    page.locator("#saveStyleSettingsBtn").click()
                    expect(page.locator("#styleSettingsModal")).to_be_hidden()
                    page.reload()
                    expect(page.locator("html")).to_have_attribute("data-pidrive-theme", mode)
                    expect(page.locator("body")).to_have_css("background-color", expected)
                    page.keyboard.press("Tab")
                    focus_target = page.locator("#openStyleSettingsBtn")
                    focus_target.focus()
                    expect(focus_target).to_have_css("outline-width", "3px")
                    expect(focus_target).to_have_css("outline-style", "solid")
                    expect(focus_target).to_have_css("outline-color", "rgb(49, 95, 209)" if mode == "light" else "rgb(251, 191, 36)")
                    feedback = check_action_feedback(page, "#openStyleSettingsBtn")
                    expect(page.locator("#styleSettingsModal")).to_be_hidden()
                    report.setdefault("action_feedback", []).append({"theme": mode, **feedback})
                    disabled = check_disabled_control(
                        page, "#openStyleSettingsBtn",
                        "rgb(231, 235, 241)" if mode == "light" else "rgb(41, 47, 57)",
                        "rgb(86, 97, 113)" if mode == "light" else "rgb(165, 175, 191)")
                    report.setdefault("disabled_controls", []).append({"theme": mode, **disabled})
                    assert page.evaluate("() => localStorage.getItem('PiServerStyleCustom:v0_3_5')") == legacy
                    assert page.evaluate("() => window.PiServerStyle.getResolvedVars()['--panel-pad']") == "19px"
                    report["persistence"].append({"theme": mode, "reload": True, "legacy_settings_preserved": True})
                    for width, height in ((1440,900),(390,844)):
                        page.set_viewport_size({"width":width,"height":height})
                        for tab in ("manual","training","auto","camera","motor"):
                            selected = page.locator(f'#pageTabs [data-page="{tab}"]')
                            selected.click()
                            expect(selected).to_have_attribute("aria-pressed", "true")
                            expect(selected).to_have_css("background-color", "rgb(49, 95, 209)" if mode == "light" else "rgb(100, 149, 255)")
                            checks = {"body": inspect(page, "body"),
                                      "selected_tab": inspect(page, f'#pageTabs [data-page="{tab}"]'),
                                      "stop": inspect(page, "#estopToggle")}
                            capture(tab, mode, width, checks)
                assert page.evaluate("() => localStorage.getItem('PiServerStyleCustom:v0_3_5')") == legacy
            assert not errors, errors
            report["page_errors"] = errors
            context.close()
            browser.close()
    finally:
        (args.output / "manifest.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"{args.component}: {len(report['captures'])} rendered theme captures, persistence {report['persistence']}")


if __name__ == "__main__":
    main()
