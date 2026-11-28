"""CI-only native display qualification. No registry persistence or virtual screen.
Try an enumerated supported mode, verify actual Qt work area, restore on exit.
A blocked report is not a geometry PASS. Existing captures are independent.
"""
from __future__ import annotations
import argparse
import ctypes as C
from ctypes import wintypes as W
import json
import os
from pathlib import Path
import subprocess
import sys
import time

class DisplayFields(C.Structure):
    _fields_ = [("x", W.LONG), ("y", W.LONG), ("orientation", W.DWORD), ("fixed_output", W.DWORD)]

class DevMode(C.Structure):
    _fields_ = [("device", W.WCHAR * 32), ("spec", W.WORD), ("driver", W.WORD),
                ("size", W.WORD), ("extra", W.WORD), ("fields", W.DWORD),
                ("display", DisplayFields), ("color", C.c_short), ("duplex", C.c_short),
                ("yres", C.c_short), ("tt", C.c_short), ("collate", C.c_short),
                ("form", W.WCHAR * 32), ("logpixels", W.WORD), ("bpp", W.DWORD),
                ("width", W.DWORD), ("height", W.DWORD), ("flags", W.DWORD),
                ("frequency", W.DWORD), ("icm_method", W.DWORD), ("icm_intent", W.DWORD),
                ("media", W.DWORD), ("dither", W.DWORD), ("reserved1", W.DWORD),
                ("reserved2", W.DWORD), ("panning_w", W.DWORD), ("panning_h", W.DWORD)]

