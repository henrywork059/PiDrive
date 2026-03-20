from __future__ import annotations

import argparse
import html
import ipaddress
import json
import socket
import threading
import time
from datetime import datetime
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Callable
from urllib.parse import parse_qs, urlencode, urlparse

from .config import ConfigStore
from .network import NetworkManagerBackend
from .state import RuntimeState
from .status_store import LastStatusStore

HTML_SHELL = """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>{title}</title>
  <style>
    :root {{ color-scheme: light dark; }}
    body {{ font-family: Arial, Helvetica, sans-serif; margin: 0; background: #f4f6f8; color: #1f2933; }}
    .wrap {{ max-width: 1020px; margin: 0 auto; padding: 16px; }}
    .hero {{ background: #0f172a; color: #fff; padding: 18px; border-radius: 14px; margin-bottom: 16px; }}
    .hero h1 {{ margin: 0 0 8px; font-size: 1.8rem; }}
    .hero p {{ margin: 0; opacity: 0.95; }}
    .card {{ background: #fff; border-radius: 14px; padding: 16px; margin-bottom: 14px; box-shadow: 0 2px 10px rgba(15, 23, 42, 0.08); }}
    .grid {{ display: grid; gap: 14px; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); }}
    .status-pill {{ display: inline-block; padding: 6px 10px; border-radius: 999px; font-weight: 700; font-size: 0.9rem; }}
    .status-connected {{ background: #dcfce7; color: #166534; }}
    .status-hotspot {{ background: #dbeafe; color: #1d4ed8; }}
    .status-connecting {{ background: #fef3c7; color: #92400e; }}
    .status-error {{ background: #fee2e2; color: #b91c1c; }}
    .status-idle, .status-starting {{ background: #e5e7eb; color: #374151; }}
    h2 {{ margin-top: 0; font-size: 1.1rem; }}
    dl {{ margin: 0; }}
    dt {{ font-weight: 700; margin-top: 10px; }}
    dd {{ margin: 4px 0 0; word-break: break-word; }}
    .muted {{ color: #52606d; }}
    .notice {{ padding: 12px 14px; border-radius: 10px; margin-bottom: 14px; }}
    .notice-info {{ background: #e0f2fe; color: #0c4a6e; }}
    .notice-warn {{ background: #fef3c7; color: #92400e; }}
    .notice-error {{ background: #fee2e2; color: #991b1b; }}
    form {{ display: grid; gap: 10px; }}
    label {{ font-weight: 700; }}
    input[type=text], input[type=password] {{ width: 100%; box-sizing: border-box; padding: 10px 12px; border-radius: 10px; border: 1px solid #cbd2d9; background: #fff; color: #111827; }}
    input[type=checkbox] {{ transform: scale(1.15); }}
    .btn-row {{ display: flex; flex-wrap: wrap; gap: 8px; }}
    button {{ border: 0; border-radius: 10px; padding: 10px 14px; cursor: pointer; font-weight: 700; }}
    .btn-primary {{ background: #2563eb; color: #fff; }}
    .btn-secondary {{ background: #e5e7eb; color: #111827; }}
    .btn-danger {{ background: #dc2626; color: #fff; }}
    table {{ width: 100%; border-collapse: collapse; }}
    th, td {{ text-align: left; padding: 10px 8px; border-bottom: 1px solid #e5e7eb; vertical-align: top; }}
    th {{ font-size: 0.9rem; color: #52606d; }}
    pre {{ white-space: pre-wrap; word-break: break-word; background: #f8fafc; padding: 12px; border-radius: 10px; border: 1px solid #e5e7eb; max-height: 320px; overflow: auto; }}
    .network-name {{ font-weight: 700; }}
    .mono {{ font-family: ui-monospace, SFMono-Regular, Menlo, monospace; }}
    .small {{ font-size: 0.92rem; }}
    ul.compact {{ margin: 8px 0 0 18px; padding: 0; }}
    @media (max-width: 640px) {{
      body {{ background: #eef2f7; }}
      .wrap {{ padding: 12px; }}
      .card, .hero {{ border-radius: 12px; }}
      th:nth-child(4), td:nth-child(4), th:nth-child(5), td:nth-child(5) {{ display: none; }}
    }}
  </style>
</head>
<body>
  <div class="wrap">
    <div class="hero">
      <h1>{title}</h1>
      <p>{subtitle}</p>
    </div>
    {notice}
    {body}
  </div>
  <script>
    function fillSsid(ssid) {{
      var ssidField = document.getElementById('ssid');
      if (!ssidField) return;
      ssidField.value = ssid || '';
      var passField = document.getElementById('password');
      if (passField) passField.focus();
      window.scrollTo({{ top: document.body.scrollHeight, behavior: 'smooth' }});
    }}
    async function refreshStatus() {{
      try {{
        const response = await fetch('/api/status');
        if (!response.ok) return;
        const data = await response.json();
        const setText = (id, value) => {{
          const el = document.getElementById(id);
          if (el) el.textContent = value || '';
        }};
        const status = document.getElementById('runtime-status');
        if (status) {{
          status.textContent = (data.phase || 'idle').toUpperCase();
          status.className = 'status-pill status-' + (data.phase || 'idle');
        }}
        setText('runtime-message', data.message || '');
        setText('active-ip', data.primary_ip || 'Not assigned yet');
        setText('active-connection', data.active_connection || 'None');
        setText('startup-remaining', data.startup_remaining_s == null ? 'Locked' : String(data.startup_remaining_s));
        setText('session-state', data.session_active ? 'Locked open' : 'Waiting for first client');
        if (data.last_status) {{
          setText('last-ssid', data.last_status.last_ssid || 'None yet');
          setText('last-known-ip', data.last_status.last_known_ip || 'None yet');
          setText('last-updated', data.last_status.updated_at || '');
        }}
      }} catch (error) {{}}
    }}
    refreshStatus();
    {status_timer}
  </script>
</body>
</html>
"""


