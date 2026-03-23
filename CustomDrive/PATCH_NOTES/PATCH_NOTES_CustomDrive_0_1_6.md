# CustomDrive 0_1_6 Patch Notes

## Summary
This patch changes the **manual control app** to default to **port 5050** instead of 5060 so it is easier to reach and consistent with the main CustomDrive GUI.

## Files changed
- `CustomDrive/run_custom_drive_manual.py`
- `CustomDrive/custom_drive/manual_control_config.py`
- `CustomDrive/config/manual_control.json`
- `CustomDrive/README.md`

## What changed
- Changed the built-in manual control default port from **5060** to **5050**.
- Changed the saved default in `CustomDrive/config/manual_control.json` to **5050**.
- Updated the README so the browser URL matches the new default.

## Why
The manual controller was still carrying over an older default of 5060 while the rest of CustomDrive already used 5050. This mismatch made launch instructions and browser testing more confusing than necessary.

## Important note
Only one app can use port **5050** at a time. If the main CustomDrive GUI is already running on 5050, the manual control app must either stop the other app first or be started with a different port override such as:

```bash
python run_custom_drive_manual.py --port 5060
```

## Verification
- Reviewed all manual-control references to the old 5060 default.
- Updated code, config, and README to the same default port.
