from __future__ import annotations

import argparse
import time

from custom_drive.demo_runtime import DemoMissionRuntime
from custom_drive.mission_state import MissionState


def main() -> None:
    parser = argparse.ArgumentParser(description="Run CustomDrive mission without GUI.")
    parser.add_argument("--mode", choices=["sim", "live"], default="sim", help="sim = scripted perception, live = camera+motor")
    parser.add_argument("--cycles", type=int, default=2, help="Maximum mission cycles")
    parser.add_argument("--tick", type=float, default=None, help="Loop sleep interval (seconds)")
    parser.add_argument("--cam-width", type=int, default=None)
    parser.add_argument("--cam-height", type=int, default=None)
    parser.add_argument("--cam-fps", type=int, default=None)
    parser.add_argument("--left-max-speed", type=float, default=None)
    parser.add_argument("--right-max-speed", type=float, default=None)
    parser.add_argument("--save-settings", action="store_true", help="Persist provided camera/motor overrides")
    args = parser.parse_args()

    runtime = DemoMissionRuntime(max_cycles=args.cycles, mode=args.mode)

    if args.save_settings:
        settings = runtime.get_settings()
        if args.cam_width is not None:
            settings.setdefault("camera", {})["width"] = args.cam_width
        if args.cam_height is not None:
            settings.setdefault("camera", {})["height"] = args.cam_height
        if args.cam_fps is not None:
            settings.setdefault("camera", {})["fps"] = args.cam_fps
        if args.left_max_speed is not None:
            settings.setdefault("motor", {})["left_max_speed"] = args.left_max_speed
        if args.right_max_speed is not None:
            settings.setdefault("motor", {})["right_max_speed"] = args.right_max_speed
        runtime.save_settings(settings)
        runtime.reset(max_cycles=args.cycles)

    runtime.start()
    last_state = None
    print(f"=== CustomDrive demo started (mode={runtime.mode}) ===")

    while True:
        snapshot = runtime.step()
        if snapshot["state"] != last_state:
            print(
                f"\n[STATE] {snapshot['state']} | detail={snapshot['detail']} "
                f"| retries={snapshot['retries']} | cycles={snapshot['completed_cycles']}"
            )
            last_state = snapshot["state"]

        cmd = snapshot["last_command"]
        print(f"  cmd: steering={cmd['steering']:+.2f} throttle={cmd['throttle']:+.2f} note={cmd['note']}")

        if snapshot["state"] in (MissionState.COMPLETE.value, MissionState.FAILED.value):
            break
        time.sleep(runtime.tick_s if args.tick is None else max(0.02, args.tick))

    print(f"\n=== Demo finished with state: {snapshot['state']} ===")
    print(f"Completed cycles: {snapshot['completed_cycles']}")
    runtime.shutdown()


if __name__ == "__main__":
    main()
