"""Bounded, validated saved environment definitions; no executable scenarios."""
from pathlib import Path
import json
import math
import os
import re
import tempfile

DEFAULT = {"markings": "dashed", "edge_lines": True, "lighting": "day"}
MAX_PROFILES = 32
MAX_STORE_BYTES = 256 * 1024

def number(value, low, high, label):
    if type(value) not in (int, float) or not math.isfinite(value) or not low <= value <= high:
        raise ValueError(f"{label} must be a finite number in [{low}, {high}].")
    return float(value)

def validate_profile(data):
    if not isinstance(data, dict) or set(data) != {"name", "segments", "road_width_m", "markings", "edge_lines", "lighting", "obstacles"}:
        raise ValueError("Supply exactly name, segments, road_width_m, markings, edge_lines, lighting, obstacles.")
    name = data["name"]
    if not isinstance(name, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9 _-]{0,39}", name):
        raise ValueError("Name must be 1–40 ASCII letters, digits, spaces, underscore or hyphen.")
    segments = data["segments"]
    if not isinstance(segments, list) or not 1 <= len(segments) <= 24:
        raise ValueError("Supply 1–24 track segments.")
    clean = []
    for segment in segments:
        if not isinstance(segment, dict) or set(segment) != {"length_m", "curvature"}:
            raise ValueError("A segment requires length_m and curvature (1/m).")
        length = number(segment["length_m"], 2, 120, "Segment length")
        if length != int(length):
            raise ValueError("Segment length must be a whole number of metres.")
        clean.append({"length_m": int(length), "curvature": number(segment["curvature"], -.18, .18, "Curvature")})
    total = sum(s["length_m"] for s in clean)
    if not 40 <= total <= 240:
        raise ValueError("Total track length must be 40–240 m.")
    width = number(data["road_width_m"], .4, 4, "Road width")
    if data["markings"] not in ("dashed", "solid", "none") or data["lighting"] not in ("day", "dusk", "night") or type(data["edge_lines"]) is not bool:
        raise ValueError("Invalid markings, lighting or edge_lines.")
    obstacles = data["obstacles"]
    if not isinstance(obstacles, list) or len(obstacles) > 64:
        raise ValueError("Supply at most 64 obstacles.")
    normalized = []
    for obstacle in obstacles:
        if not isinstance(obstacle, dict) or set(obstacle) != {"station_m", "lateral_m", "kind"} or obstacle["kind"] not in ("cone", "bollard"):
            raise ValueError("Obstacle requires station_m, lateral_m and cone/bollard kind.")
        normalized.append({"station_m": number(obstacle["station_m"], 2, total-1, "Obstacle station"),
                           "lateral_m": number(obstacle["lateral_m"], -width/2, width/2, "Obstacle lateral offset"),
                           "kind": obstacle["kind"]})
    return {"name":name,"segments":clean,"road_width_m":width,"markings":data["markings"],
            "edge_lines":data["edge_lines"],"lighting":data["lighting"],"obstacles":normalized}

class EnvironmentStore:
    def __init__(self, workspace):
        self.path = Path(workspace) / "config" / "emulator_environments.json"

    def read(self):
        if not self.path.exists():
            return {}
        try:
            with self.path.open("rb") as handle:
                raw = handle.read(MAX_STORE_BYTES+1)
            if len(raw) > MAX_STORE_BYTES:
                raise ValueError("Saved environment store exceeds size limit.")
            data = json.loads(raw)
            if not isinstance(data, dict) or data.get("schema") != 1 or not isinstance(data.get("profiles"), dict):
                raise ValueError("Unknown environment store schema.")
            profiles = data["profiles"]
            if len(profiles)>MAX_PROFILES:
                raise ValueError("Too many saved environments.")
            checked = {}
            for key,value in profiles.items():
                profile=validate_profile(value)
                if key != profile["name"]:
                    raise ValueError("Environment key/name mismatch.")
                checked[key]=profile
            return checked
        except (OSError, ValueError, TypeError, OverflowError) as exc:
            raise ValueError("Saved environment store unreadable; original file preserved.") from exc

    def save(self, profile, replace=False):
        profile = validate_profile(profile)
        if type(replace) is not bool:
            raise ValueError("replace must be a boolean.")
        profiles = self.read()
        name = profile["name"]
        if name in profiles and not replace:
            raise ValueError("Environment already exists; explicit replacement required.")
        if name not in profiles and len(profiles)>=MAX_PROFILES:
            raise ValueError("Saved environment limit reached.")
        profiles[name]=profile
        raw=json.dumps({"schema":1,"profiles":profiles},indent=2,sort_keys=True,allow_nan=False).encode()
        if len(raw)>MAX_STORE_BYTES:
            raise ValueError("Saved environment store exceeds size limit.")
        self.path.parent.mkdir(parents=True,exist_ok=True)
        fd,temp=tempfile.mkstemp(prefix=".environments-",dir=self.path.parent)
        try:
            with os.fdopen(fd,"wb") as handle:
                handle.write(raw)
            os.replace(temp,self.path)
        finally:
            if os.path.exists(temp):
                os.unlink(temp)
        return profile
