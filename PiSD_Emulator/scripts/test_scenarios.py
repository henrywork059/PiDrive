"""Real emulator service integration: Keras, recording, replay and stale-camera latch."""
import io
import json
import os
import socket
import sys
import tempfile
import time
import unittest
import zipfile
from pathlib import Path
from types import SimpleNamespace

os.environ.setdefault("TF_NUM_INTEROP_THREADS", "1")
os.environ.setdefault("TF_NUM_INTRAOP_THREADS", "1")
os.environ.setdefault("OMP_NUM_THREADS", "1")
ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / "PiSD"), str(ROOT / "PiSD_Emulator")]
from PIL import Image
from pisd_emulator.runtime import PiSDRuntime
from pisd_emulator.control_app import create_control_app
from pisd_emulator.replay import ImageReplay, VideoReplay, open_replay

def free_port():
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]

def wait(check, timeout=15):
    end = time.monotonic() + timeout
    while time.monotonic() < end:
        result = check()
        if result:
            return result
        time.sleep(.05)
    raise AssertionError("Expected condition not reached")

def zero(runtime):
    motor = runtime.engine.snapshot()["motor"]
    return abs(motor["left_intended"]) < .001 and abs(motor["right_intended"]) < .001

class ScenarioTests(unittest.TestCase):
    def test_image_order_eof_loop_and_path_boundaries(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            folder = root / "replay" / "frames"
            folder.mkdir(parents=True)
            Image.new("RGB", (80, 60), (255, 0, 0)).save(folder / "02.png")
            Image.new("RGB", (80, 60), (0, 0, 255)).save(folder / "01.png")
            settings = SimpleNamespace(width=80,height=60,brightness=0,contrast=1,saturation=1,hflip=False,vflip=False)
            replay = ImageReplay(root, "replay/frames")
            self.assertEqual(replay.render(settings)[0,0].tolist(), [255,0,0])
            self.assertEqual(replay.render(settings)[0,0].tolist(), [0,0,255])
            with self.assertRaisesRegex(RuntimeError, "exhausted"):
                replay.render(settings)
            replay = ImageReplay(root, "replay/frames", True)
            first = replay.render(settings)
            replay.render(settings)
            self.assertTrue((first == replay.render(settings)).all())
            for invalid in ("../frames", str(folder), "replay/../frames", "config/frames"):
                with self.assertRaises(ValueError):
                    ImageReplay(root, invalid)
            (folder / "labels.jsonl").write_text('{"frame":"../outside.png"}\n', encoding="utf-8")
            with self.assertRaises(ValueError):
                ImageReplay(root, "replay/frames")

    def test_video_sequence_and_motor_disconnect(self):
        import cv2
        import numpy as np
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            folder = root / "replay"
            folder.mkdir()
            path = folder / "clip.avi"
            writer = cv2.VideoWriter(str(path), cv2.VideoWriter_fourcc(*"MJPG"), 10, (80, 60))
            self.assertTrue(writer.isOpened())
            try:
                for color in ((230, 10, 10), (10, 230, 10), (10, 10, 230)):
                    frame = np.zeros((60, 80, 3), np.uint8)
                    frame[:] = color
                    writer.write(frame)
            finally:
                writer.release()
            settings = SimpleNamespace(width=80,height=60,brightness=0,contrast=1,saturation=1,hflip=False,vflip=False)
            replay = open_replay(root, "replay/clip.avi", False)
            self.assertIsInstance(replay, VideoReplay)
            try:
                self.assertEqual(replay.status()["frame_count"], 3)
                for i in range(3):
                    self.assertEqual(int(np.argmax(replay.render(settings)[30,40])), i)
                with self.assertRaisesRegex(RuntimeError, "exhausted"):
                    replay.render(settings)
                self.assertIsNone(replay.capture)
                replay.reset()
                self.assertEqual(int(np.argmax(replay.render(settings)[30,40])), 0)
            finally:
                replay.close()
            loop = open_replay(root, "replay/clip.avi", True)
            try:
                self.assertEqual([int(np.argmax(loop.render(settings)[30,40])) for _ in range(4)], [0,1,2,0])
            finally:
                loop.close()
            for invalid in (str(path), "replay/../clip.avi", "recordings/clip.avi"):
                with self.assertRaises(ValueError):
                    open_replay(root, invalid)
            port, control_port = free_port(), free_port()
            while port == control_port:
                control_port = free_port()
            runtime = PiSDRuntime(ROOT, workspace=root, port=port, control_port=control_port)
            controller = create_control_app(runtime).test_client()
            origin = f"http://127.0.0.1:{control_port}"
            def post(url, data, **kw):
                return controller.post(url, base_url=origin, json=data, **kw)
            try:
                self.assertEqual(post("/api/scenarios/replay", {"source":"replay/clip.avi","loop":True}).status_code, 200)
                runtime.start()
                wait(lambda: runtime.camera_input_status()["delivered"] >= 4)
                services = runtime._app.config["pisd_services"]
                self.assertEqual(services["recording"].source_metadata["replay_media"], "video")
                motor = services["motor"]
                motor.update(steering=0, throttle=.5)
                wait(lambda: not zero(runtime))
                self.assertEqual(post("/api/scenarios/motor-disconnect", {"confirm":False}).status_code, 400)
                self.assertEqual(post("/api/scenarios/motor-disconnect", {"confirm":True}, headers={"Origin":"http://evil.test"}).status_code, 403)
                self.assertEqual(post("/api/scenarios/motor-disconnect", {"confirm":True}).status_code, 200)
                self.assertTrue(zero(runtime))
                for _ in range(3):
                    motor.update(steering=0, throttle=.5)
                    self.assertTrue(zero(runtime))
                self.assertIn("Injected virtual motor disconnect", motor.status()["last_error"])
                wait(lambda: abs(runtime.engine.snapshot()["vehicle"]["speed_mps"]) < .01)
                motor.stop()
                self.assertTrue(runtime.status()["motor_disconnected"])
                runtime.stop()
                self.assertFalse(runtime.status()["motor_disconnected"])
                self.assertIsNone(runtime._replay.capture)
                runtime.start()
                self.assertTrue(zero(runtime))
                self.assertFalse(runtime.status()["motor_disconnected"])
            finally:
                runtime.close()

    def test_real_ai_record_replay_and_camera_fault(self):
        import tensorflow as tf
        import numpy as np
        with tempfile.TemporaryDirectory() as temp:
            workspace = Path(temp)
            port, control_port = free_port(), free_port()
            while port == control_port:
                control_port = free_port()
            runtime = PiSDRuntime(ROOT, workspace=workspace, port=port, control_port=control_port)
            controller = create_control_app(runtime).test_client()
            origin = f"http://127.0.0.1:{control_port}"
            def post(path, data, **kw):
                return controller.post(path, base_url=origin, json=data, **kw)
            try:
                with controller.get("/scenarios", base_url=origin) as response:
                    self.assertEqual(response.status_code, 200)
                self.assertEqual(post("/api/scenarios/camera-fault", {"active": True}).status_code, 400)
                self.assertEqual(post("/api/scenarios/camera-fault", {"active": True}, headers={"Origin":"http://evil.test"}).status_code, 403)
                runtime.start()
                services = runtime._app.config["pisd_services"]
                camera, motor, ai, recorder = (services[k] for k in ("camera","motor","ai_drive","recording"))
                self.assertFalse(motor.hardware_enabled)
                before, seq, _, _ = camera.wait_for_jpeg_frame(timeout=3)
                self.assertTrue(before)
                # Deterministic real Keras fixture exercises model loading and
                # inference, not a trained policy or a model-accuracy claim.
                inputs = tf.keras.Input((32,32,3))
                x = tf.keras.layers.GlobalAveragePooling2D()(inputs)
                output = tf.keras.layers.Dense(2, kernel_initializer="zeros",
                    bias_initializer=tf.keras.initializers.Constant([.05,.8]))(x)
                tf.keras.Model(inputs, output).save(workspace / "models" / "fixture.keras")
                result = ai.load_model("fixture.keras")
                self.assertTrue(result["ok"], result)
                self.assertFalse(ai.start(camera,motor,mode="drive",safety_ack=False)["ok"])
                self.assertTrue(ai.start(camera,motor,mode="drive",safety_ack=True,enable_motor_output=True)["ok"])
                wait(lambda: not zero(runtime))
                wait(lambda: abs(runtime.engine.snapshot()["vehicle"]["y_m"]) > .05)
                status = ai.status()
                self.assertAlmostEqual(status["last_raw_prediction"]["throttle"], .8, places=4)
                self.assertLessEqual(abs(status["last_safe_command"]["throttle"]), status["safety_layer"]["max_throttle"] + 1e-6)
                self.assertGreater(status["last_frame_seq"], seq)
                self.assertNotEqual(camera.get_jpeg_frame_info()[0], before)
                started = recorder.start(camera,motor,label="ai_fixture",fps=5,command_source="ai_safe_command",ai_status_provider=ai.status)
                self.assertTrue(started["ok"], started)
                wait(lambda: recorder.status()["frame_count"] >= 3)
                stopped = recorder.stop()
                self.assertTrue(stopped["ok"], stopped)
                session = Path(stopped["stopped_session"]["session_dir"])
                manifest = json.loads((session/"manifest.json").read_text())
                labels = [json.loads(line) for line in (session/"labels.jsonl").read_text().splitlines()]
                records = [json.loads(line) for line in (session/"records.jsonl").read_text().splitlines()]
                self.assertEqual(manifest["data_source"]["kind"],"synthetic_simulation")
                self.assertEqual(len(labels),len(records))
                self.assertEqual(manifest["frame_count"],len(labels))
                for label, record in zip(labels, records):
                    self.assertEqual(label["source_frame_seq"],record["source_frame_seq"])
                    self.assertEqual(label["control_label_source"], "ai_safe_command")
                    self.assertEqual(label["throttle"],record["throttle"])
                    with Image.open(session/label["frame"]) as image:
                        image.verify()
                err, archive, _ = recorder.build_collection_zip("recording",session.relative_to(workspace/"recordings").as_posix())
                self.assertIsNone(err)
                with zipfile.ZipFile(io.BytesIO(archive)) as zipped:
                    self.assertIsNone(zipped.testzip())
                    self.assertTrue(any(n.endswith("/labels.jsonl") for n in zipped.namelist()))
                self.assertEqual(post("/api/scenarios/replay",{"source":session.relative_to(workspace).as_posix()}).status_code,400)
                self.assertEqual(post("/api/scenarios/camera-fault",{"active":"true"}).status_code,400)
                self.assertEqual(post("/api/scenarios/camera-fault",{"active":True}).status_code,200)
                wait(lambda: ai.status()["camera_frame_fault_latched"] and zero(runtime) and not ai.status()["running"])
                frozen_seq = camera.get_jpeg_frame_info()[1]
                time.sleep(.3)
                self.assertEqual(camera.get_jpeg_frame_info()[1],frozen_seq)
                self.assertFalse(ai.rearm_camera_fault(camera,motor,confirm=True)["ok"])
                self.assertEqual(post("/api/scenarios/camera-fault",{"active":False}).status_code,200)
                wait(lambda: camera.get_jpeg_frame_info()[1] > frozen_seq)
                self.assertTrue(ai.status()["camera_frame_fault_latched"])
                self.assertFalse(ai.start(camera,motor,mode="drive",safety_ack=True)["ok"])
                self.assertTrue(ai.rearm_camera_fault(camera,motor,confirm=True)["ok"])
                self.assertTrue(zero(runtime))
                runtime.stop()
                relative = session.relative_to(workspace).as_posix()
                self.assertEqual(post("/api/scenarios/replay",{"source":relative,"loop":True}).status_code,200)
                runtime.start()
                wait(lambda: runtime.camera_input_status()["delivered"] >= 2)
                self.assertEqual(runtime.camera_input_status()["source"],relative)
                self.assertEqual(runtime._app.config["pisd_services"]["recording"].source_metadata["camera_input"],"replay")
                self.assertTrue(zero(runtime))
                self.assertFalse(runtime.status()["gpio_access"])
            finally:
                runtime.close()

if __name__ == "__main__":
    unittest.main(verbosity=2)
