"""Local-only lifecycle manager for the real PiSD Flask application."""

from __future__ import annotations

import json
import os
import sys
import threading
import time
from collections import deque
from pathlib import Path
from typing import Any

from .engine import TRACKS, VehicleEngine
from .renderer import RoadRenderer
from .replay import ImageReplay, VideoReplay, open_replay
from .faults import ServiceFaults
from .environments import EnvironmentStore
from .diagnostics import Diagnostics


def default_workspace() -> Path:
    if os.name == "nt":
        local_app_data = os.environ.get("LOCALAPPDATA")
        root = Path(local_app_data) if local_app_data else Path.home() / "AppData" / "Local"
    else:
        xdg_data_home = os.environ.get("XDG_DATA_HOME")
        root = Path(xdg_data_home) if xdg_data_home else Path.home() / ".local" / "share"
    return root / "PiSD_Emulator" / "workspace"


class PiSDRuntime:
    """Starts the production PiSD app with explicitly injected virtual devices."""

    def __init__(self, repository_root: Path | str, workspace: Path | str | None = None, port: int = 5050, *, control_port: int = 8760):
        self.repository_root = Path(repository_root).resolve()
        self.pisd_root = self.repository_root / "PiSD"
        if self.pisd_root.is_dir() and str(self.pisd_root) not in sys.path:
            sys.path.insert(0, str(self.pisd_root))
        self.workspace = Path(workspace).expanduser().resolve() if workspace else default_workspace()
        self.port = self._validate_port(port)
        self.control_port = self._validate_port(control_port)
        self._generation = 0
        self.engine = VehicleEngine(self._read_emulator_settings())
        self.renderer = RoadRenderer()
        self._environment_store = EnvironmentStore(self.workspace)
        self._active_environment = None
        self._diagnostics = Diagnostics()
        self._lock = threading.RLock()
        self._state_lock = threading.RLock()
        self._camera_input_lock = threading.RLock()
        self._replay: ImageReplay | VideoReplay | None = None
        self._motor_fault_lock = threading.RLock()
        self._motor_disconnected = False
        self._service_faults = ServiceFaults()
        self._camera_fault = False
        self._server: Any | None = None
        self._server_thread: threading.Thread | None = None
        self._app: Any | None = None
        self._running = False
        self._last_error = ""
        self._events: deque[dict[str, Any]] = deque(maxlen=80)
        self._record_event("ready", "PiSD Emulator is idle. Physical GPIO is disabled.")

    def _validate_port(self, port: Any) -> int:
        try:
            value = int(port)
        except (TypeError, ValueError) as exc:
            raise ValueError("PiSD port must be an integer between 1024 and 65535.") from exc
        if not 1024 <= value <= 65535:
            raise ValueError("PiSD port must be between 1024 and 65535.")
        return value

    def _read_emulator_settings(self) -> dict[str, Any]:
        path = self.workspace / "config" / "emulator_settings.json"
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except FileNotFoundError:
            return {}
        except (OSError, json.JSONDecodeError):
            return {}

    def _save_emulator_settings(self, settings: dict[str, Any]) -> None:
        path = self.workspace / "config" / "emulator_settings.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        temp = path.with_suffix(".tmp")
        temp.write_text(json.dumps(settings, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        temp.replace(path)

    def _record_event(self, level: str, message: str) -> None:
        with self._state_lock:
            self._events.append({"timestamp": time.strftime("%H:%M:%S"), "level": level, "message": str(message)})

    def _load_pisd_app_factory(self):
        if not self.pisd_root.is_dir() or not (self.pisd_root / "PiSD.py").is_file():
            raise FileNotFoundError(f"PiSD source was not found at {self.pisd_root}.")
        path_text = str(self.pisd_root)
        if path_text not in sys.path:
            sys.path.insert(0, path_text)
        loaded = sys.modules.get("pisd")
        if loaded is not None:
            loaded_path = Path(getattr(loaded, "__file__", "")).resolve()
            if self.pisd_root not in loaded_path.parents:
                raise RuntimeError(f"A different 'pisd' package is already loaded from {loaded_path}.")
        from pisd.app import create_app

        return create_app

    def start(self, port: Any | None = None) -> dict[str, Any]:
        with self._lock:
            if self._running:
                return self.status()
            selected_port = self._validate_port(port if port is not None else self.port)
            if selected_port == self.control_port:
                raise ValueError("PiSD and emulator control ports must differ.")
            self.workspace.mkdir(parents=True, exist_ok=True)
            for directory in ("config", "models", "recordings"):
                (self.workspace / directory).mkdir(parents=True, exist_ok=True)
            try:
                create_app = self._load_pisd_app_factory()
                app = create_app(
                    hardware_enabled=False,
                    emulator=self,
                    runtime_root=self.workspace,
                    emulator_frame_port=self.control_port,
                )
                self._diagnostics.install(app, self._generation + 1)
                self._service_faults.install(app)
                with self._camera_input_lock:
                    if self._replay is not None:
                        self._replay.reset()
                        app.config["pisd_services"]["recording"].source_metadata = {
                            "kind": "synthetic_simulation", "generated_by": "PiSD_Emulator",
                            "physical_camera": False, "camera_input": "replay",
                            "replay_source": self._replay.source,
                            "replay_media": self._replay.status().get("media", "images"),
                        }
                if self._active_environment is not None and self._replay is None:
                    recording = app.config["pisd_services"]["recording"]
                    recording.source_metadata = {**recording.source_metadata, "environment": self._active_environment}
                try:
                    from werkzeug.serving import make_server
                except ImportError as exc:
                    raise RuntimeError("Werkzeug is unavailable. Install PiSD/requirements.txt first.") from exc
                server = make_server("127.0.0.1", selected_port, app, threaded=True)
                with self._state_lock:
                    self._app = app
                    self._server = server
                    self.port = selected_port
                    self._last_error = ""
                self.engine.start()
                camera = app.config["pisd_services"]["camera"]
                camera_ok, camera_message = camera.start()
                if not camera_ok:
                    raise RuntimeError(camera_message or "The virtual camera failed to start.")
                thread = threading.Thread(target=server.serve_forever, name="PiSD-Emulator-Web", daemon=True)
                with self._state_lock:
                    self._server_thread = thread
                thread.start()
                with self._state_lock:
                    self._running = True
                    self._generation += 1
                self._record_event("ok", f"PiSD {self.pisd_version} started in emulator mode at http://127.0.0.1:{self.port}/.")
                return self.status()
            except Exception as exc:
                with self._state_lock:
                    self._last_error = f"{type(exc).__name__}: {exc}"
                self._record_event("error", self._last_error)
                self._shutdown_partial_locked()
                raise

    @property
    def pisd_version(self) -> str:
        with self._state_lock:
            app = self._app
        if app is not None:
            return str(app.config.get("pisd_version", "1.0.0"))
        try:
            from pisd import __version__

            return str(__version__)
        except Exception:
            return "1.0.0"

    def _shutdown_partial_locked(self) -> None:
        with self._state_lock:
            server, thread, app = self._server, self._server_thread, self._app
        if app is not None:
            services = app.config.get("pisd_services", {})
            for name, method in (("recording", "close"), ("ai_drive", "close"), ("camera", "stop"), ("motor", "close")):
                service = services.get(name)
                try:
                    callback = getattr(service, method, None)
                    if callback:
                        callback()
                except Exception as exc:
                    self._record_event("warning", f"PiSD {name} shutdown issue: {exc}")
        if server is not None:
            if thread and thread.is_alive():
                try:
                    server.shutdown()
                except Exception:
                    pass
            try:
                server.server_close()
            except Exception:
                pass
        if thread and thread.is_alive() and thread is not threading.current_thread():
            thread.join(timeout=2.0)
        self.engine.stop()
        with self._camera_input_lock:
            self._camera_fault = False
            if isinstance(self._replay, VideoReplay):
                self._replay.close()
        with self._motor_fault_lock:
            self._motor_disconnected = False
            self._service_faults = ServiceFaults()
        with self._state_lock:
            self._server = None
            self._server_thread = None
            self._app = None
            self._running = False

    def stop(self) -> dict[str, Any]:
        with self._lock:
            if not self._running:
                return self.status()
            self._shutdown_partial_locked()
            self._record_event("ok", "PiSD stopped. Virtual motor outputs are zero and the vehicle is halted.")
            return self.status()

    def restart(self, port: Any | None = None) -> dict[str, Any]:
        with self._lock:
            selected_port = self._validate_port(port if port is not None else self.port)
            if self._running:
                self._shutdown_partial_locked()
                self._record_event("ok", "PiSD stopped for restart.")
        return self.start(selected_port)

    def change_track(self, track_id: str) -> None:
        if track_id not in TRACKS:
            raise ValueError(f"Unknown track '{track_id}'.")
        self._stop_pisd_motors()
        self.engine.change_track(track_id)
        self._active_environment = None
        self._record_event("ok", f"Track changed to {TRACKS[track_id]}; vehicle pose reset.")

    def reset_vehicle(self) -> None:
        self._stop_pisd_motors()
        self.engine.reset()
        self._record_event("ok", "Vehicle and track position reset.")

    def _stop_pisd_motors(self) -> None:
        with self._state_lock:
            app = self._app
        if app is None:
            return
        try:
            app.config["pisd_services"]["motor"].stop()
        except Exception as exc:
            self._record_event("warning", f"PiSD virtual motor stop returned an error: {exc}")

    def update_simulation_settings(self, data: dict[str, Any]) -> dict[str, Any]:
        allowed = {
            "wheel_separation_m", "max_speed_mps", "acceleration_mps2", "braking_mps2",
            "motor_dead_zone", "left_efficiency", "right_efficiency", "response_delay_s",
            "road_width_m", "seed",
        }
        current = self._read_emulator_settings()
        current.update({key: value for key, value in data.items() if key in allowed})
        self._save_emulator_settings(current)
        was_running = self._running
        if was_running:
            self.stop()
        self.engine = VehicleEngine(current)
        if self._active_environment is not None:
            self.engine.configure_environment(self._active_environment)
        self.renderer = RoadRenderer()
        self._record_event("ok", "Emulator physics settings saved.")
        if was_running:
            self.start()
        return self.status()

    def environments(self) -> dict[str, Any]:
        with self._lock:
            return {"profiles": list(self._environment_store.read().values()),
                    "active": self._active_environment, "running": self._running}

    def save_environment(self, profile, replace=False) -> dict[str, Any]:
        with self._lock:
            self._environment_store.save(profile, replace)
            return self.environments()

    def select_environment(self, name) -> dict[str, Any]:
        with self._lock:
            if self._running:
                raise ValueError("Stop PiSD before applying a saved environment.")
            if name is None:
                self.engine.change_track("straight")
                self._active_environment = None
            else:
                if not isinstance(name, str):
                    raise ValueError("Invalid environment name.")
                profile = self._environment_store.read().get(name)
                if profile is None:
                    raise ValueError("Saved environment not found.")
                self.engine.configure_environment(profile)
                self._active_environment = profile
            self._record_event("ok", "Saved environment selected." if name else "Default environment selected.")
            return self.environments()

    def diagnostics(self) -> dict[str, Any]:
        return self._diagnostics.sample(self.status())

    def configure_replay(self, source: str | None, loop: bool = False) -> dict[str, Any]:
        # No live source switching: stop the real PiSD services first.
        with self._lock:
            if self._running:
                raise ValueError("Stop PiSD before changing the camera source.")
            candidate = None if source is None else open_replay(self.workspace, source, loop)
            with self._camera_input_lock:
                self._replay = candidate
            self._record_event("ok", "Replay configured." if candidate else "Generated road camera selected.")
            return self.status()

    def set_camera_fault(self, active: bool) -> dict[str, Any]:
        if type(active) is not bool:
            raise ValueError("active must be a boolean.")
        with self._lock:
            if active and not self._running:
                raise ValueError("Start PiSD before injecting a camera fault.")
            with self._camera_input_lock:
                changed = self._camera_fault != active
                self._camera_fault = active
            if changed:
                self._record_event("warning" if active else "ok",
                                   "Virtual camera capture failure injected." if active else
                                   "Camera fault removed; PiSD safety rearm remains explicit.")
            return self.status()

    def camera_input_status(self) -> dict[str, Any]:
        with self._camera_input_lock:
            result = self._replay.status() if self._replay else {"mode": "generated"}
            return {**result, "capture_fault": self._camera_fault}

    def render_frame(self, camera_settings: Any) -> Any:
        with self._camera_input_lock:
            if self._camera_fault:
                # The real CameraService catches this at its capture boundary;
                # never publish a fabricated fresh sequence to mask the fault.
                raise RuntimeError("Injected emulator camera capture failure.")
            if self._replay is not None:
                return self._replay.render(camera_settings)
        return self.renderer.render(self.engine, camera_settings)

    def inject_motor_disconnect(self) -> dict[str, Any]:
        # This fault is sticky for the runtime generation. Removing it while AI
        # or manual intent survives could replay an earlier nonzero command.
        with self._lock:
            if not self._running:
                raise ValueError("Start PiSD before injecting a motor disconnect.")
            with self._motor_fault_lock:
                self._motor_disconnected = True
                self.engine.disconnect_motor_outputs()
            self._record_event("warning", "Virtual motor disconnected; stop the runtime to recover.")
            return self.status()

    def inject_service_fault(self, kind: str) -> dict[str, Any]:
        if kind not in ServiceFaults.KINDS:
            raise ValueError("Unknown service fault.")
        with self._lock:
            if not self._running:
                raise ValueError("Start PiSD before injecting a service fault.")
            with self._motor_fault_lock:
                self._service_faults.activate(kind)
                if kind.startswith("gpio_"):
                    self.engine.disconnect_motor_outputs()
            self._record_event("warning", f"Injected {kind}; stop runtime to recover.")
            return self.status()

    def motor_fault_status(self) -> bool:
        with self._motor_fault_lock:
            return self._motor_disconnected

    def set_motor_outputs(self, payload: dict[str, Any]) -> None:
        with self._motor_fault_lock:
            gpio_fault = self._service_faults.gpio_active()
            if self._motor_disconnected or gpio_fault:
                self.engine.disconnect_motor_outputs()
                keys = ("left_intended", "right_intended", "left_hardware", "right_hardware")
                if any(abs(float(payload.get(key, 0))) > 1e-6 for key in keys):
                    # Existing MotorService records the adapter failure; its
                    # requested values are not proof of applied virtual output.
                    raise RuntimeError("Injected virtual GPIO output failure." if gpio_fault else "Injected virtual motor disconnect.")
                return
            self.engine.set_motor_outputs(payload)

    def status(self) -> dict[str, Any]:
        with self._state_lock:
            running = self._running
            generation = self._generation
            port = self.port
            last_error = self._last_error
            events = list(self._events)
            workspace = str(self.workspace)
        return {
            "runtime_mode": "emulator",
            "running": running,
            "generation": generation,
            "version": self.pisd_version,
            "url": f"http://127.0.0.1:{port}/" if running else "",
            "manual_drive_url": f"http://127.0.0.1:{port}/manual-drive" if running else "",
            "port": port,
            "host": "127.0.0.1",
            "hardware_enabled": False,
            "gpio_access": False,
            "workspace": workspace,
            "last_error": last_error,
            "tracks": [{"id": key, "name": name} for key, name in TRACKS.items()],
            "engine": self.engine.snapshot(),
            "camera_input": self.camera_input_status(),
            "motor_disconnected": self.motor_fault_status(),
            "service_faults": self._service_faults.status(),
            "events": events,
        }

    def pisd_status(self) -> dict[str, Any]:
        with self._state_lock:
            running, app = self._running, self._app
        if not running or app is None:
            return {"ok": False, "runtime_mode": "offline", "hardware_requested": False}
        response = app.test_client().get("/api/status")
        payload = response.get_json(silent=True) or {}
        return payload if response.status_code == 200 else {"ok": False, "status_code": response.status_code}

    def close(self) -> None:
        self.stop()


__all__ = ["PiSDRuntime", "default_workspace"]
