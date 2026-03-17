# PATCH NOTES — PiServer 0_2_8

## Summary
This patch fixes the PiServer motor-settings workflow for steering-direction calibration and improves how saved motor defaults are carried in the runtime config.

Main user-facing result:
- you can now flip **turn direction** directly in the Motor tab without breaking forward/reverse calibration
- the steering-direction choice is now included in the saved motor config
- the default runtime config now contains a full motor block, so the motor page starts from an explicit saved structure instead of relying on implicit defaults

---

## Problem reported
You reported two linked issues:

1. motor settings did not appear to save/apply in a useful way
2. the car turned right when steering left, and you wanted a way to change turn direction

---

## Root cause
The existing Motor tab only exposed:
- left motor direction
- right motor direction
- left/right max speed
- left/right bias

That works for wiring calibration, but it does **not** give a clean dedicated control for **steering sign**.

So if:
- forward/backward wiring was already correct
- but steering felt inverted

changing left/right motor directions could easily create confusion because those settings affect the underlying motor polarity, not just the steering interpretation.

Also, the default `config/runtime.json` did not include a `motor` block, so the runtime started from implicit in-memory defaults until a save happened later.

---

## What I changed

### 1) Added a dedicated steering-direction motor setting
A new motor config field is now supported:
- `steering_direction`

Values:
- `1` = normal steering (`left input -> car turns left`)
- `-1` = reversed steering (`left input -> car turns right`)

This is applied inside `MotorService._map_drive()` before wheel mixing.

### 2) Exposed steering direction in the web UI
The Motor tab now includes a new selector:
- **Steering direction**
  - Normal (left = car left)
  - Reverse (left = car right)

This makes the fix explicit and avoids forcing you to misuse left/right motor polarity just to correct turn direction.

### 3) Saved steering direction into runtime config
The motor config returned by the backend now includes:
- `steering_direction`

That means the save path now writes this setting into the runtime config together with the rest of the motor tuning values.

### 4) Added motor defaults to `config/runtime.json`
The default runtime config now includes a full `motor` section:
- left/right direction
- steering direction
- left/right max speed
- left/right bias

This makes startup behavior clearer and more consistent.

### 5) Extended runtime status/state reporting
The runtime state now tracks:
- `motor_steering_direction`

This lets the UI reflect the currently active steering-direction setting while status polling is running.

### 6) Version bump
PiServer app version updated from:
- `0_2_7`

to:
- `0_2_8`

---

## Files changed
- `PiServer/piserver/services/motor_service.py`
- `PiServer/piserver/services/control_service.py`
- `PiServer/piserver/core/runtime_state.py`
- `PiServer/piserver/web/static/app.js`
- `PiServer/piserver/web/templates/index.html`
- `PiServer/config/runtime.json`
- `PiServer/piserver/app.py`
- `PiServer/README.md`
- `PiServer/PATCH_NOTES/PATCH_NOTES_PiServer_0_2_8.md`

---

## Verification performed
I verified the patch in three ways:

### A. Python syntax check
Compiled the changed Python files successfully with `py_compile`.

### B. Motor mixing behavior check
Confirmed that:
- normal steering direction produces the original left/right wheel mix
- reversed steering direction swaps the turn behavior as expected

Example logic check:
- normal mode with positive steering -> right wheel gets more drive than left
- reversed mode with positive steering -> left wheel gets more drive than right

### C. Runtime/default config check
Confirmed the updated runtime JSON now includes a persistent `motor` section with `steering_direction`.

---

## How to use after applying this patch
1. replace the files from this patch into your existing `PiServer` folder
2. restart PiServer
3. open the **Motor** tab
4. keep left/right motor direction for wiring calibration
5. use **Steering direction** to fix `left input / right input` turn behavior
6. click **Apply motor settings**
7. test on blocks first

If your current issue is exactly “steer left makes the car go right”, then set:
- **Steering direction = Reverse**

---

## Notes / limitations
- Applying motor settings still stops the motors first for safety.
- This patch does not auto-detect wiring or turning direction; it gives you an explicit control to set it correctly.
- If forward/backward is also wrong, you may still need to adjust **left motor direction** and/or **right motor direction** separately.

---

## Recommended next improvement
A good next patch would be to add a small **Motor test panel** with buttons like:
- left wheel forward
- left wheel reverse
- right wheel forward
- right wheel reverse
- steering test left/right

That would make calibration much faster on the real car.