class PiBooterController:
    def __init__(self, config_path: str | Path):
        self.config_store = ConfigStore(config_path)
        self.config = self.config_store.data
        self.state = RuntimeState(log_limit=self.config["server"]["log_limit"])
        self.network = NetworkManagerBackend(self.config)
        self.status_store = LastStatusStore(self.config_store.runtime_status_path())
        self.hotspot_ssid = self.config_store.compute_hotspot_ssid()
        self.hostname = socket.gethostname().strip() or "raspberrypi"
        self._connection_lock = threading.Lock()
        self._session_lock = threading.Lock()
        self._monitor_stop = threading.Event()
        self._shutdown_requested = threading.Event()
        self._shutdown_callback: Callable[[], None] | None = None
        self._scan_cache: list[dict[str, Any]] = []
        self._scan_cache_ts = 0.0
        self._started_at = time.time()
        self._session_active = False
        self._session_source = ""
        self._session_started_at = 0.0
        self.state.update(last_status=self.status_store.snapshot(), startup_wait_s=self.config["server"]["startup_wait_s"])
        self.state.log("PiBooter controller initialised.")
        self.initial_refresh(force_rescan=True)
        self._monitor_thread = threading.Thread(target=self._monitor_loop, name="PiBooterMonitor", daemon=True)
        self._monitor_thread.start()

    def set_shutdown_callback(self, callback: Callable[[], None]) -> None:
        self._shutdown_callback = callback

    def close(self) -> None:
        self._monitor_stop.set()

    def initial_refresh(self, force_rescan: bool = False) -> None:
        if self.network.nmcli_available() and force_rescan:
            try:
                networks = self.network.list_wifi_networks(force_rescan=True)
                if networks:
                    self._scan_cache = networks
                    self._scan_cache_ts = time.time()
                    self.state.log(f"Loaded {len(networks)} nearby Wi-Fi network(s) into scan cache.")
            except Exception as exc:  # pragma: no cover
                self.state.log(f"Initial Wi-Fi scan failed: {exc}", level="warn")
        self.refresh_state(ensure_hotspot=True)

    def note_http_activity(self, path: str, client_ip: str) -> None:
        self._activate_session(source=f"HTTP request from {client_ip} ({path})")

    def _activate_session(self, source: str) -> None:
        source = str(source or "activity")
        with self._session_lock:
            if self._session_active:
                return
            self._session_active = True
            self._session_source = source
            self._session_started_at = time.time()
        self.state.log(f"Startup hold cancelled because activity was detected: {source}.")
        self.state.update(
            session_active=True,
            session_source=self._session_source,
            session_started_at=self._session_started_at,
            startup_remaining_s=0,
        )

    def get_scan_results(self, force_rescan: bool = False) -> list[dict[str, Any]]:
        if not self.network.nmcli_available():
            return []
        now = time.time()
        ttl = self.config["server"]["scan_cache_ttl_s"]
        if not force_rescan and self._scan_cache and (now - self._scan_cache_ts) < ttl:
            return list(self._scan_cache)
        networks = self.network.list_wifi_networks(force_rescan=force_rescan)
        if networks:
            self._scan_cache = networks
            self._scan_cache_ts = now
            self.state.log(f"Wi-Fi scan refreshed. Found {len(networks)} network(s).")
            return list(networks)
        return list(self._scan_cache)

    def refresh_state(self, ensure_hotspot: bool = False) -> dict[str, Any]:
        snapshot = self.network.get_runtime_snapshot(self.hotspot_ssid)
        scan_results = self.get_scan_results(force_rescan=False)
        known_connections = self.network.get_known_wifi_connections() if snapshot.get("nmcli_available") else []
        if snapshot.get("hotspot_clients"):
            joined = ", ".join(client.get("ip", "") for client in snapshot.get("hotspot_clients", []) if client.get("ip"))
            self._activate_session(source=f"hotspot client joined ({joined or 'client detected'})")

        phase = snapshot.get("phase", "idle")
        message = snapshot.get("message", "")
        attempt = self.state.snapshot().get("connection_attempt")
        if ensure_hotspot and snapshot.get("nmcli_available") and not self._shutdown_requested.is_set():
            autostart = self.config["network"].get("hotspot_autostart_when_unconfigured", True)
            attempt_running = bool(attempt and attempt.get("status") == "running")
            if autostart and not attempt_running and not snapshot.get("any_non_hotspot_connection") and not snapshot["wifi"].get("hotspot_active"):
                result = self.network.start_hotspot(ssid=self.hotspot_ssid, password=self.config["network"]["hotspot_password"])
                if result.ok:
                    self.state.log(f"Hotspot started: {self.hotspot_ssid} ({self.config['network']['hotspot_url']}).")
                    snapshot = self.network.get_runtime_snapshot(self.hotspot_ssid)
                    phase = snapshot.get("phase", phase)
                    message = snapshot.get("message", message)
                else:
                    phase = "error"
                    message = f"Failed to start hotspot: {result.stderr or result.stdout or 'unknown error'}"
                    self.state.log(message, level="error")

        primary_ip = self._pick_primary_ip(snapshot.get("ip_addresses", {}), snapshot)
        active_connection = self._pick_active_connection(snapshot)
        hotspot_info = {
            "ssid": self.hotspot_ssid,
            "password": self.config["network"]["hotspot_password"],
            "url": self.config["network"]["hotspot_url"],
            "active": snapshot.get("wifi", {}).get("hotspot_active", False),
        }
        if attempt and attempt.get("status") == "running":
            phase = "connecting"
            message = attempt.get("message") or message

        startup_wait_s = int(self.config["server"]["startup_wait_s"])
        startup_remaining_s = 0 if self._session_active else max(0, startup_wait_s - int(time.time() - self._started_at))

        self.state.update(
            phase=phase,
            message=message,
            last_error=self.state.snapshot().get("last_error", ""),
            network=snapshot,
            scan_results=scan_results,
            known_connections=known_connections,
            hotspot=hotspot_info,
            hotspot_clients=snapshot.get("hotspot_clients", []),
            primary_ip=primary_ip,
            active_connection=active_connection,
            last_status=self.status_store.snapshot(),
            session_active=self._session_active,
            session_source=self._session_source,
            session_started_at=self._session_started_at,
            startup_wait_s=startup_wait_s,
            startup_remaining_s=startup_remaining_s,
        )
        return self.state.snapshot()

    @staticmethod
    def _pick_primary_ip(ip_map: dict[str, list[str]], snapshot: dict[str, Any]) -> str:
        preferred_interfaces: list[str] = []
        wifi = snapshot.get("wifi", {})
        ethernet = snapshot.get("ethernet", {})
        if ethernet and ethernet.get("state") == "connected":
            preferred_interfaces.append(ethernet.get("device", "") or "eth0")
        if wifi.get("connected"):
            preferred_interfaces.append(wifi.get("interface", "") or "wlan0")
        preferred_interfaces.extend([key for key in ip_map if not key.endswith("_gateway")])
        seen: set[str] = set()
        for ifname in preferred_interfaces:
            if not ifname or ifname in seen:
                continue
            seen.add(ifname)
            ips = ip_map.get(ifname, [])
            if ips:
                return PiBooterController._strip_cidr(ips[0])
        return ""

    @staticmethod
    def _pick_active_connection(snapshot: dict[str, Any]) -> str:
        devices = snapshot.get("devices", [])
        connected = [row.get("connection", "") for row in devices if row.get("state") == "connected" and row.get("connection")]
        return connected[0] if connected else ""

    @staticmethod
    def _strip_cidr(value: str) -> str:
        return str(value or "").split("/", 1)[0].strip()

    def _hotspot_network(self) -> ipaddress.IPv4Network | None:
        try:
            return ipaddress.ip_interface(self.config["network"]["hotspot_ip"]).network
        except ValueError:
            return None

    def _is_hotspot_ip(self, address: str) -> bool:
        hotspot_network = self._hotspot_network()
        if hotspot_network is None:
            return False
        try:
            return ipaddress.ip_address(address) in hotspot_network
        except ValueError:
            return False

    def _gateway_ip_from_snapshot(self, snapshot: dict[str, Any]) -> str:
        ip_map = snapshot.get("ip_addresses", {})
        ethernet = snapshot.get("ethernet", {})
        wifi = snapshot.get("wifi", {})
        preferred = []
        if ethernet and ethernet.get("state") == "connected":
            preferred.append(f"{ethernet.get('device', 'eth0')}_gateway")
        if wifi.get("connected") and not wifi.get("hotspot_active"):
            preferred.append(f"{wifi.get('interface', 'wlan0')}_gateway")
        preferred.extend([key for key in ip_map if key.endswith("_gateway")])
        for key in preferred:
            gateways = ip_map.get(key, [])
            if gateways:
                return self._strip_cidr(gateways[0])
        return ""

    def start_connection_attempt(self, ssid: str, password: str, hidden: bool = False) -> None:
        ssid = str(ssid or "").strip()
        password = str(password or "")
        if not ssid:
            raise ValueError("SSID is required.")
        current_attempt = self.state.snapshot().get("connection_attempt") or {}
        if current_attempt.get("status") == "running":
            raise RuntimeError("A Wi-Fi connection attempt is already running.")

        self._activate_session(source=f"Wi-Fi setup started for {ssid}")
        self.state.update(
            connection_attempt={
                "status": "running",
                "ssid": ssid,
                "hidden": bool(hidden),
                "started_at": time.time(),
                "message": f"Trying to connect to {ssid}. The hotspot may disconnect while the Pi switches modes.",
            }
        )
        self.state.log(f"Starting Wi-Fi connection attempt for SSID '{ssid}'.")
        thread = threading.Thread(
            target=self._run_connection_attempt,
            args=(ssid, password, bool(hidden)),
            daemon=True,
            name="PiBooterConnect",
        )
        thread.start()

    def _run_connection_attempt(self, ssid: str, password: str, hidden: bool) -> None:
        with self._connection_lock:
            result = self.network.connect_to_wifi(ssid=ssid, password=password, hidden=hidden)
            if result.ok:
                lan_ip, gateway_ip = self._wait_for_router_ip()
                last_status = self.status_store.save(
                    {
                        "last_ssid": ssid,
                        "last_known_ip": lan_ip,
                        "last_gateway_ip": gateway_ip,
                        "hostname": self.hostname,
                        "updated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
                        "note": "Last known router-side Pi IP. This may change if your router assigns a new address.",
                    }
                )
                success_target = lan_ip or f"{self.hostname}.local"
                success_message = (
                    f"Pi connected to {ssid}. Last known Pi IP was saved as {success_target}. Reconnect your phone to the same Wi-Fi to reach the Pi."
                )
                self.state.log(success_message)
                self.state.update(
                    connection_attempt={
                        "status": "success",
                        "ssid": ssid,
                        "hidden": hidden,
                        "finished_at": time.time(),
                        "message": success_message,
                    },
                    last_error="",
                    last_status=last_status,
                )
                self.refresh_state(ensure_hotspot=False)
                delay_s = int(self.config["server"].get("shutdown_after_success_s", 1))
                if delay_s > 0:
                    time.sleep(delay_s)
                self.request_shutdown(reason=f"Wi-Fi connected successfully. Saved last known IP: {success_target}.", stop_hotspot=False)
            else:
                error_message = result.stderr or result.stdout or "Unknown nmcli error."
                self.state.log(f"Wi-Fi connection failed for {ssid}: {error_message}", level="error")
                self.state.update(
                    connection_attempt={
                        "status": "error",
                        "ssid": ssid,
                        "hidden": hidden,
                        "finished_at": time.time(),
                        "message": f"Could not connect to {ssid}: {error_message}",
                    },
                    last_error=error_message,
                )
                autostart = self.config["network"].get("hotspot_autostart_when_unconfigured", True)
                if autostart:
                    hotspot_result = self.network.start_hotspot(ssid=self.hotspot_ssid, password=self.config["network"]["hotspot_password"])
                    if hotspot_result.ok:
                        self.state.log("Hotspot restored after failed Wi-Fi connection attempt.", level="warn")
                    else:
                        self.state.log(
                            f"Failed to restore hotspot after Wi-Fi error: {hotspot_result.stderr or hotspot_result.stdout}",
                            level="error",
                        )
                self.get_scan_results(force_rescan=True)
                self.refresh_state(ensure_hotspot=False)

    def _wait_for_router_ip(self) -> tuple[str, str]:
        deadline = time.time() + max(5, int(self.config["server"]["connection_wait_s"]))
        latest_ip = ""
        latest_gateway = ""
        while time.time() < deadline:
            snapshot = self.network.get_runtime_snapshot(self.hotspot_ssid)
            if snapshot.get("any_non_hotspot_connection"):
                latest_ip = self._pick_primary_ip(snapshot.get("ip_addresses", {}), snapshot)
                latest_gateway = self._gateway_ip_from_snapshot(snapshot)
                if latest_ip and not self._is_hotspot_ip(latest_ip):
                    return latest_ip, latest_gateway
            time.sleep(1)
        snapshot = self.network.get_runtime_snapshot(self.hotspot_ssid)
        latest_ip = self._pick_primary_ip(snapshot.get("ip_addresses", {}), snapshot)
        latest_gateway = self._gateway_ip_from_snapshot(snapshot)
        return latest_ip, latest_gateway

    def forget_connection(self, name: str) -> tuple[bool, str]:
        name = str(name or "").strip()
        if not name:
            return False, "Connection name is required."
        result = self.network.forget_connection(name)
        if result.ok:
            self.state.log(f"Forgot saved Wi-Fi profile: {name}.")
            self.refresh_state(ensure_hotspot=False)
            return True, f"Forgot saved network '{name}'."
        message = result.stderr or result.stdout or "Unknown error while deleting connection."
        self.state.log(f"Failed to forget saved network {name}: {message}", level="error")
        self.refresh_state(ensure_hotspot=False)
        return False, message

    def rescan(self) -> None:
        self.get_scan_results(force_rescan=True)
        self.refresh_state(ensure_hotspot=False)

    def request_shutdown(self, reason: str, stop_hotspot: bool = False) -> None:
        if self._shutdown_requested.is_set():
            return
        self._shutdown_requested.set()
        if stop_hotspot:
            result = self.network.stop_hotspot()
            if result.ok:
                self.state.log("Hotspot stopped before PiBooter exit.")
            else:
                message = result.stderr or result.stdout or "Unknown error while stopping hotspot."
                self.state.log(f"Failed to stop hotspot before exit: {message}", level="warn")
        self.state.log(reason)
        self.state.update(should_exit=True, shutdown_reason=reason)
        if self._shutdown_callback is not None:
            threading.Thread(target=self._shutdown_callback, name="PiBooterShutdown", daemon=True).start()

    def _monitor_loop(self) -> None:
        poll_interval = max(1, int(self.config["server"].get("poll_interval_s", 1)))
        periodic_refresh = max(1, int(self.config["server"].get("monitor_interval_s", 5)))
        next_full_refresh = 0.0
        while not self._monitor_stop.wait(poll_interval):
            try:
                now = time.time()
                ensure_hotspot = not self._shutdown_requested.is_set()
                snapshot = self.refresh_state(ensure_hotspot=ensure_hotspot)
                if not self._session_active and not self._shutdown_requested.is_set():
                    startup_wait_s = int(self.config["server"].get("startup_wait_s", 5))
                    if now - self._started_at >= startup_wait_s:
                        self.request_shutdown(
                            reason=f"No client or web request arrived within {startup_wait_s} seconds. PiBooter is exiting.",
                            stop_hotspot=True,
                        )
                        continue
                if now >= next_full_refresh:
                    next_full_refresh = now + periodic_refresh
            except Exception as exc:  # pragma: no cover
                self.state.log(f"Background monitor error: {exc}", level="error")


