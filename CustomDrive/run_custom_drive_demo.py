from __future__ import annotations

import time

from custom_drive.demo_runtime import DemoMissionRuntime
from custom_drive.mission_state import MissionState


def main() -> None:
    runtime = DemoMissionRuntime(max_cycles=2)
    runtime.start()

    last_state = None
    print("=== CustomDrive demo started ===")

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
        time.sleep(0.2)

    print(f"\n=== Demo finished with state: {snapshot['state']} ===")
    print(f"Completed cycles: {snapshot['completed_cycles']}")


if __name__ == "__main__":
    main()
