# PiSD Testing Server GUI

## Purpose

`PiSD_0_2_1` adds a temporary testing server GUI before the final PiDrive/PiServer-style GUI is built.

This page is not intended to be the final driving interface. Its job is to make every important service and API call easy to test from a browser:

- camera start/stop/frame/config/capabilities
- camera settings apply
- motor settings apply
- one-by-one motor channel test
- emergency stop
- custom API calls
- status and error-code visibility

## Run

From inside `PiSD/`:

```bash
python3 PiSD.py --host 0.0.0.0 --port 5050 --hardware
```

Open:

```text
http://<pi-ip>:5050/
http://<pi-ip>:5050/testing
```

Both routes show the same testing GUI.

## Safety behaviour

The motor channel test panel is locked by default.

Real motor movement requires this checkbox in the page:

```text
Wheels lifted, enable real output
```

The backend still enforces the safety rule. If the PiSD server was started with `--hardware` and the request does not include `enable_motor_output: true`, `/api/motor/test-channel` returns a safety refusal with:

```text
PISD-MOT-008
```

## What to test before the final GUI

### 1. Camera API calls

Use the Camera Preview card:

1. Click `Start camera`.
2. Click `Refresh frame`.
3. Click `Read camera config`.
4. Click `Read capabilities`.
5. Confirm the response panel reports `PISD-OK-000`.

The default visual path should remain:

```text
capture_source=request
```

The confirmed raw array/CV path should remain:

```text
array_color_order=rgb
```

### 2. Camera settings apply

Change one setting at a time first, for example:

```text
width: 320
height: 240
preview_quality: 60
```

Click `Apply camera settings` and confirm:

```text
PISD-OK-000
```

Then refresh the frame.

### 3. Motor settings apply

Change direction or trim values and click `Apply motor settings`.

This must not move the wheels. It only tests `/api/motor/apply`.

### 4. One-by-one motor channel test

Lift the wheels.

Set:

```text
side: left or right
direction: 1 or -1
speed: 0.10 to 0.20
duration: 0.25
```

Select the arming checkbox only when the wheels are lifted, then click `Run channel test`.

Expected successful response:

```text
PISD-OK-000
```

Expected safe refusal when not armed:

```text
PISD-MOT-008
```

### 5. Custom API caller

Click an endpoint in the manifest list, or manually enter an endpoint such as:

```text
GET /api/status
POST /api/control/stop
POST /api/motor/test-channel
```

For POST requests, edit the JSON body box.

## Local validation command

The standard validation script now checks the testing GUI page and its endpoint manifest:

```bash
python3 scripts/run_standard_validation.py --skip-camera --skip-motor
```

Expected lines include:

```text
OK   PISD-OK-000   api.testing_gui.page - testing GUI page loaded
OK   PISD-OK-000   api.testing_gui.manifest - testing GUI manifest loaded
```

## Files

```text
PiSD/pisd/web/templates/testing_server.html
PiSD/pisd/web/static/css/testing_server.css
PiSD/pisd/web/static/js/testing_server.js
```