class RequestHandler(BaseHTTPRequestHandler):
    controller: PiBooterController
    server_version = "PiBooter/0.1.1"

    def do_GET(self) -> None:  # noqa: N802
        self.controller.note_http_activity(self.path, self.client_address[0])
        parsed = urlparse(self.path)
        path = parsed.path or "/"
        if path in {"/", "/index.html"}:
            self.handle_index(parse_qs(parsed.query))
            return
        if path == "/api/status":
            self.handle_status_json()
            return
        if path == "/api/networks":
            self.handle_networks_json()
            return
        if path in {"/generate_204", "/gen_204", "/connecttest.txt", "/redirect", "/success.txt"}:
            self.redirect("/")
            return
        if path == "/hotspot-detect.html":
            self.redirect("/")
            return
        if path == "/ncsi.txt":
            self.send_text("Microsoft NCSI")
            return
        if path == "/favicon.ico":
            self.send_response(HTTPStatus.NO_CONTENT)
            self.end_headers()
            return
        self.send_error(HTTPStatus.NOT_FOUND, "Not found")

    def do_POST(self) -> None:  # noqa: N802
        self.controller.note_http_activity(self.path, self.client_address[0])
        parsed = urlparse(self.path)
        path = parsed.path or "/"
        form = self.parse_post_form()
        if path == "/connect":
            self.handle_connect(form)
            return
        if path == "/forget":
            self.handle_forget(form)
            return
        if path == "/rescan":
            self.controller.rescan()
            self.redirect("/?notice=Wi-Fi%20scan%20refreshed")
            return
        self.send_error(HTTPStatus.NOT_FOUND, "Not found")

    def log_message(self, format: str, *args: Any) -> None:  # noqa: A003
        message = format % args
        try:
            self.controller.state.log(f"HTTP {self.command} {self.path} - {message}")
        except Exception:
            pass

    def parse_post_form(self) -> dict[str, str]:
        content_length = int(self.headers.get("Content-Length", "0") or 0)
        raw = self.rfile.read(content_length)
        content_type = self.headers.get("Content-Type", "")
        if "application/json" in content_type:
            try:
                data = json.loads(raw.decode("utf-8"))
            except json.JSONDecodeError:
                return {}
            if isinstance(data, dict):
                return {str(key): str(value) for key, value in data.items()}
            return {}
        parsed = parse_qs(raw.decode("utf-8"), keep_blank_values=True)
        return {key: values[0] if values else "" for key, values in parsed.items()}

    def handle_index(self, query: dict[str, list[str]]) -> None:
        snapshot = self.controller.refresh_state(ensure_hotspot=False)
        notice = self.render_notice(query, snapshot)
        body = self.render_index_body(snapshot)
        refresh_s = int(self.controller.config["ui"]["status_refresh_s"])
        status_timer = f"setInterval(refreshStatus, {refresh_s * 1000});" if refresh_s > 0 else ""
        page = HTML_SHELL.format(
            title=html.escape(self.controller.config["ui"]["title"]),
            subtitle=html.escape(self.controller.config["ui"]["subtitle"]),
            notice=notice,
            body=body,
            status_timer=status_timer,
        )
        self.send_html(page)

    def render_notice(self, query: dict[str, list[str]], snapshot: dict[str, Any]) -> str:
        message = ""
        level = "info"
        if query.get("notice"):
            message = query["notice"][0]
        attempt = snapshot.get("connection_attempt")
        if attempt:
            if attempt.get("status") == "running":
                message = attempt.get("message", message)
                level = "warn"
            elif attempt.get("status") == "success":
                message = attempt.get("message", message)
                level = "info"
            elif attempt.get("status") == "error":
                message = attempt.get("message", message)
                level = "error"
        if not message:
            return ""
        level_class = {"info": "notice-info", "warn": "notice-warn", "error": "notice-error"}.get(level, "notice-info")
        return f'<div class="notice {level_class}">{html.escape(message)}</div>'

    def render_index_body(self, snapshot: dict[str, Any]) -> str:
        phase = snapshot.get("phase", "idle")
        status_class = {
            "connected": "status-connected",
            "hotspot": "status-hotspot",
            "connecting": "status-connecting",
            "error": "status-error",
            "starting": "status-starting",
        }.get(phase, "status-idle")
        network = snapshot.get("network", {})
        hotspot = snapshot.get("hotspot", {})
        wifi = network.get("wifi", {})
        primary_ip = snapshot.get("primary_ip") or "Not assigned yet"
        active_connection = snapshot.get("active_connection") or "None"
        devices = network.get("devices", [])
        last_status = snapshot.get("last_status", {}) or {}
        hotspot_clients = snapshot.get("hotspot_clients", []) or []
        device_rows = "".join(
            f"<tr><td>{html.escape(row.get('device', ''))}</td><td>{html.escape(row.get('type', ''))}</td><td>{html.escape(row.get('state', ''))}</td><td>{html.escape(row.get('connection', ''))}</td></tr>"
            for row in devices
        ) or '<tr><td colspan="4" class="muted">No network devices reported yet.</td></tr>'

        networks_table = self.render_scan_results(snapshot.get("scan_results", []))
        known_table = self.render_known_connections(snapshot.get("known_connections", []))
        logs_text = self.render_logs(snapshot.get("logs", []))
        chip_message = html.escape(snapshot.get("message", ""))
        session_state = "Locked open" if snapshot.get("session_active") else "Waiting for first client"
        startup_remaining = "Locked" if snapshot.get("session_active") else str(snapshot.get("startup_remaining_s", 0))

        hotspot_block = ""
        if hotspot:
            hotspot_block = f"""
            <div class="card">
              <h2>Hotspot details</h2>
              <dl>
                <dt>SSID</dt><dd class="mono">{html.escape(hotspot.get('ssid', ''))}</dd>
                <dt>Password</dt><dd class="mono">{html.escape(hotspot.get('password', ''))}</dd>
                <dt>Open on your phone</dt><dd><a href="{html.escape(hotspot.get('url', '/'))}">{html.escape(hotspot.get('url', ''))}</a></dd>
                <dt>Tip</dt><dd>If your phone says the hotspot has no internet, stay connected anyway and open the URL above.</dd>
              </dl>
            </div>
            """

        client_rows = "".join(
            f"<tr><td class='mono'>{html.escape(row.get('ip', ''))}</td><td class='mono'>{html.escape(row.get('mac', ''))}</td><td>{html.escape(row.get('state', ''))}</td></tr>"
            for row in hotspot_clients
        ) or '<tr><td colspan="3" class="muted">No hotspot client detected yet.</td></tr>'

        manual_form = f"""
        <div class="card">
          <h2>Connect Pi to home Wi-Fi</h2>
          <form method="post" action="/connect">
            <div>
              <label for="ssid">Wi-Fi name (SSID)</label>
              <input id="ssid" name="ssid" type="text" required placeholder="Example: MyHomeWiFi">
            </div>
            <div>
              <label for="password">Password</label>
              <input id="password" name="password" type="password" placeholder="Leave blank only for open networks">
            </div>
            <div>
              <label><input name="hidden" type="checkbox" value="1"> Hidden network</label>
            </div>
            <div class="btn-row">
              <button class="btn-primary" type="submit">Connect Pi to this Wi-Fi</button>
              <button class="btn-secondary" type="button" onclick="document.getElementById('password').value='';">Clear password</button>
            </div>
          </form>
        </div>
        """

        nmcli_warning = ""
        if not network.get("nmcli_available", False):
            nmcli_warning = """
            <div class="notice notice-error">
              NetworkManager / nmcli is missing. PiBooter can still show this page, but it cannot start the setup hotspot or save Wi-Fi through the web UI until NetworkManager is installed and enabled.
            </div>
            """

        return f"""
        {nmcli_warning}
        <div class="grid">
          <div class="card">
            <h2>Current status</h2>
            <p><span id="runtime-status" class="status-pill {status_class}">{html.escape(phase.upper())}</span></p>
            <p id="runtime-message">{chip_message}</p>
            <dl>
              <dt>Active connection</dt><dd id="active-connection">{html.escape(active_connection)}</dd>
              <dt>Primary IP</dt><dd id="active-ip" class="mono">{html.escape(primary_ip)}</dd>
              <dt>Wi-Fi interface</dt><dd>{html.escape(wifi.get('interface', ''))}</dd>
            </dl>
          </div>
          <div class="card">
            <h2>Boot window</h2>
            <dl>
              <dt>Session state</dt><dd id="session-state">{html.escape(session_state)}</dd>
              <dt>First-client wait</dt><dd><span id="startup-remaining">{html.escape(startup_remaining)}</span> second(s)</dd>
              <dt>Rule</dt><dd class="small">PiBooter exits if no hotspot client and no web request arrives within {int(self.controller.config['server']['startup_wait_s'])} seconds.</dd>
            </dl>
          </div>
        </div>
        <div class="grid">
          <div class="card">
            <h2>Last known router connection</h2>
            <dl>
              <dt>Last SSID</dt><dd id="last-ssid">{html.escape(last_status.get('last_ssid') or 'None yet')}</dd>
              <dt>Last known Pi IP</dt><dd id="last-known-ip" class="mono">{html.escape(last_status.get('last_known_ip') or 'None yet')}</dd>
              <dt>Hostname</dt><dd class="mono">{html.escape(last_status.get('hostname') or self.controller.hostname)}</dd>
              <dt>Updated</dt><dd id="last-updated">{html.escape(last_status.get('updated_at') or '')}</dd>
              <dt>Note</dt><dd>{html.escape(last_status.get('note') or 'The saved IP is the last known router-side address and may change later.')}</dd>
            </dl>
          </div>
          <div class="card">
            <h2>What to do</h2>
            <ol>
              <li>Connect your phone to the PiBooter hotspot.</li>
              <li>Open the setup page at the hotspot URL.</li>
              <li>Select your home Wi-Fi or type the SSID manually.</li>
              <li>Enter the Wi-Fi password and submit.</li>
              <li>After a successful join, reconnect your phone to the same router Wi-Fi and open the saved Pi IP or <span class="mono">{html.escape(self.controller.hostname)}.local</span>.</li>
            </ol>
          </div>
        </div>
        {hotspot_block}
        <div class="grid">
          <div class="card">
            <h2>Hotspot clients</h2>
            <table>
              <thead><tr><th>Client IP</th><th>MAC</th><th>State</th></tr></thead>
              <tbody>{client_rows}</tbody>
            </table>
          </div>
          <div class="card">
            <h2>Nearby Wi-Fi networks</h2>
            <form method="post" action="/rescan" style="margin-bottom: 12px; display: inline-block;">
              <button class="btn-secondary" type="submit">Refresh scan</button>
            </form>
            <p class="muted">Some Raspberry Pi Wi-Fi adapters cannot actively scan while the hotspot is running. If your network is missing, type the SSID manually below.</p>
            {networks_table}
          </div>
        </div>
        {manual_form}
        <div class="grid">
          <div class="card">
            <h2>Network devices</h2>
            <table>
              <thead><tr><th>Device</th><th>Type</th><th>State</th><th>Connection</th></tr></thead>
              <tbody>{device_rows}</tbody>
            </table>
          </div>
          <div class="card">
            <h2>Saved Wi-Fi profiles</h2>
            {known_table}
          </div>
        </div>
        <div class="card">
          <h2>Recent log</h2>
          <pre>{html.escape(logs_text)}</pre>
        </div>
        """

    @staticmethod
    def render_scan_results(networks: list[dict[str, Any]]) -> str:
        if not networks:
            return '<p class="muted">No nearby Wi-Fi networks are cached yet. Use the manual form below if needed.</p>'
        rows = []
        for item in networks:
            ssid = item.get("ssid") or "(hidden network)"
            use_button = ""
            if item.get("ssid"):
                quoted_ssid = json.dumps(item.get("ssid"))
                use_button = f'<button class="btn-secondary" type="button" onclick="fillSsid({quoted_ssid})">Use this network</button>'
            rows.append(
                "<tr>"
                f"<td><div class='network-name'>{html.escape(ssid)}</div></td>"
                f"<td>{html.escape(str(item.get('signal', '')))}%</td>"
                f"<td>{html.escape(str(item.get('security', 'open')))}</td>"
                f"<td>{html.escape(str(item.get('channel', '')))}</td>"
                f"<td>{use_button}</td>"
                "</tr>"
            )
        return (
            "<table><thead><tr><th>SSID</th><th>Signal</th><th>Security</th><th>Channel</th><th></th></tr></thead>"
            f"<tbody>{''.join(rows)}</tbody></table>"
        )

    @staticmethod
    def render_known_connections(connections: list[dict[str, str]]) -> str:
        if not connections:
            return '<p class="muted">No saved Wi-Fi profiles yet.</p>'
        rows = []
        for item in connections:
            rows.append(
                "<tr>"
                f"<td>{html.escape(item.get('name', ''))}</td>"
                f"<td>{html.escape(item.get('autoconnect', ''))}</td>"
                "<td>"
                "<form method='post' action='/forget' style='display:inline;'>"
                f"<input type='hidden' name='name' value='{html.escape(item.get('name', ''))}'>"
                "<button class='btn-danger' type='submit'>Forget</button>"
                "</form>"
                "</td>"
                "</tr>"
            )
        return "<table><thead><tr><th>Name</th><th>Autoconnect</th><th></th></tr></thead>" f"<tbody>{''.join(rows)}</tbody></table>"

    @staticmethod
    def render_logs(logs: list[dict[str, Any]]) -> str:
        if not logs:
            return "No log entries yet."
        lines = []
        for entry in logs[-100:]:
            ts = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(float(entry.get("ts", 0))))
            lines.append(f"[{ts}] {str(entry.get('level', 'info')).upper()}: {entry.get('message', '')}")
        return "\n".join(lines)

    def handle_status_json(self) -> None:
        snapshot = self.controller.refresh_state(ensure_hotspot=False)
        payload = {
            "phase": snapshot.get("phase"),
            "message": snapshot.get("message"),
            "primary_ip": snapshot.get("primary_ip"),
            "active_connection": snapshot.get("active_connection"),
            "connection_attempt": snapshot.get("connection_attempt"),
            "hotspot": snapshot.get("hotspot"),
            "last_status": snapshot.get("last_status"),
            "hotspot_clients": snapshot.get("hotspot_clients"),
            "session_active": snapshot.get("session_active"),
            "startup_remaining_s": snapshot.get("startup_remaining_s"),
        }
        self.send_json(payload)

    def handle_networks_json(self) -> None:
        self.controller.rescan()
        snapshot = self.controller.state.snapshot()
        self.send_json(snapshot.get("scan_results", []))

    def handle_connect(self, form: dict[str, str]) -> None:
        ssid = form.get("ssid", "")
        password = form.get("password", "")
        hidden = form.get("hidden", "") in {"1", "true", "on", "yes"}
        try:
            self.controller.start_connection_attempt(ssid=ssid, password=password, hidden=hidden)
        except Exception as exc:
            notice = urlencode({"notice": str(exc)})
            self.redirect(f"/?{notice}")
            return
        self.redirect("/?notice=Connection%20attempt%20started")

    def handle_forget(self, form: dict[str, str]) -> None:
        name = form.get("name", "")
        ok, message = self.controller.forget_connection(name)
        notice = urlencode({"notice": message})
        self.redirect(f"/?{notice}")

    def redirect(self, location: str) -> None:
        self.send_response(HTTPStatus.FOUND)
        self.send_header("Location", location)
        self.end_headers()

    def send_html(self, body: str) -> None:
        encoded = body.encode("utf-8")
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)

    def send_json(self, payload: Any) -> None:
        encoded = json.dumps(payload, indent=2).encode("utf-8")
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)

    def send_text(self, body: str) -> None:
        encoded = body.encode("utf-8")
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)


