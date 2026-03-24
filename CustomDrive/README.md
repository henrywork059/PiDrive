# CustomDrive

CustomDrive now includes a PiServer-style **GUI control web** entrypoint for manual driving and arm testing.

## Run the GUI control page

From the `CustomDrive` folder:

```bash
python run_custom_drive_gui.py
```

Open the printed URL, usually:

```text
http://127.0.0.1:5050
```

or from another device on the same network:

```text
http://<pi-ip>:5050
```

## What this GUI includes

- live camera preview using PiServer camera services
- real manual drag-pad driving through PiServer motor/control services
- separate **Drive Settings** and **Style Settings** overlay windows
- responsive default layout that stays inside the browser window more reliably
- left-side arm panel with:
  - Up
  - Down
  - Open
  - Close

## Arm control notes

The GUI arm panel uses `CustomDrive/config/manual_control.json`.

The current default setup supports:

- primary lift servo on channel `0`
- optional secondary lift servo on channel `1`
- optional separate grip servo on channel `2`

Up and Down move the lift by **1° every 0.1 seconds** while the button is held.

## Drive settings

The **Drive Settings** window controls:

- max throttle
- steer mix
- steer bias
- left motor direction
- right motor direction
- steering direction
- left/right max speed
- left/right bias

These are applied through PiServer motor/config flow and saved back into:

- `PiServer/config/runtime.json`

## Style settings

The **Style Settings** window uses the same PiServer theme-variable method and stores custom style overrides in browser local storage.
