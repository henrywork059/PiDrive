"""Instance-local fault hooks for the real PiSD services, never hardware drivers."""
from __future__ import annotations

import threading

class ServiceFaults:
    """Sticky faults per emulator generation; no persisted fault configuration."""
    KINDS = ("model_inference", "heartbeat_api", "gpio_left", "gpio_right")

    def __init__(self):
        self._lock = threading.RLock()
        self._active = set()
        self._counts = {kind: 0 for kind in self.KINDS}

    def activate(self, kind):
        if kind not in self.KINDS:
            raise ValueError("Unknown service fault.")
        with self._lock:
            self._active.add(kind)

    def hit(self, kind):
        with self._lock:
            if kind not in self._active:
                return False
            self._counts[kind] += 1
            return True

    def gpio_active(self):
        with self._lock:
            return bool({"gpio_left", "gpio_right"} & self._active)

    def status(self):
        with self._lock:
            return {"active": sorted(self._active), "hits": dict(self._counts),
                    "recovery": "stop_runtime"}

    def install(self, app):
        from flask import jsonify, request
        services = app.config["pisd_services"]
        ai, motor = services["ai_drive"], services["motor"]
        if motor.hardware_enabled or app.config.get("pisd_runtime_mode") != "emulator":
            raise RuntimeError("Service faults require isolated emulator mode.")
        original_predict = ai._predict_from_jpeg

        def predict(frame):
            if self.hit("model_inference"):
                raise RuntimeError("Injected emulator model inference failure.")
            return original_predict(frame)

        ai._predict_from_jpeg = predict

        def wrap_drivers():
            for side in ("left", "right"):
                driver = getattr(motor, side)
                if driver.hardware_enabled:
                    raise RuntimeError("Cannot wrap physical GPIO.")
                original = driver.set_speed
                def guarded(speed, original=original, kind="gpio_" + side):
                    # Always allow zero/STOP; return the real driver's failure
                    # contract for nonzero simulated PWM writes.
                    if abs(float(speed)) > 1e-6 and self.hit(kind):
                        return False
                    return original(speed)
                driver.set_speed = guarded

        wrap_drivers()
        original_rebuild = motor._rebuild_drivers_locked

        def rebuild():
            original_rebuild()
            wrap_drivers()
        motor._rebuild_drivers_locked = rebuild

        # Registered after PiSD access-control hooks. Auth/origin rejection
        # still wins. Only lease renewals fail; STOP is never intercepted.
        @app.before_request
        def fail_heartbeat():
            if request.method == "POST" and request.path == "/api/control/heartbeat" and self.hit("heartbeat_api"):
                return jsonify(ok=False, code="EMULATOR_HEARTBEAT_FAULT",
                               message="Injected emulator heartbeat API failure."), 503
