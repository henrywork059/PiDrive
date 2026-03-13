# PATCH NOTES — PiServer_0_2_5

## Goal
Repair the mixed 0_2_1/0_2_2/0_2_3/0_2_4 startup state and restore the full Manual + Motor tab feature set on top of the PiServer_0_2_0 baseline.

## Problems fixed
- `python3 server.py` failed because the working tree ended up with a partial/mixed set of startup and service files.
- `piserver.services.control_service` on the Pi did not export `ControlService`, which blocked app startup.
- The Manual + Motor feature patch was not fully self-consistent after the later startup-only fixes.

## What this patch includes
- Restores a complete `piserver/app.py` with `create_app()` and the Manual + Motor routes.
- Restores a complete `ControlService` with runtime-config support for motor settings.
- Restores a complete `MotorService` with direction, max-speed, and bias controls.
- Restores the `RuntimeState` fields needed by the new Manual and Motor tabs.
- Keeps `piserver/services/__init__.py` lightweight so startup does not force-import every service module.
- Restores the Manual + Motor web UI files from the 0_2_1 feature patch.
- Uses the simple known-good `server.py` and `piserver/__init__.py` startup path now that `create_app()` is present again.

## Files included
- `PiServer/server.py`
- `PiServer/piserver/__init__.py`
- `PiServer/piserver/app.py`
- `PiServer/piserver/core/runtime_state.py`
- `PiServer/piserver/services/__init__.py`
- `PiServer/piserver/services/control_service.py`
- `PiServer/piserver/services/motor_service.py`
- `PiServer/piserver/web/static/app.js`
- `PiServer/piserver/web/static/styles.css`
- `PiServer/piserver/web/templates/index.html`
- `PiServer/README.md`
- `PiServer/PATCH_NOTES/PATCH_NOTES_PiServer_0_2_5.md`

## Validation
After copying these files over your current PiServer checkout:

```bash
cd ~/PiDrive/PiServer
python3 server.py
```

Expected:
- Flask starts without `ImportError`.
- Manual tab loads.
- Motor tab loads.
- `/api/status` returns motor tuning fields.
