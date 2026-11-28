"""Compare completed validation snapshots, never current controls or deployment authority."""
from __future__ import annotations

import re
import numpy as np

from .validation_receipts import evaluated_rows_hash


def compare_conversion(keras: dict | None, lite: dict | None) -> dict:
    """Require recorded provenance and identical ordered identities/labels.

    Receipt row hashes do not attest image bytes. Same run association does not
    prove weights are identical. Report differences, not a pass/fail threshold.
    """
    def unavailable(reason):
        return {"available": False, "reason": reason}

    if not keras or not lite:
        return unavailable("Complete Validate and TFLite Check first.")
    try:
        kc, lc = (r.get("experiment_context") or {} for r in (keras, lite))
        run = kc.get("run_id")
        if not isinstance(run, str) or not re.fullmatch(r"[0-9a-f]{32}", run) or run != lc.get("run_id"):
            return unavailable("Recorded training-run associations are missing or different.")
        if kc.get("status") not in ("Tracked in-memory training run.", "Verified model/run association."):
            return unavailable("Keras result has no verified local run association.")
        if lc.get("status") != "Verified model/run association." or not re.fullmatch(r"[0-9a-f]{64}", str(lc.get("model_sha256") or "")):
            return unavailable("TFLite result has no verified local model/run association.")
        if keras.get("prediction_backend") != "Keras model.predict" or lite.get("prediction_backend") != "TFLite Interpreter":
            return unavailable("Expected recorded Keras and TFLite prediction backends.")
        kr, lr = (r.get("validation_receipt") or {} for r in (keras, lite))
        kh, lh = evaluated_rows_hash(keras), evaluated_rows_hash(lite)
        if not kh or kh != lh or kh != kr.get("rows_sha256") or lh != lr.get("rows_sha256"):
            return unavailable("Ordered evaluated row identities or labels differ, or receipt hashes are unavailable.")
        if not all(re.fullmatch(r"[0-9a-f]{32}", str(r.get("id") or "")) for r in (kr, lr)):
            return unavailable("Both validation receipts are required.")
        n = int(keras["rows_used"])
        if n <= 0 or n != int(lite["rows_used"]):
            return unavailable("Evaluated row counts differ.")
        arrays = {}
        for key in ("steering_pred", "throttle_pred", "steering_true", "throttle_true"):
            for tag, result in (("keras", keras), ("lite", lite)):
                values = np.asarray(result[key], dtype=np.float64)
                if values.shape != (n,) or not np.isfinite(values).all():
                    return unavailable("Predictions or labels are incomplete or nonfinite.")
                arrays[tag, key] = values
        if any(not np.array_equal(arrays["keras", key], arrays["lite", key])
               for key in ("steering_true", "throttle_true")):
            return unavailable("Ground-truth labels differ.")
        ds = np.abs(arrays["keras", "steering_pred"] - arrays["lite", "steering_pred"])
        dt = np.abs(arrays["keras", "throttle_pred"] - arrays["lite", "throttle_pred"])
        if not np.isfinite(ds).all() or not np.isfinite(dt).all():
            return unavailable("Prediction differences are nonfinite.")
        # Only render the largest 100 rows, but compute metrics over every row.
        order = np.argsort(-np.maximum(ds, dt), kind="stable")[:100]
        rows = []
        for idx in order:
            i = int(idx)
            rows.append({"row": i+1, "session": str(lite["sessions"][i]),
                         "frame": str(lite["frame_ids"][i]), "flipped": bool(lite["aug_flip_lr"][i]),
                         "steering_delta": float(ds[i]), "speed_delta": float(dt[i]),
                         "keras_steering": float(arrays["keras", "steering_pred"][i]),
                         "lite_steering": float(arrays["lite", "steering_pred"][i]),
                         "keras_speed": float(arrays["keras", "throttle_pred"][i]),
                         "lite_speed": float(arrays["lite", "throttle_pred"][i])})
        return {"available": True, "run_id": run, "rows_sha256": kh, "rows_used": n,
                "keras_receipt": kr["id"], "lite_receipt": lr["id"],
                "model_sha256": lc["model_sha256"],
                "steering_max": float(ds.max()), "speed_max": float(dt.max()),
                "steering_mean": float(ds.mean()), "speed_mean": float(dt.mean()),
                "rows": rows}
    except (KeyError, TypeError, ValueError, OverflowError):
        return unavailable("Validation snapshots contain invalid or incomplete comparison data.")
