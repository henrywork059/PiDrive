from __future__ import annotations

import ipaddress
import shutil
import subprocess
import time
from dataclasses import dataclass
from typing import Any


def split_nmcli_terse(line: str) -> list[str]:
    parts: list[str] = []
    current: list[str] = []
    escape = False
    for char in line:
        if escape:
            current.append(char)
            escape = False
            continue
        if char == "\\":
            escape = True
            continue
        if char == ":":
            parts.append("".join(current))
            current = []
            continue
        current.append(char)
    parts.append("".join(current))
    return parts


@dataclass
class CommandResult:
    ok: bool
    stdout: str = ""
    stderr: str = ""
    returncode: int = 0


class NetworkManagerBackend:
    def __init__(self, config: dict[str, Any]):
        self.config = config
        self.network_cfg = config["network"]
        self.server_cfg = config["server"]
        self.wifi_ifname = self.network_cfg["wifi_interface"]
        self.ethernet_ifname = self.network_cfg["ethernet_interface"]
        self.hotspot_name = self.network_cfg["hotspot_connection_name"]
        self.hotspot_ip = self.network_cfg["hotspot_ip"]
        self.hotspot_band = self.network_cfg["hotspot_band"]
        self.hotspot_channel = str(self.network_cfg["hotspot_channel"])

    def nmcli_available(self) -> bool:
        return shutil.which("nmcli") is not None

    def ip_command_available(self) -> bool:
        return shutil.which("ip") is not None

    def run(self, *args: str, timeout: int | None = None) -> CommandResult:
        if not self.nmcli_available():
            return CommandResult(ok=False, stderr="nmcli is not installed.", returncode=127)
        try:
            completed = subprocess.run(
                ["nmcli", *args],
                check=False,
                capture_output=True,
                text=True,
                timeout=timeout or self.server_cfg["connection_wait_s"],
            )
        except subprocess.TimeoutExpired:
            return CommandResult(ok=False, stderr="Command timed out.", returncode=124)
        return CommandResult(
            ok=completed.returncode == 0,
            stdout=completed.stdout.strip(),
            stderr=completed.stderr.strip(),
            returncode=completed.returncode,
        )

    def run_ip(self, *args: str, timeout: int = 5) -> CommandResult:
        if not self.ip_command_available():
            return CommandResult(ok=False, stderr="ip command is not installed.", returncode=127)
        try:
            completed = subprocess.run(
                ["ip", *args],
                check=False,
                capture_output=True,
                text=True,
                timeout=timeout,
            )
        except subprocess.TimeoutExpired:
            return CommandResult(ok=False, stderr="Command timed out.", returncode=124)
        return CommandResult(
            ok=completed.returncode == 0,
            stdout=completed.stdout.strip(),
            stderr=completed.stderr.strip(),
            returncode=completed.returncode,
        )

    def get_device_status(self) -> list[dict[str, str]]:
        result = self.run("-t", "-f", "DEVICE,TYPE,STATE,CONNECTION", "device", "status", timeout=15)
        if not result.ok:
            return []
        rows: list[dict[str, str]] = []
        for line in result.stdout.splitlines():
            if not line.strip():
                continue
            fields = split_nmcli_terse(line)
            while len(fields) < 4:
                fields.append("")
            rows.append(
                {
                    "device": fields[0],
                    "type": fields[1],
                    "state": fields[2],
                    "connection": fields[3],
                }
            )
        return rows

    def get_ip_addresses(self) -> dict[str, list[str]]:
        addresses: dict[str, list[str]] = {}
        for ifname in (self.wifi_ifname, self.ethernet_ifname):
            result = self.run("-t", "-f", "IP4.ADDRESS,IP4.GATEWAY", "device", "show", ifname, timeout=10)
            if not result.ok:
                continue
            ips: list[str] = []
            gateways: list[str] = []
            for line in result.stdout.splitlines():
                value = line.strip()
                if not value:
                    continue
                if value.startswith("IP4.ADDRESS"):
                    _, _, current = value.partition(":")
                    current = current.strip()
                    if current:
                        ips.append(current)
                elif value.startswith("IP4.GATEWAY"):
                    _, _, current = value.partition(":")
                    current = current.strip()
                    if current:
                        gateways.append(current)
            if ips:
                addresses[ifname] = ips
            if gateways:
                addresses[f"{ifname}_gateway"] = gateways
        return addresses

    def get_hotspot_clients(self) -> list[dict[str, str]]:
        result = self.run_ip("neigh", "show", "dev", self.wifi_ifname, timeout=5)
        if not result.ok:
            return []
        try:
            hotspot_network = ipaddress.ip_interface(self.hotspot_ip).network
        except ValueError:
            hotspot_network = None
        clients: list[dict[str, str]] = []
        for line in result.stdout.splitlines():
            line = line.strip()
            if not line:
                continue
            parts = line.split()
            if not parts:
                continue
            ip_str = parts[0]
            try:
                ip_obj = ipaddress.ip_address(ip_str)
            except ValueError:
                continue
            if hotspot_network is not None and ip_obj not in hotspot_network:
                continue
            if str(ip_obj) == str(hotspot_network.network_address + 1) if hotspot_network else False:
                continue
            mac = ""
            state = parts[-1] if parts else ""
            if "lladdr" in parts:
                idx = parts.index("lladdr")
                if idx + 1 < len(parts):
                    mac = parts[idx + 1]
            clients.append({"ip": str(ip_obj), "mac": mac, "state": state})
        deduped: dict[str, dict[str, str]] = {}
        for client in clients:
            deduped[client["ip"]] = client
        return sorted(deduped.values(), key=lambda row: row["ip"])

    def connection_profile_exists(self, name: str) -> bool:
        result = self.run("-t", "-f", "NAME", "connection", "show", timeout=10)
        if not result.ok:
            return False
        existing = {line.strip() for line in result.stdout.splitlines() if line.strip()}
        return name in existing

    def get_known_wifi_connections(self) -> list[dict[str, str]]:
        result = self.run("-t", "-f", "NAME,TYPE,AUTOCONNECT,DEVICE", "connection", "show", timeout=10)
        if not result.ok:
            return []
        items: list[dict[str, str]] = []
        for line in result.stdout.splitlines():
            if not line.strip():
                continue
            fields = split_nmcli_terse(line)
            while len(fields) < 4:
                fields.append("")
            if fields[1] not in {"802-11-wireless", "wifi"}:
                continue
            if fields[0] == self.hotspot_name:
                continue
            items.append(
                {
                    "name": fields[0],
                    "type": fields[1],
                    "autoconnect": fields[2],
                    "device": fields[3],
                }
            )
        items.sort(key=lambda item: item["name"].lower())
        return items

    def list_wifi_networks(self, force_rescan: bool = False) -> list[dict[str, Any]]:
        if force_rescan:
            self.run("device", "wifi", "rescan", "ifname", self.wifi_ifname, timeout=20)
            time.sleep(2.0)
        result = self.run(
            "-t",
            "-f",
            "IN-USE,SSID,SIGNAL,SECURITY,BARS,CHAN,BSSID",
            "device",
            "wifi",
            "list",
            "ifname",
            self.wifi_ifname,
            "--rescan",
            "no",
            timeout=20,
        )
        if not result.ok:
            return []
        deduped: dict[str, dict[str, Any]] = {}
        hidden_index = 0
        for line in result.stdout.splitlines():
            if not line.strip():
                continue
            fields = split_nmcli_terse(line)
            while len(fields) < 7:
                fields.append("")
            in_use, ssid, signal, security, bars, chan, bssid = fields[:7]
            key = ssid or f"__hidden__{hidden_index}"
            try:
                signal_value = int(signal or 0)
            except ValueError:
                signal_value = 0
            row = {
                "in_use": in_use == "*",
                "ssid": ssid,
                "signal": signal_value,
                "security": security or "open",
                "bars": bars,
                "channel": chan,
                "bssid": bssid,
                "hidden": not bool(ssid),
            }
            if key not in deduped or signal_value > int(deduped[key].get("signal", 0)):
                deduped[key] = row
            if not ssid:
                hidden_index += 1
        networks = list(deduped.values())
        networks.sort(key=lambda item: (item["hidden"], -item["signal"], item["ssid"].lower() if item["ssid"] else ""))
        return networks

    def ensure_wifi_radio_on(self) -> CommandResult:
        return self.run("radio", "wifi", "on", timeout=15)

    def ensure_hotspot_profile(self, ssid: str, password: str) -> CommandResult:
        self.ensure_wifi_radio_on()
        if not self.connection_profile_exists(self.hotspot_name):
            created = self.run(
                "connection",
                "add",
                "type",
                "wifi",
                "ifname",
                self.wifi_ifname,
                "con-name",
                self.hotspot_name,
                "autoconnect",
                "no",
                "ssid",
                ssid,
                timeout=20,
            )
            if not created.ok:
                return created
        modify_calls = [
            ("connection", "modify", self.hotspot_name, "connection.autoconnect", "no"),
            ("connection", "modify", self.hotspot_name, "connection.autoconnect-priority", "-999"),
            ("connection", "modify", self.hotspot_name, "wifi.mode", "ap"),
            ("connection", "modify", self.hotspot_name, "wifi.band", self.hotspot_band),
            ("connection", "modify", self.hotspot_name, "wifi.channel", self.hotspot_channel),
            ("connection", "modify", self.hotspot_name, "wifi.ssid", ssid),
            ("connection", "modify", self.hotspot_name, "ipv4.method", "shared"),
            ("connection", "modify", self.hotspot_name, "ipv4.addresses", self.hotspot_ip),
            ("connection", "modify", self.hotspot_name, "ipv6.method", "ignore"),
            ("connection", "modify", self.hotspot_name, "wifi-sec.key-mgmt", "wpa-psk"),
            ("connection", "modify", self.hotspot_name, "wifi-sec.psk", password),
        ]
        for args in modify_calls:
            result = self.run(*args, timeout=15)
            if not result.ok:
                return result
        return CommandResult(ok=True)

    def start_hotspot(self, ssid: str, password: str) -> CommandResult:
        prepared = self.ensure_hotspot_profile(ssid=ssid, password=password)
        if not prepared.ok:
            return prepared
        return self.run("connection", "up", self.hotspot_name, timeout=40)

    def stop_hotspot(self) -> CommandResult:
        if self.connection_profile_exists(self.hotspot_name):
            result = self.run("connection", "down", self.hotspot_name, timeout=20)
            if result.ok:
                return result
        return self.run("device", "disconnect", self.wifi_ifname, timeout=20)

    def forget_connection(self, name: str) -> CommandResult:
        if not name or name == self.hotspot_name:
            return CommandResult(ok=False, stderr="Refusing to remove hotspot profile.")
        return self.run("connection", "delete", name, timeout=20)

    def connect_to_wifi(self, ssid: str, password: str, hidden: bool = False) -> CommandResult:
        ssid = str(ssid or "").strip()
        password = str(password or "")
        if not ssid:
            return CommandResult(ok=False, stderr="SSID is required.")
        if not password and not self.network_cfg.get("allow_open_wifi", True):
            return CommandResult(ok=False, stderr="Open networks are disabled in settings.")

        self.ensure_wifi_radio_on()
        self.stop_hotspot()

        profile_name = ssid
        if self.connection_profile_exists(profile_name):
            update_args = [
                "connection",
                "modify",
                profile_name,
                "connection.autoconnect",
                "yes",
                "connection.autoconnect-priority",
                str(self.network_cfg["known_wifi_priority"]),
            ]
            result = self.run(*update_args, timeout=15)
            if not result.ok:
                return result
            result = self.run("connection", "modify", profile_name, "wifi.hidden", "yes" if hidden else "no", timeout=15)
            if not result.ok:
                return result
            if password:
                result = self.run(
                    "connection",
                    "modify",
                    profile_name,
                    "wifi-sec.key-mgmt",
                    "wpa-psk",
                    "wifi-sec.psk",
                    password,
                    timeout=15,
                )
                if not result.ok:
                    return result
            return self.run("connection", "up", profile_name, "ifname", self.wifi_ifname, timeout=self.server_cfg["connection_wait_s"] + 15)

        args = [
            "--wait",
            str(self.server_cfg["connection_wait_s"]),
            "device",
            "wifi",
            "connect",
            ssid,
            "ifname",
            self.wifi_ifname,
            "name",
            profile_name,
        ]
        if hidden:
            args.extend(["hidden", "yes"])
        if password:
            args.extend(["password", password])
        result = self.run(*args, timeout=self.server_cfg["connection_wait_s"] + 20)
        if not result.ok:
            return result
        self.run(
            "connection",
            "modify",
            profile_name,
            "connection.autoconnect",
            "yes",
            "connection.autoconnect-priority",
            str(self.network_cfg["known_wifi_priority"]),
            timeout=15,
        )
        return result

    def get_runtime_snapshot(self, hotspot_ssid: str) -> dict[str, Any]:
        devices = self.get_device_status()
        ip_addresses = self.get_ip_addresses()
        hotspot_clients = self.get_hotspot_clients()
        wifi_device = next((row for row in devices if row["device"] == self.wifi_ifname), None)
        ethernet_device = next((row for row in devices if row["device"] == self.ethernet_ifname), None)

        wifi_connected = bool(wifi_device and wifi_device["state"] == "connected")
        hotspot_active = bool(wifi_connected and wifi_device and wifi_device.get("connection") == self.hotspot_name)
        any_non_hotspot_connection = any(
            row["state"] == "connected" and row.get("connection") and row.get("connection") != self.hotspot_name
            for row in devices
        )
        active_wifi_name = wifi_device.get("connection", "") if wifi_connected and wifi_device else ""
        info = {
            "nmcli_available": self.nmcli_available(),
            "devices": devices,
            "wifi": {
                "interface": self.wifi_ifname,
                "connected": wifi_connected,
                "connection": active_wifi_name,
                "hotspot_active": hotspot_active,
                "hotspot_name": self.hotspot_name,
                "hotspot_ssid": hotspot_ssid,
                "hotspot_url": self.network_cfg["hotspot_url"],
                "hotspot_password": self.network_cfg["hotspot_password"],
            },
            "ethernet": ethernet_device or {},
            "ip_addresses": ip_addresses,
            "hotspot_clients": hotspot_clients,
            "any_non_hotspot_connection": any_non_hotspot_connection,
        }
        if hotspot_active:
            info["phase"] = "hotspot"
            if hotspot_clients:
                info["message"] = "Hotspot is active and a client has joined. Open the setup page to continue."
            else:
                info["message"] = "Hotspot is active. Connect from your phone and open the setup page."
        elif any_non_hotspot_connection:
            info["phase"] = "connected"
            info["message"] = "Pi is connected to a saved network."
        elif self.nmcli_available():
            info["phase"] = "idle"
            info["message"] = "No active network yet. PiBooter can start the setup hotspot."
        else:
            info["phase"] = "error"
            info["message"] = "nmcli / NetworkManager is not available on this Pi."
        return info
