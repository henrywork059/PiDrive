# PiSD 0.10.0 Stable Package / Patch Notes

## Request summary

The user provided the current `PiSD.zip` package and asked to pack it as `v10` and also provide a `v10` patch package.

## Baseline decision

`PiSD_0_10_0` promotes the current uploaded PiSD state into the next full stable baseline. It builds forward from the accepted `PiSD_0_9_0` stable package and the accepted `0_9_1` through `0_9_10` patch line.

Future PiSD bug-fix patches should use the `0_10_x` line unless the user promotes a newer stable package.

## Behaviour changed

No runtime algorithm was intentionally changed in this packaging patch. The package version and stable-baseline documentation were updated so the current accepted state becomes `0.10.0`.

The promoted baseline includes the latest accepted behaviour:

- linear X steering;
- keyboard throttle steps and `0.8 s` steering ramp/release;
- removed motor dead-zone/start-kick feature;
- intended motor-output readouts;
- reduced seven-control Manual Drive overlay calibration;
- overlay settings saved to recordings and snapshots;
- AI model upload/delete controls;
- improved piTrainer/TFLite model loading diagnostics and parsing;
- TFLite runtime install/check helper scripts and documentation;
- AI loop update-rate/cache-frame improvements;
- AI Update Hz max increased to `60`;
- combined Start camera + live stream control in AI Mode;
- AI Mode recording and snapshot controls.

## Files changed

- `PiSD/pisd/__init__.py`
- `PiSD/README.md`
- `PiSD/docs/STABLE_BASELINE.md`
- `PiSD/PATCH_NOTES/PATCH_NOTES_PiSD_0_10_0.md`

## Compatibility notes

- This is a stable packaging/version promotion.
- Existing runtime config values are not reset.
- User-local model files and recording folders are not included or modified by this patch.
- The patch-only zip contains only the version/docs/patch-note files required to promote an existing current `0.9.10` state to `0.10.0`.

## Verification performed

Performed locally in the packaging container after updating the uploaded PiSD tree:

```bash
python3 -m compileall -q pisd scripts PiSD.py
python3 PiSD.py --status-only
```

Also inspected the package layout to confirm the full zip contains a top-level `PiSD/` folder and the patch zip contains only changed/new files under the same folder structure.

## Not verified

- Raspberry Pi hardware camera testing was not run in this container.
- Real motor movement was not tested in this container.
- Real TFLite inference was not run in this container.