class PiBooterServer(ThreadingHTTPServer):
    def __init__(self, address: tuple[str, int], controller: PiBooterController):
        RequestHandler.controller = controller
        super().__init__(address, RequestHandler)
        self.controller = controller
        self.controller.set_shutdown_callback(self.shutdown)

    def server_close(self) -> None:
        try:
            self.controller.close()
        finally:
            super().server_close()


def create_server(config_path: str | Path) -> PiBooterServer:
    controller = PiBooterController(config_path)
    host = controller.config["server"]["host"]
    port = int(controller.config["server"]["port"])
    controller.state.log(f"Serving PiBooter web UI on {host}:{port}.")
    return PiBooterServer((host, port), controller)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="PiBooter Wi-Fi onboarding web service")
    parser.add_argument("--config", default=str(Path(__file__).resolve().parent.parent / "config" / "settings.json"))
    parser.add_argument("--write-default-config", action="store_true", help="Create or normalize the config file, then exit.")
    args = parser.parse_args(argv)

    config_store = ConfigStore(args.config)
    if args.write_default_config:
        config_store.runtime_status_path().parent.mkdir(parents=True, exist_ok=True)
        print(f"Wrote default config to {config_store.path}")
        return 0

    server = create_server(config_store.path)
    try:
        server.serve_forever(poll_interval=0.5)
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
