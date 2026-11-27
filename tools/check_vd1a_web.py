"""Actual templates in Chromium using isolated hardware-free Flask fixtures.
Only the explicit PiSD presentation-save POST reaches a disposable backend.
"""
import argparse
from contextlib import ExitStack
import hashlib
import json
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
                            capture(name, mode, width, checks)
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
                    capture("style-dialog-preview", mode, 1440, {"body": inspect(page, "body")})
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
