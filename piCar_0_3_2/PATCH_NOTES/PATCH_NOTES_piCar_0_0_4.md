# PATCH_NOTES piCar_0_0_4 – Taller manual panel, central grid line, dot recording status

## Reason for changes
- You wanted more space for the Manual Drag Control so the joystick + speed slider feel less cramped.
- The Recording Control panel should only use a small vertical space (3 grid rows).
- The joystick grid needed a clearer visual reference in the middle.
- Recording state should be shown with a simple red/grey dot instead of the text ON/OFF.

## What changed

### 1. Layout: Manual Drag Control taller, Recording Control shorter
**Files touched**
- `ui_base.py`

**Details**
- The CSS grid layout for the right-hand side panels was updated:
  - `.panel-manual` now spans rows **1–17** (was 1–10).
  - `.panel-record` now spans rows **18–20** (was 11–20, now exactly 3 rows tall).
- This keeps the overall 30×20 layout, but gives the Manual Drag Control much more vertical space while shrinking the Recording Control area to only three grid units.

```css
.panel-manual {
    grid-column: 21 / span 10;
    grid-row: 1 / span 17;
}

.panel-record {
    grid-column: 21 / span 10;
    grid-row: 18 / span 3;
}
```

### 2. Joystick grid with thicker central lines
**Files touched**
- `ui_base.py`

**Details**
- The joystick area (`#joystickArea`) keeps the existing fine grid created by CSS linear-gradients.
- Added pseudo-elements to draw a thicker **central vertical** and **central horizontal** line so it is easier to see the middle:

```css
#joystickArea::before,
#joystickArea::after {
    content: "";
    position: absolute;
    pointer-events: none;
}

#joystickArea::before {
    left: 50%;
    top: 0;
    width: 2px;
    height: 100%;
    margin-left: -1px;
    background-color: rgba(180, 195, 245, 0.9);
}

#joystickArea::after {
    top: 50%;
    left: 0;
    height: 2px;
    width: 100%;
    margin-top: -1px;
    background-color: rgba(180, 195, 245, 0.9);
}
```

This preserves the existing grid, but visually emphasizes the center crosshair.

### 3. Recording status uses red/grey dot instead of ON/OFF
**Files touched**
- `ui_base.py`
- `ui_record_panel.py`
- `ui_script.py`

**Details**
- Introduced new CSS classes for a small circular status dot:

```css
.record-status-text {
    margin-top: 6px;
    font-size: 0.85em;
    display: flex;
    align-items: center;
    gap: 6px;
}

.rec-dot {
    display: inline-block;
    width: 10px;
    height: 10px;
    border-radius: 50%;
    box-shadow: 0 0 4px rgba(0, 0, 0, 0.4);
}

.rec-dot-on {
    background-color: #ff4d4d;
    box-shadow: 0 0 8px rgba(255, 77, 77, 0.8);
}

.rec-dot-off {
    background-color: #4b4f63;
}
```

- Updated the Recording Control panel HTML to use the dot:

```html
<div id="recordStatusText" class="record-status-text">
    <span class="rec-dot rec-dot-off"></span>
    Recording
</div>
```

- Updated JavaScript logic in `MAIN_SCRIPT` (in `ui_script.py`):

  - In `pollStatus()`:
    - Status bar text now uses a dot instead of ON/OFF:

    ```js
    const recDotHtml = '<span class="rec-dot ' + (data.recording ? 'rec-dot-on' : 'rec-dot-off') + '"></span>';
    const txt =
        "Mode: " + data.mode +
        " | FPS: " + data.fps.toFixed(1) +
        " | Rec: " + recDotHtml +
        " | Steering: " + data.steering.toFixed(2) +
        " | Speed: " + data.speed.toFixed(2) +
        " | Model: " + data.model_name;
    statusEl.innerHTML = txt;
    ```

    - The Recording Control text is kept in sync with the backend state:

    ```js
    if (data.recording) {
        btn.classList.remove("btn-record-off");
        btn.classList.add("btn-record-on");
        txtNode.innerHTML = '<span class="rec-dot rec-dot-on"></span> Recording';
    } else {
        btn.classList.remove("btn-record-on");
        btn.classList.add("btn-record-off");
        txtNode.innerHTML = '<span class="rec-dot rec-dot-off"></span> Recording';
    }
    ```

  - In `toggleRecord()`:
    - Local UI update after toggle now also uses the dot:

    ```js
    if (recording) {
        btn.classList.remove("btn-record-off");
        btn.classList.add("btn-record-on");
        txtNode.innerHTML = '<span class="rec-dot rec-dot-on"></span> Recording';
    } else {
        btn.classList.remove("btn-record-on");
        btn.classList.add("btn-record-off");
        txtNode.innerHTML = '<span class="rec-dot rec-dot-off"></span> Recording';
    }
    ```

So now both:
- The **Status bar** (`Rec:` field), and  
- The **Recording Control** panel  

display a **red dot when recording** and a **grey dot when idle**, with no ON/OFF text.

## Where does recording go right now?

In this version, `DataRecorder` is still a **placeholder** and does **not actually save files** yet.  
The `record()` method logs to the console when a frame would be captured, but it does not write images or metadata to disk:

```python
print(
    f"[REC] Captured record at {now:.3f} "
    f"steering={control_state['steering']:+.2f} "
    f"throttle={control_state['throttle']:.2f} "
    f"mode={control_state['mode']}"
)
```

So at the moment:
- **No images / tubs are written to storage.**
- All "recording" is visible only as debug print logs.

A later patch can extend `DataRecorder` to:
- Create a `data/` or `tub_xxx/` folder.
- Save JPEG frames and a matching JSON/CSV of steering, throttle, and mode (DonkeyCar-style).

## Suggested future improvements

- Implement real recording to disk with a DonkeyCar-like folder structure.
- Add a small label near the dot (e.g. “Idle / Recording”) for accessibility.
- Make the joystick grid density adjustable from the UI if you want different resolutions for fine control.
