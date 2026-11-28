"""Actual auxiliary emulator dark/light renders; no motor/lifecycle mutations."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile
import threading
import unittest
from playwright.sync_api import sync_playwright, expect
from werkzeug.serving import make_server
from test_scenarios import ROOT, PiSDRuntime, create_control_app, free_port

class AuxiliaryVisualTests(unittest.TestCase):
    def test_real_pages_themes_and_no_api_echo(self):
        evidence = Path(os.environ.get("VD36_AUX_EVIDENCE", "vd36-auxiliary-evidence"))
        evidence.mkdir(parents=True, exist_ok=True)
        captures = []
        revision = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
        with tempfile.TemporaryDirectory() as temp:
            cp, port = free_port(), free_port()
            while cp == port:
                port = free_port()
            runtime = PiSDRuntime(ROOT, workspace=Path(temp), port=port, control_port=cp)
            controller = create_control_app(runtime)
            server = make_server("127.0.0.1", cp, controller, threaded=True)
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            url = f"http://127.0.0.1:{cp}"
            try:
                with sync_playwright() as pw:
                    browser = pw.chromium.launch()
                    try:
                        workspace = browser.new_page(viewport={"width":1440,"height":900})
                        try:
                            workspace.goto(url)
                            for route in ("environment","scenarios","diagnostics"):
                                expect(workspace.locator(f'nav[aria-label="Emulator tools"] a[href="/{route}"]')).to_be_visible()
                        finally:
                            workspace.close()
                        for width, height in ((390,844),(768,900),(1440,900)):
                            for route, marker, message in (
                                ("environment", "#message", "Confirmed."),
                                ("scenarios", "#feedback", "Status confirmed."),
                                ("diagnostics", "#summary", "API requests"),
                            ):
                                page = browser.new_page(viewport={"width":width,"height":height})
                                errors, requests = [], []
                                page.on("pageerror", lambda error: errors.append(str(error)))
                                page.on("request", lambda request: requests.append(request.url) if "/api/" in request.url else None)
                                try:
                                    page.goto(url+"/"+route)
                                    expect(page.locator(marker)).to_contain_text(message)
                                    page.evaluate("document.fonts.ready")
                                    prior = list(requests)
                                    if route == "scenarios":
                                        expect(page.locator("#fault")).to_be_disabled()
                                    if route == "environment":
                                        expect(page.locator("#save")).to_be_enabled()
                                    for theme in ("dark","light"):
                                        page.locator("#auxiliaryTheme").select_option(theme)
                                        expect(page.locator("html")).to_have_attribute("data-emulator-theme",theme)
                                        info = page.evaluate("""() => {
                                          const style = e=>getComputedStyle(e);
                                          const controls=[...document.querySelectorAll('main button, main select')];
                                          const body=style(document.body);
                                          const a=document.querySelector('main a');
                                          const target=document.querySelector('main textarea');
                                          const canv=document.querySelector('main canvas');
                                          return {width:document.documentElement.scrollWidth,viewport:innerWidth,
                                            background:body.backgroundColor, foreground:body.color,
                                            font:body.fontFamily, localFont:document.fonts.check('13px "PiDrive Inter"'),
                                            anchor:style(a).color, minTarget:Math.min(...controls.map(e=>e.getBoundingClientRect().height)),
                                            textarea:target?{background:style(target).backgroundColor,foreground:style(target).color}:null,
                                            canvas:canv?[...canv.getContext('2d').getImageData(0,0,1,1).data]:null,
                                            disabled:controls.filter(e=>e.disabled).map(e=>({id:e.id,color:style(e).color,background:style(e).backgroundColor}))};
                                        }""")
                                        self.assertLessEqual(info["width"],info["viewport"],(route,theme,width,info))
                                        self.assertIn("PiDrive Inter",info["font"])
                                        self.assertTrue(info["localFont"])
                                        self.assertEqual(info["background"], "rgb(20, 23, 28)" if theme=="dark" else "rgb(244, 246, 250)")
                                        self.assertEqual(info["foreground"], "rgb(237, 241, 247)" if theme=="dark" else "rgb(32, 37, 45)")
                                        if width<=768:self.assertGreaterEqual(info["minTarget"],44)
                                        if info["textarea"]:
                                            self.assertEqual(info["textarea"]["background"],"rgb(25, 29, 36)" if theme=="dark" else "rgb(255, 255, 255)")
                                        if info["canvas"]:
                                            self.assertEqual(info["canvas"],[41,47,57,255] if theme=="dark" else [231,235,241,255])
                                        page.locator("#auxiliaryTheme").focus()
                                        page.keyboard.press("Tab")
                                        focus = page.evaluate("""() => ({tag:document.activeElement.tagName, outline:getComputedStyle(document.activeElement).outlineStyle})""")
                                        self.assertNotEqual(focus["tag"],"BODY")
                                        self.assertNotEqual(focus["outline"],"none")
                                        page.evaluate("document.activeElement.blur()")
                                        name=f"{route}-{theme}-{width}.png"
                                        page.screenshot(path=str(evidence/name),full_page=True)
                                        captures.append({"file":name,"sha256":hashlib.sha256((evidence/name).read_bytes()).hexdigest(),"theme":theme,"viewport":[width,height],"route":route,"computed":info,"keyboard_focus":focus})
                                    self.assertEqual(requests,prior,(route,requests))
                                    self.assertFalse(errors,errors)
                                finally:
                                    page.close()
                    finally:
                        browser.close()
                # Verify physical authority remains disabled using actual controller.
                client = controller.test_client()
                denied = client.get("/api/status")
                self.assertEqual(denied.status_code, 403)
                response = client.get("/api/status", base_url=url)
                self.assertEqual(response.status_code, 200)
                status = response.get_json()
                self.assertIs(status["hardware_enabled"], False)
                self.assertIs(status["gpio_access"], False)
                self.assertIs(status["running"], False)
                self.assertEqual(status["runtime_mode"], "emulator")
            finally:
                runtime.close();server.shutdown();server.server_close();thread.join(timeout=2)
        (evidence/"manifest.json").write_text(json.dumps({"revision":revision,"hardware_enabled":False,"runtime_started":False,"theme_api_echoes":0,"captures":captures},indent=2),encoding="utf-8")

if __name__=="__main__":
    unittest.main(verbosity=2)
