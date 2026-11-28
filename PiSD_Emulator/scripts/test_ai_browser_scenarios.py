"""Real AI page, real recording download, relocated piTrainer import and fault recovery."""
import hashlib
import io
import json
import os
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path
from urllib.parse import urlencode
from unittest.mock import patch

from test_scenarios import ROOT, PiSDRuntime, create_control_app, free_port, wait, zero
from playwright.sync_api import sync_playwright, expect
from PIL import Image

sys.path.insert(0, str(ROOT / "piTrainer"))
from piTrainer.services.data.session_service import list_sessions
from piTrainer.services.data.record_loader_service import load_records_dataframe

def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

class AIBrowserScenario(unittest.TestCase):
    def test_actual_ai_page_and_relocated_trainer_import(self):
        import tensorflow as tf
        import numpy as np
        evidence = Path(os.environ.get("PISD_EMULATOR_EVIDENCE", "emulator-scenario-evidence")).resolve()
        evidence.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory() as temp, patch.dict(os.environ, {"PISD_ACCESS_TOKEN": ""}):
            workspace = Path(temp) / "workspace"
            (workspace / "models").mkdir(parents=True)
            inputs = tf.keras.Input((32,32,3))
            x = tf.keras.layers.GlobalAveragePooling2D()(inputs)
            outputs = tf.keras.layers.Dense(2, kernel_initializer="zeros",
                bias_initializer=tf.keras.initializers.Constant([.05,.8]))(x)
            fixture = workspace / "models" / "browser_fixture.keras"
            tf.keras.Model(inputs, outputs).save(fixture)
            port, control_port = free_port(), free_port()
            while port == control_port:
                control_port = free_port()
            runtime = PiSDRuntime(ROOT, workspace=workspace, port=port, control_port=control_port)
            controller = create_control_app(runtime).test_client()
            origin = f"http://127.0.0.1:{control_port}"
            url = f"http://127.0.0.1:{port}"
            screenshots = {}
            def shot(page, name):
                path = evidence / (name + ".png")
                page.screenshot(path=str(path), full_page=True)
                screenshots[name] = digest(path)
            try:
                runtime.start()
                services = runtime._app.config["pisd_services"]
                camera, motor, ai, recorder = (services[k] for k in ("camera","motor","ai_drive","recording"))
                self.assertFalse(motor.hardware_enabled)
                with sync_playwright() as pw:
                    browser = pw.chromium.launch()
                    try:
                        page = browser.new_page(viewport={"width":1440,"height":1000})
                        page_errors = []
                        page.on("pageerror", lambda exc: page_errors.append(str(exc)))
                        page.goto(url + "/ai-mode")
                        expect(page.locator("#aiModeShell")).to_be_visible()
                        expect(page.locator("#aiModelSelect option[value='browser_fixture.keras']")).to_have_count(1, timeout=15000)
                        page.locator("#aiModelSelect").select_option("browser_fixture.keras")
                        with page.expect_response(lambda res: res.url.endswith("/api/ai/load-model") and res.request.method=="POST", timeout=30000) as loaded:
                            page.locator("#aiLoadModel").click()
                        self.assertTrue(loaded.value.json()["ok"])
                        wait(lambda: ai.status()["model_ready"])
                        page.locator("#aiLive").click()
                        expect(page.locator("#aiPreviewFrame")).to_have_attribute("data-preview-mode", "live", timeout=15000)
                        page.locator("#aiStartPreview").click()
                        wait(lambda: ai.status()["mode"]=="preview" and ai.status()["last_prediction_at_utc"])
                        self.assertTrue(zero(runtime))
                        shot(page, "ai-preview")
                        page.locator("#aiStop").click()
                        wait(lambda: not ai.status()["running"])
                        page.locator("#aiEnableMotor").uncheck()
                        with page.expect_response(lambda res: res.url.endswith("/api/ai/start") and res.request.method=="POST") as rejected:
                            page.locator("#aiStartDrive").click()
                        self.assertFalse(rejected.value.json()["ok"])
                        self.assertTrue(zero(runtime))
                        page.locator("#aiEnableMotor").check()
                        before, seq, _, _ = camera.get_jpeg_frame_info()
                        page.locator("#aiStartDrive").click()
                        wait(lambda: ai.status()["mode"]=="drive" and not zero(runtime))
                        wait(lambda: abs(runtime.engine.snapshot()["vehicle"]["y_m"]) > .05)
                        status = ai.status()
                        self.assertAlmostEqual(status["last_raw_prediction"]["throttle"], .8, places=4)
                        self.assertLessEqual(abs(status["last_safe_command"]["throttle"]),status["safety_layer"]["max_throttle"]+1e-6)
                        self.assertGreater(status["last_frame_seq"],seq)
                        self.assertNotEqual(camera.get_jpeg_frame_info()[0],before)
                        motion = runtime.engine.snapshot()
                        page.locator("#aiRecordToggle").click()
                        wait(lambda: recorder.status()["running"] and recorder.status()["frame_count"] >= 4)
                        session = Path(recorder.status()["active_session"]["session_dir"])
                        shot(page, "ai-recording")
                        page.locator("#aiRecordToggle").click()
                        wait(lambda: not recorder.status()["running"])
                        labels = [json.loads(l) for l in (session/"labels.jsonl").read_text().splitlines()]
                        query = urlencode({"kind":"recording","id":session.relative_to(workspace/"recordings").as_posix()})
                        result = page.request.get(url+"/api/recording/download.zip?"+query)
                        self.assertEqual(result.status,200)
                        downloaded = result.body()
                        archive_path = evidence/"recording.zip"
                        archive_path.write_bytes(downloaded)
                        imported = Path(temp)/"relocated"
                        imported.mkdir()
                        with zipfile.ZipFile(io.BytesIO(downloaded)) as archive:
                            self.assertIsNone(archive.testzip())
                            archive.extractall(imported)
                        names = list_sessions(imported)
                        self.assertEqual(len(names),1,names)
                        frame = load_records_dataframe(imported,names)
                        self.assertEqual(len(frame),len(labels))
                        np.testing.assert_allclose(frame["steering"],[l["steering"] for l in labels],atol=1e-6,rtol=0)
                        np.testing.assert_allclose(frame["throttle"],[l["throttle"] for l in labels],atol=1e-6,rtol=0)
                        self.assertEqual(frame["source_frame_seq"].tolist(),[l["source_frame_seq"] for l in labels])
                        imported_hashes = []
                        for label, image_path in zip(labels,frame["abs_image"]):
                            path = Path(image_path)
                            self.assertTrue(path.is_relative_to(imported))
                            self.assertEqual(digest(path),digest(session/label["frame"]))
                            with Image.open(path) as image:
                                image.verify()
                            imported_hashes.append(digest(path))
                        self.assertEqual(controller.post("/api/scenarios/camera-fault",base_url=origin,json={"active":True}).status_code,200)
                        wait(lambda: ai.status()["camera_frame_fault_latched"] and zero(runtime) and not ai.status()["running"])
                        shot(page,"ai-camera-fault")
                        self.assertEqual(controller.post("/api/scenarios/camera-fault",base_url=origin,json={"active":False}).status_code,200)
                        stale_seq = camera.get_jpeg_frame_info()[1]
                        wait(lambda: camera.get_jpeg_frame_info()[1]>stale_seq)
                        self.assertTrue(ai.status()["camera_frame_fault_latched"])
                        page.once("dialog", lambda dialog: dialog.accept())
                        page.locator("#aiSafetyRearm").click()
                        wait(lambda: not ai.status()["camera_frame_fault_latched"])
                        self.assertTrue(zero(runtime))
                        page.locator("#aiEnableMotor").check()
                        page.locator("#aiStartDrive").click()
                        wait(lambda: ai.status()["mode"]=="drive" and not zero(runtime))
                        page.locator("#aiStopAll").click()
                        wait(lambda: not ai.status()["running"] and zero(runtime))
                        page.wait_for_timeout(1200)
                        self.assertTrue(zero(runtime))
                        shot(page,"ai-stopped")
                        self.assertFalse(page_errors,page_errors)
                        report={"fixture_sha256":digest(fixture),"recording_zip_sha256":digest(archive_path),
                            "source_frame_sequences":[l["source_frame_seq"] for l in labels],
                            "imported_rows":len(frame),"image_sha256":imported_hashes,
                            "raw_prediction":status["last_raw_prediction"],"safe_command":status["last_safe_command"],
                            "motor_output":status["last_motor_output"],"vehicle":motion["vehicle"],
                            "screenshots":screenshots,"page_errors":page_errors,
                            "scope":"deterministic virtual integration, not model accuracy or physical acceptance"}
                        (evidence/"report.json").write_text(json.dumps(report,indent=2),encoding="utf-8")
                    finally:
                        browser.close()
            finally:
                runtime.close()

if __name__ == "__main__":
    unittest.main(verbosity=2)
