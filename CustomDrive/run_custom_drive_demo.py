from __future__ import annotations

import argparse
import time

from custom_drive.mission_state import MissionState
from custom_drive.runtime_factory import create_runtime


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run CustomDrive in sim or live mode.")
    parser.add_argument("--mode", choices=("sim", "live"), default="sim", help="Mission runtime mode.")
    parser.add_argument("--cycles", type=int, default=2, help="Maximum pickup/drop cycles.")
    parser.add_argument("--tick", type=float, default=None, help="Loop period override in seconds.")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    runtime = create_runtime(mode=args.mode, max_cycles=args.cycles)

    last_state = None
    print("=== CustomDrive started ===")
    print(f"Requested mode: {args.mode} | effective mode: {runtime.mode}")
    fallback_reason = getattr(runtime, "fallback_reason", "")
    if fallback_reason:
        print(f"Mode note: {fallback_reason}")

    runtime.start()
    tick = args.tick
    if tick is None:
        settings = getattr(runtime, "get_settings", lambda: {})()
        runtime_cfg = settings.get("runtime", {}) if isinstance(settings, dict) else {}
        tick = float(runtime_cfg.get("tick_s_live" if runtime.mode == "live" else "tick_s_sim", 0.1 if runtime.mode == "live" else 0.2))

    try:
        while True:
            snapshot = runtime.step()

            if snapshot["state"] != last_state:
                print(
                    f"\n[STATE] {snapshot['state']} | detail={snapshot['detail']} "
                    f"| retries={snapshot['retries']} | cycles={snapshot['completed_cycles']}"
                )
                last_state = snapshot["state"]

            cmd = snapshot["last_command"]
            line = f"  cmd: steering={cmd['steering']:+.2f} throttle={cmd['throttle']:+.2f} note={cmd['note']}"
            if runtime.mode == "live":
                cam = snapshot.get("camera", {})
                line += f" | camera={cam.get('backend', 'unknown')} fps={cam.get('fps', 0.0):.1f}"
                if cam.get("error"):
                    line += f" | camera_error={cam['error']}"
            print(line)

            if snapshot["state"] in (MissionState.COMPLETE.value, MissionState.FAILED.value):
                break
            time.sleep(max(0.02, float(tick)))
    finally:
        closer = getattr(runtime, "close", None)
        if callable(closer):
            closer()

    print(f"\n=== Run finished with state: {snapshot['state']} ===")
    print(f"Completed cycles: {snapshot['completed_cycles']}")


if __name__ == "__main__":
    main()
