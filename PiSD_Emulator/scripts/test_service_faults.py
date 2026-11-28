"""Actual service failure and transport-loss scenarios with reproducible evidence."""
import json
import os
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

import requests
from playwright.sync_api import sync_playwright, expect
from test_scenarios import ROOT, PiSDRuntime, create_control_app, free_port, wait, zero

def observed(runtime):
    s = runtime.status()
    return {"generation":s["generation"], "motor":s["engine"]["motor"],
            "vehicle":s["engine"]["vehicle"], "service_faults":s["service_faults"]}

class ServiceFaultScenarios(unittest.TestCase):
    def test_model_api_gpio_and_browser_transport(self):
        import tensorflow as tf
        evidence = Path(os.environ.get("PISD_EMULATOR_EVIDENCE", "emulator-scenario-evidence"))
        evidence.mkdir(parents=True, exist_ok=True)
        report = {}
        with tempfile.TemporaryDirectory() as temp, patch.dict(os.environ, {"PISD_ACCESS_TOKEN": ""}):
            workspace = Path(temp)
            (workspace/"models").mkdir()
            inputs = tf.keras.Input((32,32,3))
            x = tf.keras.layers.GlobalAveragePooling2D()(inputs)
            output = tf.keras.layers.Dense(2,kernel_initializer="zeros",
                bias_initializer=tf.keras.initializers.Constant([.05,.8]))(x)
            tf.keras.Model(inputs, output).save(workspace/"models"/"fault_fixture.keras")
            port, control_port = free_port(), free_port()
            while port == control_port:
                control_port = free_port()
            runtime = PiSDRuntime(ROOT,workspace=workspace,port=port,control_port=control_port)
            controller = create_control_app(runtime).test_client()
            control_origin = f"http://127.0.0.1:{control_port}"
            origin = f"http://127.0.0.1:{port}"
            def inject(kind, confirm=True, headers=None):
                return controller.post("/api/scenarios/service-fault",base_url=control_origin,
                                       json={"kind":kind,"confirm":confirm},headers=headers or {})
            def post(path,data):
                return requests.post(origin+path,json=data,headers={"Origin":origin},timeout=5)
            def services():
                return runtime._app.config["pisd_services"]
            def restart():
                runtime.stop()
                runtime.start()
                self.assertFalse(runtime.status()["service_faults"]["active"])
                self.assertTrue(zero(runtime))
            def manual():
                response = post("/api/control/manual",{"steering":0,"throttle":.4})
                self.assertEqual(response.status_code,200,response.text)
                result = response.json()
                self.assertTrue(result["ok"],result)
                return result["manual_lease_id"]
            try:
                self.assertEqual(inject("model_inference").status_code,400)
                runtime.start()
                self.assertEqual(inject("unknown").status_code,400)
                self.assertEqual(inject("gpio_left",False).status_code,400)
                self.assertEqual(inject("gpio_left",headers={"Origin":"http://evil.test"}).status_code,403)
                self.assertFalse(runtime.status()["service_faults"]["active"])
                ai = services()["ai_drive"]
                camera = services()["camera"]
                motor = services()["motor"]
                self.assertTrue(ai.load_model("fault_fixture.keras")["ok"])
                self.assertTrue(ai.start(camera,motor,mode="drive",safety_ack=True,enable_motor_output=True)["ok"])
                wait(lambda: not zero(runtime))
                before = observed(runtime)
                start = time.monotonic()
                self.assertEqual(inject("model_inference").status_code,200)
                wait(lambda: zero(runtime) and not ai.status()["running"])
                status = ai.status()
                self.assertIn("Injected emulator model inference failure",status["last_error"])
                self.assertEqual(status["last_raw_prediction"],{"steering":0.0,"throttle":0.0})
                self.assertEqual(status["last_safe_command"],{"steering":0.0,"throttle":0.0})
                self.assertGreaterEqual(runtime.status()["service_faults"]["hits"]["model_inference"],5)
                self.assertFalse(status["camera_frame_fault_latched"])
                report["model"]={"before":before,"after":observed(runtime),"error":status["last_error"],
                                 "elapsed_s":time.monotonic()-start,"raw":status["last_raw_prediction"],
                                 "safe":status["last_safe_command"]}
                self.assertTrue(post("/api/control/stop",{}).json()["ok"])
                restart()
                motor = services()["motor"]
                lease = manual()
                wait(lambda: not zero(runtime))
                self.assertEqual(post("/api/control/heartbeat",{"lease_id":lease}).status_code,200)
                self.assertEqual(inject("heartbeat_api").status_code,200)
                response = post("/api/control/heartbeat",{"lease_id":lease})
                self.assertEqual(response.status_code,503)
                self.assertFalse(response.json()["ok"])
                wait(lambda: zero(runtime) and motor.status()["manual_command_timed_out"])
                report["api"]={"response":response.json(),"http_status":response.status_code,
                               "after":observed(runtime),"lease_expired":motor.status()["manual_command_timed_out"]}
                self.assertTrue(post("/api/control/stop",{}).json()["ok"])
                restart()
                for side in ("left","right"):
                    motor = services()["motor"]
                    manual()
                    wait(lambda: not zero(runtime))
                    before = observed(runtime)
                    self.assertEqual(inject("gpio_"+side).status_code,200)
                    self.assertTrue(zero(runtime))
                    # Actual manual endpoint must report a failed driver write,
                    # not acknowledge an applied nonzero command.
                    refused = post("/api/control/manual",{"steering":0,"throttle":.4})
                    self.assertFalse(refused.json()["ok"],refused.text)
                    self.assertTrue(zero(runtime))
                    self.assertGreater(runtime.status()["service_faults"]["hits"]["gpio_"+side],0)
                    pins = runtime.engine.snapshot()["motor"]["virtual_gpio"]
                    self.assertTrue(all(pin["state"]=="LOW" and pin["duty_cycle_percent"]==0 for pin in pins))
                    self.assertTrue(post("/api/control/stop",{}).json()["ok"])
                    report["gpio_"+side]={"before":before,"after":observed(runtime),
                                         "http_status":refused.status_code,"pins":pins,
                                         "motor_error":motor.status()["last_error"]}
                    restart()
                # Real Chromium transport loss, not an API success stub.
                with sync_playwright() as pw:
                    browser = pw.chromium.launch()
                    try:
                        context = browser.new_context(viewport={"width":1440,"height":1000})
                        page = context.new_page()
                        page.goto(origin+"/manual-drive")
                        expect(page.locator("#manualDriveShell")).to_be_visible()
                        page.locator("#mdrvArm").check()
                        page.locator("#mdrvDragPad").focus()
                        page.keyboard.press("ArrowUp")
                        page.keyboard.press("ArrowUp")
                        wait(lambda: not zero(runtime))
                        before = observed(runtime)
                        started = time.monotonic()
                        context.set_offline(True)
                        rejected = page.evaluate("""async () => {try {await fetch('/api/status', {cache:'no-store'}); return false;} catch (_) {return true;}}""")
                        self.assertTrue(rejected)
                        wait(lambda: zero(runtime))
                        elapsed = time.monotonic()-started
                        context.set_offline(False)
                        page.wait_for_timeout(1200)
                        self.assertTrue(zero(runtime))
                        page.locator("#mdrvStopTop").click()
                        wait(lambda: zero(runtime))
                        page.screenshot(path=str(evidence/"manual-network-recovery.png"),full_page=True)
                        report["network"]={"before":before,"after":observed(runtime),
                                           "offline_fetch_failed":rejected,"elapsed_to_zero_s":elapsed,
                                           "manual_no_automatic_resume":True,
                                           "scope":"browser manual lease only; server-side AI is not a browser lease"}
                    finally:
                        browser.close()
                (evidence/"service-fault-report.json").write_text(json.dumps(report,indent=2),encoding="utf-8")
            finally:
                runtime.close()

if __name__ == "__main__":
    unittest.main(verbosity=2)
