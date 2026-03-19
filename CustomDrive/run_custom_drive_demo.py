from __future__ import annotations

import argparse
import time

from custom_drive.mission_state import MissionState
from custom_drive.run_settings import load_run_settings
from custom_drive.runtime_factory import create_runtime



def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description='Run CustomDrive in headless mode without GUI.')
    parser.add_argument('--mode', choices=('sim', 'live'), default=None, help='Runtime backend. Defaults to config/run_settings.json.')
    parser.add_argument('--cycles', type=int, default=None, help='Maximum pickup/drop cycles. Defaults to config/run_settings.json.')
    parser.add_argument('--tick', type=float, default=None, help='Loop period override in seconds. Defaults to config/run_settings.json.')
    parser.add_argument('--show-debug', action='store_true', help='Print debug trace entries when the mission changes state.')
    return parser



def main() -> None:
    args = build_parser().parse_args()
    run_settings = load_run_settings()
    runtime_mode = args.mode or str(run_settings.get('runtime_mode', 'sim'))
    max_cycles = int(args.cycles if args.cycles is not None else run_settings.get('max_cycles', 2))
    tick = args.tick
    if tick is None:
        tick = float(run_settings.get('headless_tick_s', 0.2))

    runtime = create_runtime(mode=runtime_mode, max_cycles=max_cycles)

    last_state = None
    last_debug_count = 0
    snapshot = None
    print('=== CustomDrive headless run started ===')
    print('Launch mode: headless')
    print(f'Runtime backend: requested={runtime_mode} effective={runtime.mode}')
    print(f'Max cycles: {max_cycles} | tick={tick:.3f}s')
    print('Shared run settings file: CustomDrive/config/run_settings.json')
    fallback_reason = getattr(runtime, 'fallback_reason', '')
    if fallback_reason:
        print(f'Mode note: {fallback_reason}')

    runtime.start()

    try:
        while True:
            snapshot = runtime.step()

            if snapshot['state'] != last_state:
                print(
                    f"\n[STATE] {snapshot['state']} | detail={snapshot['detail']} "
                    f"| retries={snapshot['retries']} | cycles={snapshot['completed_cycles']}"
                )
                if args.show_debug:
                    debug_events = snapshot.get('debug_events') or []
                    for entry in debug_events[last_debug_count:]:
                        extra = ' '.join(
                            f"{k}={v!r}" for k, v in entry.items()
                            if k not in {'timestamp', 'level', 'type', 'message'}
                        )
                        print(
                            f"  [DEBUG {entry.get('level', 'info').upper()}] {entry.get('type', 'runtime')}: {entry.get('message', '')}"
                            + (f" | {extra}" if extra else '')
                        )
                    last_debug_count = len(debug_events)
                last_state = snapshot['state']

            cmd = snapshot['last_command']
            line = f"  cmd: steering={cmd['steering']:+.2f} throttle={cmd['throttle']:+.2f} note={cmd['note']}"
            if runtime.mode == 'live':
                cam = snapshot.get('camera', {})
                line += f" | camera={cam.get('backend', 'unknown')} fps={cam.get('fps', 0.0):.1f}"
                if cam.get('error'):
                    line += f" | camera_error={cam['error']}"
            if snapshot.get('last_error'):
                line += f" | last_error={snapshot['last_error']}"
            print(line)

            if snapshot['state'] in (MissionState.COMPLETE.value, MissionState.FAILED.value):
                break
            time.sleep(max(0.02, float(tick)))
    except KeyboardInterrupt:
        print('\nInterrupted by user.')
    finally:
        closer = getattr(runtime, 'close', None)
        if callable(closer):
            closer()

    final_state = snapshot['state'] if isinstance(snapshot, dict) else 'unknown'
    completed_cycles = snapshot.get('completed_cycles', 0) if isinstance(snapshot, dict) else 0
    print(f"\n=== Run finished with state: {final_state} ===")
    print(f'Completed cycles: {completed_cycles}')


if __name__ == '__main__':
    main()
