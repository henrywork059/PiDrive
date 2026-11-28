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


def check_flat_readouts(page, selector):
    """Preserve real label/value elements and grid geometry; flatten only chrome."""
    rows = page.locator(selector)
    assert rows.count() > 0, selector
    visible = 0
    for row in rows.all():
        expect(row).to_have_css("background-color", "rgba(0, 0, 0, 0)")
        expect(row).to_have_css("border-radius", "0px")
        expect(row).to_have_css("box-shadow", "none")
        assert row.locator("strong").count() == 1
        if row.is_visible():
            visible += 1
            expect(row.locator("strong")).to_be_visible()
    return {"selector":selector,"count":rows.count(),"visible":visible}


def check_flat_sections(page, selector, heading_selector=None):
    """Inspect actual workspace section chrome without activating controls."""
    sections = page.locator(selector)
    assert sections.count() > 0, selector
    visible = 0
    for section in sections.all():
        expect(section).to_have_css("background-color", "rgba(0, 0, 0, 0)")
        expect(section).to_have_css("border-left-color", "rgba(0, 0, 0, 0)")
        if heading_selector:
            heading = section.locator(heading_selector)
            assert heading.count() == 1
            expect(heading).to_have_css("box-shadow", re.compile(r"0px -1px 0px 0px inset"))
        else:
            expect(section).to_have_css("box-shadow", re.compile(r"0px -1px 0px 0px inset"))
        if section.is_visible():
            visible += 1
            if heading_selector:
                expect(heading).to_be_visible()
            assert section.locator("input,select,button,textarea").count() > 0
    return {"selector":selector,"count":sections.count(),"visible":visible}


def check_density_field(page, selector):
    """Measure an actual control without mutating device settings."""
    field = page.locator(selector).first
    expect(field).to_be_visible()
    field.scroll_into_view_if_needed()
    box = field.bounding_box()
    assert box and box["height"] >= 44 and box["width"] >= 44, (selector, box)
    assert box["x"] >= -1 and box["x"] + box["width"] <= page.viewport_size["width"] + 1, (selector, box)
    assert box["y"] >= -1 and box["y"] + box["height"] <= page.viewport_size["height"] + 1, (selector, box)
    return {"selector":selector, **box}


def check_keyboard_focus(page, selector, *, touch=False):
    """Keyboard modality, no activation of operational controls."""
    control = page.locator(selector).first
    expect(control).to_be_visible()
    control.scroll_into_view_if_needed()
    page.keyboard.press("Tab")
    control.focus()
    assert control.evaluate("el => el.matches(':focus-visible')"), selector
    expect(control).to_have_css("outline-style", "solid")
    details = control.evaluate("""el => {
        const s=getComputedStyle(el), r=el.getBoundingClientRect();
        const hit=document.elementFromPoint(r.x+r.width/2,r.y+r.height/2);
        return {outline:parseFloat(s.outlineWidth),width:r.width,height:r.height,
                visible:!!hit&&(hit===el||el.contains(hit))};
    }""")
    assert details["outline"] >= 2 and details["visible"], (selector,details)
    if touch:
        assert details["width"] >= 44 and details["height"] >= 44, (selector,details)
    return details


def check_selected_cue(locator, selected):
    expect(locator).to_have_attribute("aria-pressed", str(selected).lower())
    expect(locator).to_have_css("text-decoration-line", "underline" if selected else "none")
    return {"selected": selected, "non_color_cue": True}


