# piCar_0_2_5

Base: piCar_0_2_0

Goal: Improve OV5647 colour rendering on Raspberry Pi 4 while keeping the
recording and autopilot pipelines stable.

## Changes

### 1. camera.py

- Kept Picamera2 configured in **BGR888** at the requested preview size.
- Added a small one-off **colour calibration** at start-up:
  - Collects a short burst of frames when the camera first starts.
  - Computes the mean value of each channel (B, G, R) over those frames.
  - Treats the **green** channel as reference and computes simple gains for
    blue and red so that their average brightness matches green.
  - Clamps the gains to a safe range to avoid noisy extremes.
- Applies these per-channel gains to every frame in BGR space, producing a
  colour-corrected frame that is used consistently for:
  - the web preview (`get_jpeg_frame`),
  - recording,
  - and autopilot/model input.

- Reworked the background capture loop:
  - Stores both the raw sensor frame and the corrected frame internally.
  - Maintains a minimum frame interval based on the configured FPS so the Pi
    is not overloaded.

- Updated `get_jpeg_frame`:
  - Uses the colour-corrected BGR frame.
  - Converts BGR → RGB (as required by JPEG viewers/browsers).
  - Attempts to resize to `(TFLITE_W, TFLITE_H)` with a safe fallback.
  - Encodes to JPEG at quality 75.

- Kept the existing public method names (`get_frame`, `get_jpeg_bytes`) as
  aliases for backwards compatibility.

## Rationale

- The OV5647 sensors used on Raspberry Pi 4 can show a strong magenta or
  blue cast under indoor lighting, even when the driver is working.
- Rather than applying an arbitrary per-frame colour fix, this version
  derives a **stable, per-channel correction** from a short calibration
  phase after start-up, and then keeps those gains fixed:
  - This helps stabilise colours over time (no frame-to-frame flicker).
  - The same corrected colours are seen by:
    - the live web UI,
    - the recorded training data,
    - and the TFLite model at inference time.

## Verification steps

1. Deploy `piCar_0_2_5` on the Pi 4 (Bookworm, Picamera2/libcamera).
2. Start the server:

   ```bash
   cd ~/piCar
   source venv/bin/activate
   python3 server.py
   ```

3. Open the web UI and wait ~2 seconds after the first preview appears so
   the calibration frames can be collected.

4. Check the scene:
   - Road: should appear closer to **neutral grey**.
   - Lane line: should appear **yellow**, not pink.
   - Surrounding mat/ground: should appear **green**, not purple.

5. Quickly test:
   - Manual mode steering/throttle.
   - Auto-steer.
   - Autopilot.

   Behaviour should remain consistent with `piCar_0_2_0`; only the colours
   should be improved and more stable.
