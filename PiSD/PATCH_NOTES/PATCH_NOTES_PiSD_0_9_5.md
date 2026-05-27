# PiSD 0.9.5 Patch Notes — TFLite model load fix for piTrainer export

## Request summary

The user reported that AI Mode showed:

```text
Runtime: TFLite OK / Keras missing
Backend: load_failed
```

The uploaded AI log showed the selected model `picar_model.tflite` failed during loading with:

```text
Failed to load AI model: The truth value of an array with more than one element is ambiguous. Use a.any() or a.all()
```

## Cause / root cause

The Raspberry Pi runtime has TFLite support installed, so the problem was not a missing runtime dependency.

The failure happened while PiSD was reading the TensorFlow Lite input tensor details. TFLite runtimes commonly return the input `shape` as a NumPy array such as:

```python
array([1, 120, 160, 3])
```

The existing code used a boolean fallback expression around that value:

```python
input_details[0].get("shape") or []
```

A multi-value NumPy array cannot be evaluated as true/false, so Python raised the ambiguous truth-value error before the model could finish loading.

## Files changed

- `PiSD/pisd/__init__.py`
  - Updated version to `0.9.5`.

- `PiSD/pisd/services/ai_drive_service.py`
  - Added `_detail_shape_list()` to safely convert TFLite tensor `shape` values into plain Python lists without boolean truth-value checks.
  - Added `_dtype_name()` to normalize runtime dtype values such as `numpy.float32` into readable names such as `float32`.
  - Updated `_load_tflite()` to use the safe shape conversion.
  - Updated output tensor name extraction to avoid unnecessary truth-value fallback expressions.
  - Updated Keras input-shape handling to avoid truth-value checks on array-like objects.

- `PiSD/scripts/test_ai_drive_service.py`
  - Added a static service check that verifies NumPy-array TFLite tensor details convert without ambiguous truth-value errors.

- `PiSD/PATCH_NOTES/PATCH_NOTES_PiSD_0_9_5.md`
  - Added this patch note.

## Exact behaviour changed

Before this patch, a valid `.tflite` model could fail while loading if the TFLite backend returned tensor details using NumPy arrays.

After this patch, PiSD handles input tensor shape values like these safely:

```python
[1, 120, 160, 3]
array([1, 120, 160, 3])
```

The model should now progress past the shape-reading stage. If the model still fails after this patch, the next error should be the real next compatibility issue, not the ambiguous NumPy truth-value issue.

## Behaviour preserved / rollback check

Before finalising, this patch was checked against the latest patch notes:

- `0_9_4`: AI runtime diagnostics, `load_failed` backend visibility, Last load/error field, and expanded TFLite backend import order are preserved.
- `0_9_3`: piTrainer model upload/delete controls and steering/throttle output parsing are preserved.
- `0_9_2`: keyboard steering ramp timing remains `0.8 s`.
- `0_9_1`: Manual Drive motor start dead-zone popup and keyboard release-to-centre are preserved.

Confirmed this patch does not restore:

- `turn_gain` in real motor steering;
- motor `turn_curve` in real motor steering;
- Manual Drive steer strength;
- old Motor Tuning panels;
- capped Manual visual tuning overlay values.

## Verification actually performed

Performed locally after applying this patch over the current `0.9.4` state:

```bash
python3 -m compileall -q pisd scripts PiSD.py
node --check pisd/web/static/js/ai_mode.js
python3 scripts/test_ai_drive_service.py
python3 scripts/test_ai_mode_page.py --static-only
python3 scripts/test_manual_drive_page.py --static-only
python3 scripts/test_motor_steering_modes.py
python3 scripts/test_settings_persistence.py
python3 scripts/run_standard_validation.py --skip-api --skip-camera --skip-motor --skip-gui
python3 PiSD.py --status-only
```

All checks above passed in this static/simulation environment.

`test_ai_drive_service.py` now includes a regression check for NumPy-array TFLite input shapes.

## Verification not performed / known limits

- Real `.tflite` inference was not run here because this container does not include a TFLite runtime backend.
- Real browser route testing was not run here because Flask is not installed in this container.
- Hardware camera/motor testing was not run here.

## Suggested Pi-side check after applying

1. Apply the patch and restart PiSD.
2. Open `/ai-mode`.
3. Select `picar_model.tflite`.
4. Click **Load model**.
5. Check **Backend**, **Outputs**, **piTrainer export**, and **Last load/error**.

Expected improvement: the ambiguous NumPy truth-value error should be gone.

If the model loads successfully, test **Predict once** first before starting AI preview/drive.
