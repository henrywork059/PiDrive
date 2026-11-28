"""VD1K: actual CPU GUI training, validation and model conversion on synthetic recordings.
Runs only in a full trainer environment. No hardware, upload or deployment.
"""
from __future__ import annotations

import argparse
import hashlib
import faulthandler
import shutil
import json
import os
from pathlib import Path
import sys
import tempfile
import time
import traceback

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--revision", required=True)
    args = parser.parse_args()
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    source = Path(__file__).resolve().parents[1] / "piTrainer"
    sys.path.insert(0, str(source))
    report = {"revision": args.revision, "fixture": "synthetic recording sessions, actual CPU training",
              "deployment_authorized": False, "captures": [], "complete": False}
    def digest(path):
        return hashlib.sha256(Path(path).read_bytes()).hexdigest()
    def write_report():
        (output / "report.json").write_text(json.dumps(report, indent=2, allow_nan=False), encoding="utf-8")
    previous = Path.cwd()
    try:
        with tempfile.TemporaryDirectory(prefix="vd1k-") as tmp:
            os.chdir(tmp)
            os.environ["XDG_CONFIG_HOME"] = tmp
            os.environ["XDG_DATA_HOME"] = tmp
            from PySide6.QtCore import QSettings
            from PySide6.QtTest import QTest
            from PySide6.QtWidgets import QApplication
            from PIL import Image, ImageDraw
            import numpy as np
            import tensorflow as tf
            from piTrainer.main_window import MainWindow
            from piTrainer.ui.typography import apply_local_typography
            from piTrainer.ui.theme import apply_application_palette
            from piTrainer.ui.styles import build_stylesheet
            from piTrainer.utils.model_manifest import inspect_manifest, manifest_path
            from piTrainer.services.validation.validation_receipts import evaluated_rows_hash
            QSettings.setDefaultFormat(QSettings.IniFormat)
            for scope in (QSettings.UserScope, QSettings.SystemScope):
                for fmt in (QSettings.IniFormat, QSettings.NativeFormat):
                    QSettings.setPath(fmt, scope, tmp)
            app = QApplication([])
            app.setStyle("Fusion")
            apply_local_typography(app)
            apply_application_palette(app)
            app.setStyleSheet(build_stylesheet())
            window = MainWindow()
            window.resize(1440, 900)
            window.show()
            app.processEvents()
            report["tensorflow"] = tf.__version__
            report["qt_platform"] = app.platformName()
            def capture(name, stage):
                window.tabs.setCurrentIndex(stage)
                app.processEvents()
                QTest.qWait(250)
                path = output / (name + ".png")
                pix = window.grab()
                assert not pix.isNull() and pix.save(str(path), "PNG")
                report["captures"].append({"file": path.name, "sha256": digest(path),
                                           "size": [pix.width(), pix.height()]})
                write_report()
            def pump(seconds):
                deadline = time.monotonic() + seconds
                while time.monotonic() < deadline:
                    app.processEvents()
                    # Explicitly release Python's GIL to TensorFlow and Qt
                    # worker callbacks rather than repeatedly calling qWait.
                    time.sleep(.02)
                app.processEvents()

            def wait(page, label, timeout=150):
                started = time.monotonic()
                progress = page.task_progress
                trace = output / (label + "-thread-trace.txt")
                transitions = []
                last = None
                with trace.open("w", encoding="utf-8") as diagnostic:
                    faulthandler.dump_traceback_later(45, repeat=True, file=diagnostic)
                    try:
                        while page.has_active_task() and time.monotonic() - started < timeout:
                            pump(.05)
                            step = progress.step_label.text()
                            if step != last:
                                transitions.append({"elapsed_s": time.monotonic()-started, "step": step})
                                last = step
                                report[label+"_transitions"] = transitions
                                write_report()
                        pump(.1)
                        report[label+"_elapsed_s"] = time.monotonic()-started
                        report[label+"_progress"] = progress.step_label.text()
                        log = page.log_panel.text.toPlainText()
                        (output / (label+"-log.txt")).write_text(log, encoding="utf-8")
                        write_report()
                        if page.has_active_task():
                            faulthandler.dump_traceback(file=diagnostic, all_threads=True)
                            report["failure"] = label + " timeout; original 150-second gate retained"
                            report["timeout_step"] = progress.step_label.text()
                            write_report()
                            if label == "training":
                                page.stop_training()
                            # Never destroy a live QThread. Allow normal safe
                            # worker retirement, then exit only this isolated CI
                            # process if it cannot finish. Not application logic.
                            grace = time.monotonic()+10
                            while page.has_active_task() and time.monotonic()<grace:
                                pump(.05)
                            report["worker_retired_after_timeout"] = not page.has_active_task()
                            write_report()
                            if page.has_active_task():
                                diagnostic.flush()
                                sys.stdout.flush()
                                sys.stderr.flush()
                                os._exit(1)
                            raise AssertionError(label + " timeout")
                        assert progress.step_label.text().startswith("Succeeded:"), (label, progress.step_label.text(), progress.result_label.text())
                    finally:
                        faulthandler.cancel_dump_traceback_later()
                if trace.stat().st_size == 0:
                    trace.unlink()

            root = Path(tmp) / "recordings"
            names = ["2026-11-24/manual_a", "2026-11-25/manual_b"]
            files = []
            for si, name in enumerate(names):
                folder = root / name
                (folder / "frames").mkdir(parents=True)
                rows = []
                for j in range(8):
                    im = Image.new("RGB", (160, 120), (30+si*25, 70, 100))
                    draw = ImageDraw.Draw(im)
                    draw.line([(80, 40), (35+j*12, 119)], fill=(230,220,40), width=6)
                    draw.rectangle((j*8, 5, j*8+10, 18), fill=(210,100,50))
                    im.save(folder / "frames" / f"{j}.jpg")
                    rows.append({"frame_id": f"f{j}", "frame": f"frames/{j}.jpg",
                                 "timestamp_utc": f"2026-11-{24+si}T00:00:0{j}Z",
                                 "mode": "manual", "steering": (j-3)/5, "throttle": .2+j*.07})
                path = folder / "labels.jsonl"
                path.write_text("".join(json.dumps(row)+"\n" for row in rows), encoding="utf-8")
                files.append(path)
            original = [digest(path) for path in files]
            shutil.copytree(root, output / "fixture-recordings")
            report["fixture_files"] = [{"file": str(p.relative_to(output)), "sha256": digest(p)}
                                       for p in sorted((output / "fixture-recordings").rglob("*")) if p.is_file()]
            write_report()
            data = window.data_page
            window.state.records_root = str(root)
            data.session_source_panel.path_edit.setText(str(root))
            data.refresh_sessions()
            data.session_source_panel.set_selected_sessions(names)
            data.load_selected_sessions()
            assert len(window.state.filtered_df) == 16
            window.export_page.set_output_dir(str(output / "models"))
            pre = window.preprocess_page
            pre.filter_panel.source_combo.setCurrentText("Visible table rows")
            pre.apply_recipe()
            wait(pre, "preprocess")
            assert len(window.state.filtered_df) > 0
            report["preprocessed_rows"] = len(window.state.filtered_df)
            capture("preprocess-applied", 1)
            train = window.train_page
            cfg = train.config_panel
            cfg.img_h.setValue(64)
            cfg.img_w.setValue(96)
            cfg.epochs.setValue(2)
            cfg.batch_size.setValue(4)
            cfg.seed.setValue(27)
            cfg.compute_device.setCurrentText("CPU only")
            cfg.split_mode.setCurrentText("By session")
            cfg.val_ratio.setValue(.5)
            cfg.shuffle.setChecked(False)
            cfg.augment.setChecked(False)
            cfg.bounded_input.setChecked(True)
            cfg.early_stopping.setChecked(False)
            cfg.reduce_lr.setChecked(False)
            window.tabs.setCurrentIndex(2)
            train.start_training()
            state = window.state
            partition_columns = ["session", "abs_image", "source_frame_id", "frame_id", "steering", "throttle", "aug_flip_lr"]
            partitions = {}
            for label, frame in (("train", state.train_df), ("validation", state.val_df)):
                columns = [c for c in partition_columns if c in frame.columns]
                partitions[label] = json.loads(frame[columns].to_json(orient="records", double_precision=15))
            partition_path = output / "partitions.json"
            partition_path.write_text(json.dumps(partitions, indent=2, allow_nan=False), encoding="utf-8")
            report["partitions"] = {"file": partition_path.name, "sha256": digest(partition_path),
                                    "train_rows": len(state.train_df), "validation_rows": len(state.val_df),
                                    "session_disjoint": not bool(set(state.train_df.session)&set(state.val_df.session)),
                                    "source_disjoint": not bool(set(state.train_df.abs_image)&set(state.val_df.abs_image))}
            assert report["partitions"]["session_disjoint"] and report["partitions"]["source_disjoint"]
            write_report()
            wait(train, "training")
            assert state.model is not None and len(state.history["loss"]) == 2
            assert len(state.train_df) and len(state.val_df)
            assert not set(state.train_df.session) & set(state.val_df.session)
            assert not set(state.train_df.abs_image) & set(state.val_df.abs_image)
            provenance = train.provenance_for_model(state.model)
            assert provenance and provenance[0]["status"] == "succeeded"
            run = provenance[0]
            report["training"] = {"run_id": run["run_id"], "train_rows": len(state.train_df),
                                  "validation_rows": len(state.val_df), "session_disjoint": True,
                                  "source_disjoint": True, "history": {k:[float(x) for x in v] for k,v in state.history.items()}}
            capture("training-complete", 2)
            def check_result(page, label, stage):
                wait(page, label)
                result = page.last_result
                assert result and result["rows_used"] == len(state.val_df)
                assert result["experiment_context"]["run_id"] == run["run_id"]
                receipt = result["validation_receipt"]
                assert receipt["rows_sha256"] == evaluated_rows_hash(result)
                raw = {k:np.asarray(result[k]).tolist() for k in
                       ("steering_true","throttle_true","steering_pred","throttle_pred","combined_error")}
                assert all(np.isfinite(v).all() for v in raw.values())
                raw.update({k:result[k] for k in ("sessions","frame_ids","source_frame_ids","abs_images","aug_flip_lr")})
                receipt_path = Path(receipt["path"])
                assert receipt_path.is_file()
                raw.update({"receipt_file": str(receipt_path.relative_to(output)),
                            "receipt_sha256": digest(receipt_path), "rows_sha256": receipt["rows_sha256"],
                            "run_id": run["run_id"], "rows_used": result["rows_used"],
                            "backend": result["prediction_backend"],
                            "metrics": {k:float(result[k]) for k in ("steering_mae","throttle_mae","steering_rmse","throttle_rmse")}})
                (output / (label+".json")).write_text(json.dumps(raw, indent=2, allow_nan=False), encoding="utf-8")
                review = page.frame_review_panel
                assert len(review.all_rows) == result["rows_used"]
                review.worst_button.click()
                app.processEvents()
                assert review.selected_row() is not None
                capture(label, stage)
                report[label] = {"file": label+".json", "sha256": digest(output/(label+".json")),
                                 "rows": result["rows_used"], "receipt_sha256": raw["receipt_sha256"]}
                return raw
            validation = window.validation_page
            validation.config_panel.dataset_source_combo.setCurrentText("Validation split")
            validation.config_panel.model_source_combo.setCurrentText("Current trained model")
            validation.config_panel.batch_spin.setValue(4)
            validation.validate_model()
            keras = check_result(validation, "keras-validation", 3)
            export = window.export_page
            export.options_panel.base_name.setText("vd1k_synthetic")
            export.options_panel.export_keras.setChecked(True)
            export.options_panel.export_tflite.setChecked(True)
            export.options_panel.quantize_int8.setChecked(False)
            export.export_model()
            wait(export, "export")
            first = Path(state.last_exported_tflite_path)
            assert first.is_file() and export.has_confirmed_export_for(state.model)
            first_digest = digest(first)
            manifest, _ = inspect_manifest(first, expected_kind="steering_control", input_size=(96,64))
            assert manifest["model_sha256"] == first_digest and manifest["experiment"]["run_id"] == run["run_id"]
            export.export_model()
            wait(export, "export-repeat")
            second = Path(state.last_exported_tflite_path)
            assert second != first and digest(first) == first_digest
            manifest2, _ = inspect_manifest(second, expected_kind="steering_control", input_size=(96,64))
            assert manifest2["model_sha256"] == digest(second) and manifest2["experiment"]["run_id"] == run["run_id"]
            report["exports"] = [{"file": str(p.relative_to(output)), "sha256": digest(p),
                                  "manifest_sha256": digest(manifest_path(p))} for p in (first, second)]
            capture("export", 4)
            check = window.export_validation_page
            check.config_panel.dataset_source_combo.setCurrentText("Validation split")
            check.config_panel.batch_spin.setValue(4)
            check.validate_export()
            lite = check_result(check, "tflite-validation", 5)
            assert keras["rows_sha256"] == lite["rows_sha256"]
            for key in ("sessions","frame_ids","source_frame_ids","abs_images","aug_flip_lr","steering_true","throttle_true"):
                assert keras[key] == lite[key], key
            report["prediction_delta"] = {key: float(np.max(np.abs(np.asarray(keras[key])-np.asarray(lite[key]))))
                                          for key in ("steering_pred","throttle_pred")}
            # Exercise the actual comparison control and its historical snapshot binding.
            if hasattr(check, "comparison_panel"):
                check.result_tabs.setCurrentWidget(check.comparison_panel)
                check.comparison_panel.compare_button.click()
                wait(check, "conversion-comparison")
                comparison = check.comparison_panel.comparison
                assert comparison and comparison["available"]
                assert comparison["rows_used"] == len(state.val_df)
                assert comparison["steering_max"] == report["prediction_delta"]["steering_pred"]
                assert comparison["speed_max"] == report["prediction_delta"]["throttle_pred"]
                assert check.comparison_panel.table.rowCount() == len(state.val_df)
                report["conversion_comparison"] = comparison
                if hasattr(check.comparison_panel, "row_detail"):
                    check.comparison_panel.table.setCurrentCell(1, 0)
                    selected = comparison["rows"][1]
                    detail = check.comparison_panel.row_detail.text()
                    assert selected["session"] in detail and selected["frame"] in detail
                    assert f"{selected['lite_speed']:.7g}" in detail and f"{selected['steering_delta']:.3e}" in detail
                    report["comparison_selected_row_detail"] = detail
                capture("conversion-comparison", 5)
                validation.clear_results()
                assert check.comparison_panel.comparison is None
                assert check.comparison_panel.table.rowCount() == 0
                if hasattr(check.comparison_panel, "row_detail"):
                    assert not check.comparison_panel.row_detail.text()
                report["comparison_invalidated_on_clear"] = True
            assert [digest(p) for p in files] == original
            report["source_metadata_unchanged"] = True
            report["model_files"] = [{"file": str(p.relative_to(output)), "sha256": digest(p), "bytes": p.stat().st_size}
                                     for p in sorted((output / "models").rglob("*")) if p.is_file()]
            report["complete"] = True
            write_report()
            window.close()
            app.processEvents()
    except BaseException:
        report["failure"] = traceback.format_exc()
        write_report()
        raise
    finally:
        os.chdir(previous)

if __name__ == "__main__":
    main()
