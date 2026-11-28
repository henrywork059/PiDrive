"""Saved environments, actual virtual camera and isolated diagnostic API/browser."""
import hashlib
import json
import os
import tempfile
import threading
import time
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import numpy as np
import requests
from playwright.sync_api import sync_playwright, expect
from werkzeug.serving import make_server
from test_scenarios import ROOT, PiSDRuntime, create_control_app, free_port, wait, zero

PROFILE={"name":"Qualification S","segments":[{"length_m":20,"curvature":0},{"length_m":20,"curvature":.08},{"length_m":20,"curvature":-.08}],"road_width_m":1.2,"markings":"solid","edge_lines":False,"lighting":"night","obstacles":[{"station_m":10,"lateral_m":.25,"kind":"cone"}]}

class EnvironmentDiagnostics(unittest.TestCase):
    def test_saved_environment_and_real_diagnostics(self):
        evidence=Path(os.environ.get("PISD_EMULATOR_EVIDENCE","emulator-scenario-evidence"))
        evidence.mkdir(parents=True,exist_ok=True)
        with tempfile.TemporaryDirectory() as temp,patch.dict(os.environ,{"PISD_ACCESS_TOKEN":""}):
            root=Path(temp)
            port,cp=free_port(),free_port()
            while port==cp:cp=free_port()
            runtime=PiSDRuntime(ROOT,workspace=root,port=port,control_port=cp)
            controller=create_control_app(runtime)
            server=make_server("127.0.0.1",cp,controller,threaded=True)
            thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
            url=f"http://127.0.0.1:{cp}"; pisd=f"http://127.0.0.1:{port}"
            def post(path,data,headers=None):
                return requests.post(url+path,json=data,headers=headers or {"Origin":url},timeout=5)
            try:
                self.assertEqual(post("/api/environments/save",{"profile":PROFILE}, {"Origin":"http://evil.test"}).status_code,403)
                for bad in ({**PROFILE,"road_width_m":0},{**PROFILE,"name":"../escape"},{**PROFILE,"segments":[{"length_m":2,"curvature":0}]}):
                    self.assertEqual(post("/api/environments/save",{"profile":bad}).status_code,400)
                with sync_playwright() as pw:
                    browser=pw.chromium.launch()
                    try:
                        page=browser.new_page(viewport={"width":1280,"height":900})
                        errors=[]; page.on("pageerror",lambda error:errors.append(str(error)))
                        page.goto(url+"/environment")
                        expect(page.locator("#message")).to_have_text("Confirmed.")
                        for id,value in (("name",PROFILE["name"]),("width","1.2"),("segments",json.dumps(PROFILE["segments"])),("obstacles",json.dumps(PROFILE["obstacles"]))):
                            page.locator("#"+id).fill(value)
                        page.locator("#markings").select_option("solid")
                        page.locator("#edges").uncheck()
                        page.locator("#lighting").select_option("night")
                        with page.expect_response(lambda r:r.url.endswith("/api/environments/save")) as saved:
                            page.locator("#save").click()
                        self.assertEqual(saved.value.status,200)
                        expect(page.locator("#saved")).to_have_value(PROFILE["name"])
                        page.locator("#apply").click()
                        expect(page.locator("#active")).to_contain_text(PROFILE["name"])
                        self.assertEqual(runtime.engine.snapshot()["track_id"],"custom")
                        self.assertEqual(runtime.engine.snapshot()["road_width_m"],1.2)
                        self.assertGreater(abs(runtime.engine._path.points[-1,0]),1)
                        self.assertEqual(runtime.engine.snapshot()["vehicle"]["cross_track_m"],0)
                        path_points=runtime.engine._path.points.copy()
                        fresh=PiSDRuntime(ROOT,workspace=root,port=port,control_port=cp)
                        self.assertEqual(fresh.environments()["profiles"],[PROFILE])
                        fresh.select_environment(PROFILE["name"])
                        np.testing.assert_array_equal(path_points,fresh.engine._path.points)
                        settings=SimpleNamespace(width=320,height=180,brightness=0,contrast=1,saturation=1,hflip=False,vflip=False)
                        night=runtime.render_frame(settings)
                        fresh.engine.configure_environment({**PROFILE,"lighting":"day"})
                        day=fresh.render_frame(settings)
                        self.assertLess(float(night[40:].mean()),float(day[40:].mean())*.5)
                        from PIL import Image
                        for name,frame in (("environment-night",night),("environment-day",day)):
                            Image.fromarray(frame[:,:,::-1]).save(evidence/(name+".png"))
                        self.assertEqual(post("/api/environments/save",{"profile":PROFILE}).status_code,400)
                        page.screenshot(path=str(evidence/"environment-editor.png"),full_page=True)
                        runtime.start()
                        self.assertEqual(post("/api/environments/select",{"name":None}).status_code,400)
                        camera=runtime._app.config["pisd_services"]["camera"]
                        wait(lambda:camera.get_jpeg_frame())
                        self.assertTrue(runtime._app.config["pisd_services"]["recording"].source_metadata["environment"]["name"]==PROFILE["name"])
                        settings_response=requests.get(pisd+"/api/status?secret=do-not-retain",timeout=5)
                        self.assertEqual(settings_response.status_code,200)
                        denied=requests.post(pisd+"/api/control/manual",json={"throttle":.4},headers={"Origin":"http://evil.test"},timeout=5)
                        self.assertEqual(denied.status_code,403)
                        self.assertTrue(zero(runtime))
                        requests.get(pisd+"/api/camera/fps-stats",timeout=5).raise_for_status()
                        page.goto(url+"/diagnostics")
                        expect(page.locator("#summary")).to_contain_text("API requests")
                        page.locator("#live").check()
                        page.wait_for_timeout(2200)
                        data=requests.get(url+"/api/diagnostics/export",timeout=5)
                        self.assertEqual(data.status_code,200)
                        self.assertIn("attachment",data.headers["Content-Disposition"])
                        report=data.json()
                        self.assertNotIn("do-not-retain",data.text)
                        self.assertNotIn("evil.test",data.text)
                        self.assertTrue(any(r["route"]=="/api/control/manual" and r["status"]==403 for r in report["requests"]))
                        self.assertTrue(any(r["route"]=="/api/status" and r["status"]==200 for r in report["requests"]))
                        self.assertGreaterEqual(len(report["samples"]),2)
                        self.assertTrue(all(s["generation"]==1 for s in report["samples"]))
                        self.assertFalse(errors,errors)
                        page.screenshot(path=str(evidence/"diagnostics.png"),full_page=True)
                        (evidence/"environment-diagnostics.json").write_text(json.dumps({"profile":PROFILE,"diagnostics":report,"night_mean":float(night[40:].mean()),"day_mean":float(day[40:].mean()),"geometry_sha256":hashlib.sha256(path_points.tobytes()).hexdigest(),"browser_errors":errors},indent=2))
                        runtime.stop()
                        runtime.update_simulation_settings({"max_speed_mps":.8})
                        self.assertEqual(runtime.engine.snapshot()["track_id"],"custom")
                        self.assertEqual(runtime.engine.snapshot()["road_width_m"],1.2)
                        runtime.select_environment(None)
                        self.assertEqual(runtime.engine.snapshot()["track_id"],"straight")
                    finally:browser.close()
                # Corrupt saved file is preserved rather than silently replaced.
                file=root/"config"/"emulator_environments.json"
                file.write_text("invalid")
                self.assertEqual(post("/api/environments/save",{"profile":PROFILE,"replace":True}).status_code,400)
                self.assertEqual(file.read_text(),"invalid")
            finally:
                runtime.close();server.shutdown();server.server_close();thread.join(timeout=2)

if __name__=="__main__":unittest.main(verbosity=2)