def check_appearance_controls(page, slider_selector, select_selector):
    """Real keyboard input; restore the draft before existing save gates."""
    slider, select = page.locator(slider_selector), page.locator(select_selector)
    initial = slider.input_value()
    slider.scroll_into_view_if_needed()
    # Establish keyboard modality after the previous pointer interaction.
    page.keyboard.press("Tab")
    slider.focus()
    assert slider.evaluate("el => el.matches(':focus-visible')"), slider_selector
    expect(slider).to_have_css("outline-style", "solid")
    style = slider.evaluate("""el => {
        const s = getComputedStyle(el, '::-webkit-slider-thumb');
        return {appearance:getComputedStyle(el).appearance, type:el.type,
                min:el.min,max:el.max,step:el.step};
    }""")
    assert style["appearance"] == "none" and style["type"] == "range", style
    key = "ArrowLeft" if float(initial) >= float(style["max"]) else "ArrowRight"
    slider.press(key)
    changed = slider.input_value()
    assert abs(abs(float(changed)-float(initial))-float(style["step"])) < 1e-6, (initial, changed, style)
    slider.fill(initial)
    expect(slider).to_have_value(initial)
    for control in (slider, select):
        original = control.evaluate("el => el.disabled")
        try:
            control.evaluate("el => { el.disabled = true; }")
            expect(control).to_be_disabled()
            expect(control).to_have_css("cursor", "not-allowed")
            expect(control).to_have_css("opacity", "1")
        finally:
            control.evaluate("(el,value) => { el.disabled = value; }", original)
    return {"slider":slider_selector,"native_step":style["step"],"restored":True,
            "disabled_checked":True}


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
            # PiServer's actual page buttons send a control envelope. Keep
            # navigation state in this isolated fixture only; no command is
            # forwarded to the backend, and nonzero intent is rejected.
            fixture_page = "manual"
            def route_request(route):
                nonlocal fixture_page
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
                    if args.component == "PiServer" and url.path == "/api/status" and res.status_code == 200:
                        data = res.get_json()
                        data["current_page"] = fixture_page
                        route.fulfill(status=200, json=data)
                        return
                elif args.component == "PiServer" and req.method == "POST" and url.path == "/api/control":
                    payload = req.post_data_json
                    requested = payload.get("current_page")
                    if (requested in {"manual","training","auto","camera","motor"}
                            and float(payload.get("steering",0)) == 0
                            and float(payload.get("throttle",0)) == 0
                            and set(payload) <= {"current_page","steering","throttle","max_throttle","steer_mix","steer_bias","algorithm"}
                            and payload.get("algorithm","manual") == "manual"):
                        fixture_page = requested
                        route.fulfill(status=200, json={"ok":True,"fixture_navigation_only":True})
                    else:
                        route.fulfill(status=503, json={"ok":False,"message":"Fixture rejects actuator mutation"})
                    return
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
                    report.setdefault("appearance_controls", []).append({"theme":mode, **check_appearance_controls(page,"#ppButtonScale","#ppDensity")})
                    expect(page.locator("#ppAutoSave")).not_to_be_checked()
                    assert len(saves) == save_count
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
                            if name == "manual":
                                expect(page.get_by_role("group", name="Live runtime signals and intended motor output")).to_be_visible()
                                expect(page.locator("#mdrvMotorOut")).to_have_css("white-space", "normal")
                                expect(page.locator("#mdrvMotorOut")).to_have_css("font-variant-numeric", "tabular-nums")
                                checks["status_inspector"] = {"intended": page.locator("#mdrvMotorOut").inner_text(),
                                                              "authorization": page.locator("#mdrvReadyMotor").inner_text()}
                            elif name == "ai":
                                expect(page.locator('.ai-readout-grid[aria-label="Selected model and runtime inspector"]')).to_be_visible()
                                expect(page.locator("#aiSafeSteering")).to_have_css("font-variant-numeric", "tabular-nums")
                                checks["status_inspector"] = {"model": page.locator("#aiRawSteering").inner_text(),
                                                              "safe": page.locator("#aiSafeSteering").inner_text()}
                            if stop:
                                checks["stop"] = inspect(page, stop)
                            if page.locator("#aiDownloadZip").count() and page.locator("#aiDownloadZip").is_visible():
                                checks["disabled_action"] = check_disabled_control(
                                    page, "#aiDownloadZip",
                                    "rgb(231, 235, 241)" if mode == "light" else "rgb(41, 47, 57)",
                                    "rgb(86, 97, 113)" if mode == "light" else "rgb(165, 175, 191)")
                            if page.locator("#mdrvFileSummary").count():
                                checks["flat_metadata"] = check_flat_readouts(page,"#mdrvFileSummary > div")
                            if page.locator("#aiFileSummary").count():
                                checks["flat_metadata"] = check_flat_readouts(page,"#aiFileSummary > div")
                            if name == "settings":
                                checks["flat_sections"] = check_flat_sections(page,
                                    "#settingsPanelPresentationPanel,#settingsCameraPanel,#settingsAISettingsPanel", ".st-card-head")
                            elif name in ("manual","ai"):
                                checks["flat_sections"] = check_flat_sections(page,
                                    "#manualDriveFilesPanel" if name == "manual" else "#aiFilesPanel", ".mdrv-panel-head")
                            if name == "settings" and width == 390:
                                checks["density_fields"] = [
                                    check_density_field(page, '#stPresentationForm select[name="density"]'),
                                    check_density_field(page, '#stPresentationForm input[name="fontScale"]'),
                                ]
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
                            check_selected_cue(toggle, False)
                            if width == 1440:
                                report.setdefault("cockpit_action_feedback", []).append({"theme":mode,"page":name, **check_action_feedback(page,"#drivingCockpitToggle")})
                                check_selected_cue(toggle, False)
                            before_arm = page.locator(arm).is_checked()
                            before_saves = len(saves)
                            # Manual cockpit changes presentation only. Track the same
                            # controls and normal grid across the reversible switch.
                            normal_grid = None
                            original_source = None
                            if name == "manual":
                                # Match image state on both sides of the layout comparison.
                                original_source = page.locator("#mdrvPreview").get_attribute("src")
                                page.evaluate("""async () => {
                                    // Join the existing startup settings read (or explicitly
                                    // synchronize through the public read-only loader).
                                    // The cached theme alone does not prove weights are applied.
                                    await window.PiSDPanelPresentation.loadFromBackend();
                                    await document.fonts.ready;
                                    await document.getElementById('mdrvPreview').decode();
                                    await new Promise(r=>requestAnimationFrame(()=>requestAnimationFrame(r)));
                                }""")
                                normal_grid = page.locator("#manualDriveShell").evaluate("el => {const s=getComputedStyle(el); return {columns:s.gridTemplateColumns,areas:s.gridTemplateAreas,width:el.clientWidth,controlWeight:s.getPropertyValue('--pisd-control-h-span').trim(),ideal:s.getPropertyValue('--pisd-layout-control-ideal').trim()}}")
                                page.evaluate("""() => {
                                    window.__vd1wControls = ['mdrvStopTop','mdrvStopPad','mdrvStopBig',
                                        'mdrvArm','mdrvDragPad','mdrvSpeed','mdrvLiveCamera','mdrvCaptureFrame',
                                        'mdrvRecordToggle','mdrvOverlayToggle'].map(id => document.getElementById(id));
                                }""")
                            if name == "ai":
                                ai_selection = page.locator("#aiModelSelect").input_value()
                                ai_tabs = page.locator("#aiSafetyPanel [role=tab]").evaluate_all("els => els.map(e=>e.getAttribute('aria-selected'))")
                                page.evaluate("""() => {
                                    window.__vd1xControls = ['aiStopAll','aiEnableMotor','aiModelSelect',
                                        'aiLoadModel','aiStartPreview','aiStartDrive','aiStop','aiSafetyRearm',
                                        'aiLive','aiSaveSnapshot','aiRecordToggle','aiStopCamera',
                                        'aiManualDriveTab','aiAssistTab','aiCorrectionTab','aiLimiterTab'].map(id=>document.getElementById(id));
                                }""")
                            # Icon is decorative; the same text-labelled native toggle remains.
                            assert toggle.inner_text().strip() == "Cockpit view"
                            assert toggle.evaluate("el => getComputedStyle(el,'::before').maskImage").startswith('url("data:image/svg+xml,')
                            toggle.click()
                            check_selected_cue(toggle, True)
                            expect(page.locator("body")).to_have_attribute("data-pisd-cockpit", "immersive")
                            assert page.locator(arm).is_checked() == before_arm
                            assert len(saves) == before_saves
                            stop_loc = page.locator(stop)
                            stop_loc.click(trial=True)
                            report.setdefault("cockpit_keyboard_focus", []).append({"theme":mode,"page":name,"width":width,
                                "stop":check_keyboard_focus(page,stop,touch=width<=900)})
                            stop_box = stop_loc.bounding_box()
                            assert stop_box and stop_box["y"] >= -1 and stop_box["y"] + stop_box["height"] <= height + 1
                            if width <= 900:
                                assert stop_box["height"] >= 44
                            if name == "manual":
                                camera = page.locator("#manualDriveCameraPanel")
                                expect(camera).to_have_css("align-self", "start")
                                row = camera.locator(".mdrv-preview-top-actions")
                                expect(row).to_have_css("flex-wrap", "wrap")
                                actions = []
                                for control in row.locator("button").all():
                                    expect(control).to_be_visible()
                                    box = control.bounding_box()
                                    assert box and box["width"] > 0 and box["height"] > 0
                                    if width <= 900:
                                        assert box["width"] >= 44 and box["height"] >= 44, box
                                    actions.append(box)
                                assert len(actions) == 3
                                for i, a in enumerate(actions):
                                    for b in actions[i+1:]:
                                        assert (a["x"]+a["width"] <= b["x"]+1 or b["x"]+b["width"] <= a["x"]+1
                                                or a["y"]+a["height"] <= b["y"]+1 or b["y"]+b["height"] <= a["y"]+1), (a,b)
                                assert page.evaluate("() => window.__vd1wControls.every(el => el && document.getElementById(el.id) === el)")
                                report.setdefault("manual_cockpit_controls", []).append({"theme":mode,"width":width,"height":height,"actions":actions,"same_controls":True})
                            if name == "ai":
                                expect(page.locator("#aiPreviewPanel")).to_have_css("align-self", "start")
                                expect(page.locator("#aiPreviewPanel .ai-preview-run-actions")).to_have_css("flex-wrap", "wrap")
                                controls = []
                                for control in page.locator("#aiPreviewPanel .ai-preview-run-actions button").all():
                                    if not control.is_visible():
                                        continue
                                    box = control.bounding_box()
                                    assert box and box["width"] > 0 and box["height"] > 0, box
                                    if width <= 900:
                                        assert box["width"] >= 44 and box["height"] >= 44, box
                                    controls.append(box)
                                assert len(controls) >= 3
                                for i, a in enumerate(controls):
                                    for b in controls[i+1:]:
                                        assert (a["x"]+a["width"] <= b["x"]+1 or b["x"]+b["width"] <= a["x"]+1
                                                or a["y"]+a["height"] <= b["y"]+1 or b["y"]+b["height"] <= a["y"]+1), (a,b)
                                assert page.locator("#aiModelSelect").input_value() == ai_selection
                                assert page.locator("#aiSafetyPanel [role=tab]").evaluate_all("els => els.map(e=>e.getAttribute('aria-selected'))") == ai_tabs
                                assert page.evaluate("() => window.__vd1xControls.every(e=>e && document.getElementById(e.id)===e)")
                                report.setdefault("ai_cockpit_controls", []).append({"theme":mode,"width":width,"height":height,"actions":controls,"same_controls":True})
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
                                expect(page.locator(frame+" .mdrv-overlay-meter strong").first).to_have_css("font-variant-numeric", "tabular-nums")
                            if name == "manual":
                                await_source = page.locator("#mdrvPreview")
                                await_source.evaluate("""async (el,src) => {
                                    el.src = src;
                                    await el.decode();
                                    await new Promise(r=>requestAnimationFrame(()=>requestAnimationFrame(r)));
                                }""", original_source)
                            toggle.click()
                            check_selected_cue(toggle, False)
                            assert page.locator("body").get_attribute("data-pisd-cockpit") is None
                            if name == "manual":
                                page.evaluate("() => new Promise(r=>requestAnimationFrame(()=>requestAnimationFrame(r)))")
                                restored = page.locator("#manualDriveShell").evaluate("el => {const s=getComputedStyle(el); return {columns:s.gridTemplateColumns,areas:s.gridTemplateAreas,width:el.clientWidth,controlWeight:s.getPropertyValue('--pisd-control-h-span').trim(),ideal:s.getPropertyValue('--pisd-layout-control-ideal').trim()}}")
                                report.setdefault("manual_restored_grid", []).append({"theme":mode,"width":width,"before":normal_grid,"after":restored})
                                assert restored == normal_grid, (normal_grid, restored)
                                assert page.evaluate("() => window.__vd1wControls.every(el => el && document.getElementById(el.id) === el)")
                            else:
                                assert page.locator("#aiModelSelect").input_value() == ai_selection
                                assert page.locator("#aiSafetyPanel [role=tab]").evaluate_all("els => els.map(e=>e.getAttribute('aria-selected'))") == ai_tabs
                                assert page.evaluate("() => window.__vd1xControls.every(e=>e && document.getElementById(e.id)===e)")
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
                    report.setdefault("appearance_controls", []).append({"theme":mode, **check_appearance_controls(page,"#styleFontScale","#styleThemePreset")})
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
                    assert page.locator("#openStyleSettingsBtn").inner_text().strip() == "Style settings"
                    assert page.locator("#openStyleSettingsBtn").evaluate("el => getComputedStyle(el,'::before').maskImage").startswith('url("data:image/svg+xml,')
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
                            check_selected_cue(selected, True)
                            expect(page.locator("body")).to_have_attribute("data-page", tab)
                            if width == 390:
                                report.setdefault("mobile_navigation_focus", []).append({"theme":mode,"tab":tab,
                                    **check_keyboard_focus(page,f'#pageTabs [data-page="{tab}"]',touch=True)})
                            for other in page.locator('#pageTabs .tab-btn[aria-pressed="false"]').all():
                                check_selected_cue(other, False)
                            expect(selected).to_have_css("background-color", "rgb(49, 95, 209)" if mode == "light" else "rgb(100, 149, 255)")
                            checks = {"body": inspect(page, "body"),
                                      "selected_tab": inspect(page, f'#pageTabs [data-page="{tab}"]'),
                                      "stop": inspect(page, "#estopToggle")}
                            checks["flat_metadata"] = check_flat_readouts(page,"#workspace div.record-meta-card.priority-low, #workspace div.record-meta-card.priority-medium")
                            checks["flat_secondary_metrics"] = check_flat_readouts(page,"#workspace div.metric-card.priority-low")
                            expect(page.locator("#operatorMetrics")).to_have_attribute("aria-label", "Runtime status and control outputs")
                            expect(page.locator("#metricManual")).to_have_css("font-variant-numeric", "tabular-nums")
                            expect(page.locator("#metricApplied")).to_have_css("white-space", "normal")
                            checks["status_inspector"] = {"target":page.locator("#metricManual").inner_text(),
                                                          "applied":page.locator("#metricApplied").inner_text()}
                            checks["flat_sections"] = check_flat_sections(page,
                                '#workspace .dock-panel:is([data-panel="model"],[data-panel="sessions"],[data-panel="camera"],[data-panel="motor"]) .panel-section:not(.panel-section-strong):not(.panel-section-footer)')
                            if width == 390 and tab in ("camera","motor"):
                                checks["density_fields"] = [check_density_field(page,
                                    "#cameraResolutionPreset" if tab == "camera" else "#steeringDirection")]
                            capture(tab, mode, width, checks)
                    # Camera cockpit uses an isolated synthetic decoded frame, not a live claim.
                    for width,height in ((1440,900),(768,1024),(390,844),(844,390)):
                        page.set_viewport_size({"width":width,"height":height})
                        page.locator('#pageTabs [data-page="camera"]').click()
                        stop = page.locator("#estopToggle")
                        stop.click(trial=True)
                        toggle = page.locator("#cameraCockpitToggle")
                        before = page.evaluate("() => JSON.stringify(Object.entries(localStorage).sort())")
                        before_stop = stop.get_attribute("aria-pressed")
                        check_selected_cue(toggle, False)
                        if width == 1440:
                            report.setdefault("cockpit_action_feedback", []).append({"theme":mode, **check_action_feedback(page,"#cameraCockpitToggle")})
                            check_selected_cue(toggle, False)
                        toggle.click()
                        check_selected_cue(toggle, True)
                        for scene, iw, ih, fill in (("bright",640,480,"#ffffff"),("dark",1280,720,"#05080b"),("complex",480,640,"#d3a04b")):
                            page.locator("#videoFeed").evaluate("""async (image, [w,h,fill]) => {
                                const svg=`<svg xmlns="http://www.w3.org/2000/svg" width="${w}" height="${h}"><rect width="100%" height="100%" fill="${fill}"/><path d="M0 ${h} L${w/2} ${h/4} L${w} ${h}" fill="none" stroke="#607080" stroke-width="12"/></svg>`;
                                image.src="data:image/svg+xml,"+encodeURIComponent(svg);
                                await image.decode();
                                // Allow the actual source/load/resize callbacks to settle;
                                // keep the original 2px bound, and capture failure if it
                                // never converges. Do not set overlay geometry here.
                                const frame=image.closest('.viewer-frame'), overlay=frame.querySelector('#frameOverlay');
                                const end=performance.now()+1000;
                                do {
                                    await new Promise(r=>requestAnimationFrame(r));
                                    const a=image.getBoundingClientRect(), b=overlay.getBoundingClientRect();
                                    const scale=Math.min(a.width/image.naturalWidth,a.height/image.naturalHeight);
                                    const w=image.naturalWidth*scale,h=image.naturalHeight*scale;
                                    if(frame.dataset.cameraGeometry==='aligned' &&
                                      Math.max(Math.abs(b.width-w),Math.abs(b.height-h),
                                      Math.abs(b.x-a.x-(a.width-w)/2),Math.abs(b.y-a.y-(a.height-h)/2))<=2) break;
                                } while(performance.now()<end);
                            }""", [iw,ih,fill])
                            geometry = page.locator(".viewer-frame").evaluate("""el => {
                                const image=el.querySelector("#videoFeed"), overlay=el.querySelector("#frameOverlay");
                                const a=image.getBoundingClientRect(), b=overlay.getBoundingClientRect();
                                const scale=Math.min(a.width/image.naturalWidth,a.height/image.naturalHeight);
                                const w=image.naturalWidth*scale,h=image.naturalHeight*scale;
                                return {expected:{x:a.x+(a.width-w)/2,y:a.y+(a.height-h)/2,width:w,height:h},actual:{x:b.x,y:b.y,width:b.width,height:b.height},fit:getComputedStyle(image).objectFit,health:el.querySelector("#previewHealth").textContent};
                            }""")
                            capture(f"camera-cockpit-{scene}-{height}",mode,width,{"geometry":geometry})
                            assert geometry["fit"] == "contain", geometry
                            assert max(abs(geometry["expected"][k]-geometry["actual"][k]) for k in geometry["expected"]) <= 2, geometry
                            expect(page.locator("#overlayThrottleValue")).to_have_css("font-variant-numeric", "tabular-nums")
                            health = page.locator("#previewHealth")
                            colors = health.evaluate("el => ({fg:getComputedStyle(el).color,bg:getComputedStyle(el).backgroundColor})")
                            assert contrast(colors["fg"],colors["bg"]) >= 4.5, colors
                        toggle.click()
                        check_selected_cue(toggle, False)
                        assert stop.get_attribute("aria-pressed") == before_stop
                        assert page.evaluate("() => JSON.stringify(Object.entries(localStorage).sort())") == before
                        assert page.locator(".viewer-frame").get_attribute("data-camera-cockpit") is None
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
