"""Open a dedicated local Chromium session and export redacted console metadata."""
import argparse
import json
from pathlib import Path
import sys
import time

import requests
from playwright.sync_api import sync_playwright, Error

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from pisd_emulator.browser_observer import BrowserObserver


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--control-port", type=int, default=8760)
    parser.add_argument("--seconds", type=int, default=300)
    parser.add_argument("--output", type=Path, required=True, help="New JSON file; never overwritten.")
    args = parser.parse_args()
    if not 1 <= args.control_port <= 65535 or not 1 <= args.seconds <= 3600:
        parser.error("Port must be 1–65535 and duration 1–3600 seconds.")
    if args.output.exists():
        parser.error("Output already exists.")
    origin = f"http://127.0.0.1:{args.control_port}"
    try:
        with requests.Session() as session:
            session.trust_env = False
            response = session.get(origin + "/api/status", timeout=5, allow_redirects=False)
            response.raise_for_status()
            state = response.json()
        if (response.status_code != 200 or state.get("runtime_mode") != "emulator"
                or state.get("hardware_enabled") is not False or state.get("gpio_access") is not False):
            raise ValueError("Not an isolated emulator.")
        observer = BrowserObserver(args.control_port, state["port"])
    except (requests.RequestException, ValueError, KeyError, TypeError, AttributeError) as exc:
        parser.error(f"Start the local emulator first; status check failed ({type(exc).__name__}).")
    print("Capture only covers this new Chromium window and its configured PiSD port.")
    print("Use STOP before closing; observation does not stop or control the runtime.")
    try:
        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=False)
            try:
                context = browser.new_context()
                observer.attach(context)
                page = context.new_page()
                page.goto(origin, timeout=15000)
                deadline = time.monotonic() + args.seconds
                while context.pages and time.monotonic() < deadline:
                    try:
                        context.pages[0].wait_for_timeout(200)
                    except Error:
                        if not browser.is_connected():
                            break
                        if not context.pages:
                            break
            finally:
                browser.close()
    except KeyboardInterrupt:
        pass
    finally:
        with args.output.open("x", encoding="utf-8") as out:
            json.dump(observer.report(), out, indent=2)
    print(f"Report saved: {args.output}")


if __name__ == "__main__":
    main()