def main():
    parser = argparse.ArgumentParser()
    for key in ("baseline", "source", "output"):
        parser.add_argument("--"+key, type=Path, required=True)
    parser.add_argument("--baseline-sha", required=True)
    parser.add_argument("--revision", required=True)
    args = parser.parse_args()
    if sys.platform != "win32" or os.environ.get("GITHUB_ACTIONS") != "true" or os.environ.get("RUNNER_OS") != "Windows":
        raise RuntimeError("Native GitHub-hosted Windows CI only")
    assert C.sizeof(DevMode) == 220, C.sizeof(DevMode)
    out = args.output.resolve()
    out.mkdir(parents=True, exist_ok=True)
    report = {"revision": args.revision, "baseline_sha": args.baseline_sha,
              "status": "blocked", "attempts": [], "profiles": []}
    def write():
        (out/"display_report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    user32 = C.WinDLL("user32", use_last_error=True)
    enum = user32.EnumDisplaySettingsW
    enum.argtypes = [W.LPCWSTR, W.DWORD, C.POINTER(DevMode)]
    enum.restype = W.BOOL
    change = user32.ChangeDisplaySettingsW
    change.argtypes = [C.POINTER(DevMode), W.DWORD]
    change.restype = W.LONG
    def get(index):
        mode = DevMode()
        mode.size = C.sizeof(mode)
        return mode if enum(None, index & 0xffffffff, C.byref(mode)) else None
    def describe(m):
        return {"width": m.width, "height": m.height, "bpp": m.bpp, "hz": m.frequency,
                "orientation": m.display.orientation}
    def screen(scale=None):
        env = os.environ.copy()
        if scale is not None:
            env["QT_SCALE_FACTOR"] = str(scale)
        probe = ("import json; from PySide6.QtWidgets import QApplication; "
                 "a=QApplication([]); s=a.primaryScreen(); g=s.availableGeometry(); "
                 "print(json.dumps(dict(platform=a.platformName(), available=[g.width(),g.height()], "
                 "dpr=s.devicePixelRatio(), dpi=s.logicalDotsPerInch())))")
        result = subprocess.run([sys.executable,"-c",probe], env=env, check=True,
                                capture_output=True, text=True, timeout=30)
        return json.loads(result.stdout.strip().splitlines()[-1])
    original = get(-1)
    if original is None:
        report["reason"] = "Current display mode unavailable"
        write()
        raise RuntimeError(report["reason"])
    report["original"] = describe(original)
    report["initial_qt"] = screen()
    candidates = []
    for i in range(4096):
        mode = get(i)
        if mode is None:
            break
        candidates.append(mode)
    report["supported_modes"] = [describe(m) for m in candidates]
    write()
    changed = False
    try:
        if min(report["initial_qt"]["available"][0]-1460, report["initial_qt"]["available"][1]-950) < 0:
            choices = sorted((m for m in candidates if m.width >= 1600 and m.height >= 1000
                              and m.bpp == original.bpp and m.display.orientation == original.display.orientation),
                             key=lambda m:(-m.width*m.height, abs(m.frequency-original.frequency)))
            for mode in choices:
                result = change(C.byref(mode), 2)  # CDS_TEST; no apply
                item = {"mode": describe(mode), "test_result": result}
                report["attempts"].append(item)
                if result == 0:
                    result = change(C.byref(mode), 0)  # temporary, no registry update
                    item["apply_result"] = result
                    if result == 0:
                        changed = True
                        time.sleep(2)
                        item["actual_qt"] = screen()
                        write()
                        if item["actual_qt"]["available"][0] >= 1460 and item["actual_qt"]["available"][1] >= 950:
                            break
                write()
        actual = screen()
        report["actual_qt"] = actual
        if actual["platform"] != "windows" or actual["available"][0] < 1460 or actual["available"][1] < 950:
            report["reason"] = "No tested native mode provides sufficient logical desktop for original sizes"
            write()
            raise RuntimeError(report["reason"])
        runner = Path(__file__).with_name("check_rc09_trainer.py").resolve()
        for name, source, sha, theme in (
            ("before",args.baseline,args.baseline_sha,None),
            ("after",args.source,args.revision,None),
            ("dark",args.source,args.revision,"dark"),
            ("light",args.source,args.revision,"light")):
            cmd = [sys.executable,str(runner),"--source",str(source.resolve()),"--output",str(out/name),
                   "--revision",sha,"--require-requested-geometry"]
            if name != "before": cmd += ["--require-readable-status"]
            if theme: cmd += ["--theme",theme]
            report["profiles"].append({"name":name,"status":"running"})
            write()
            subprocess.run(cmd,check=True,timeout=180)
            report["profiles"][-1]["status"] = "passed"
            write()
        report["status"] = "qualified"
        # An explicit Qt scale override is a separate stress test, not proof
        # of an actual high-DPI monitor. Only run if logical work area fits.
        scaled = screen(1.25)
        report["qt_scale_125_probe"] = scaled
        if scaled["available"][0] >= 1460 and scaled["available"][1] >= 950:
            env = os.environ.copy()
            env["QT_SCALE_FACTOR"] = "1.25"
            subprocess.run([sys.executable,str(runner),"--source",str(args.source.resolve()),
                            "--output",str(out/"qt-scale-125"),"--revision",args.revision,
                            "--require-readable-status","--require-requested-geometry","--theme","dark"],
                            env=env,check=True,timeout=180)
            report["qt_scale_125_status"] = "passed simulated scale override"
        elif scaled["available"][0] >= 1040 and scaled["available"][1] >= 815:
            env = os.environ.copy()
            env["QT_SCALE_FACTOR"] = "1.25"
            for theme in ("dark", "light"):
                subprocess.run([sys.executable,str(runner),"--source",str(args.source.resolve()),
                                "--output",str(out/("qt-scale-125-"+theme)),"--revision",args.revision,
                                "--require-readable-status","--require-requested-geometry","--small-only","--theme",theme],
                               env=env,check=True,timeout=180)
            report["qt_scale_125_status"] = "1024x768 only passed simulated scale override; 1440x900 blocked"
        else:
            report["qt_scale_125_status"] = "blocked by logical work area"
    except Exception as exc:
        report["status"] = "failed"
        report["error"] = repr(exc)
        raise
    finally:
        if changed:
            report["restore_result"] = change(C.byref(original),0)
            time.sleep(1)
            restored = get(-1)
            report["restored_mode"] = describe(restored) if restored is not None else None
            write()
            if report["restore_result"] != 0 or report["restored_mode"] != report["original"]:
                raise RuntimeError("Native display mode restoration failed")
        write()

if __name__ == "__main__":
    main()
