"""Bounded, payload-free API and performance history for the isolated emulator."""
from collections import deque
from datetime import datetime, timezone
import threading
import time

class Diagnostics:
    def __init__(self):
        self._lock = threading.RLock()
        self._requests = deque(maxlen=400)
        self._samples = deque(maxlen=180)
        self._total = 0
        self._last_sample = -1.0
        self._started = time.monotonic()

    def install(self, app, generation):
        from flask import g, request

        @app.before_request
        def measure():
            g.emulator_request_start = time.perf_counter()

        @app.after_request
        def record(response):
            rule = request.url_rule
            # No raw URL, query, credentials, cookies, payload, response body
            # or exception string. Unknown paths are not retained.
            if rule is not None and rule.rule.startswith("/api/"):
                start = getattr(g, "emulator_request_start", None)
                elapsed = round((time.perf_counter()-start)*1000,3) if start is not None else None
                with self._lock:
                    self._total += 1
                    self._requests.append({"sequence":self._total,"generation":generation,
                        "elapsed_s":round(time.monotonic()-self._started,3),
                        "method":request.method,"route":rule.rule,
                        "status":response.status_code,"handler_ms":elapsed})
            return response

    def sample(self, state):
        now = time.monotonic()
        with self._lock:
            if now-self._last_sample >= 0.9:
                self._last_sample=now
                engine=state["engine"]
                self._samples.append({"elapsed_s":round(now-self._started,3),
                    "generation":state["generation"],"running":state["running"],
                    "physics_fps":engine["physics"]["actual_fps"] if state["running"] else 0.0,
                    "speed_mps":engine["vehicle"]["speed_mps"],
                    "left_output":engine["motor"]["left_intended"],
                    "right_output":engine["motor"]["right_intended"],
                    "api_total":self._total})
            return {"schema":1,"exported_utc":datetime.now(timezone.utc).isoformat(),
                    "request_total":self._total,"request_capacity":400,"sample_capacity":180,
                    "requests":list(self._requests),"samples":list(self._samples),
                    "runtime":{"generation":state["generation"],"running":state["running"],
                               "version":state["version"],"track_id":state["engine"]["track_id"],
                               "hardware_enabled":False,"gpio_access":False,
                               "camera_mode":state["camera_input"]["mode"],
                               "motor_disconnected":state["motor_disconnected"],
                               "service_faults":state["service_faults"]},
                    "events":[{"timestamp":e["timestamp"],"level":e["level"]}
                              for e in state["events"]],
                    "scope":"API handler latency excludes body streaming; auth short-circuits may have null timing. Events omit free-text paths and errors. Performance sampled on diagnostics observation."}
