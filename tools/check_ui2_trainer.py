"""UI2: capture actual native Qt widgets and audit six-stage readiness/navigation.

Synthetic empty-workspace fixture only; no training or hardware authority.
Run from any directory with the existing desktop test dependencies installed.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import sys
import tempfile
import time


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True, help="piTrainer component root")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--revision", required=True)
    parser.add_argument("--require-readable-status", action="store_true")
    parser.add_argument("--theme", choices=("dark", "light"), default=None)
    args = parser.parse_args()
    source = args.source.resolve()
    output = args.output.resolve()
    if not (source / "main.py").is_file():
        raise ValueError("Expected actual piTrainer component root")
    output.mkdir(parents=True, exist_ok=True)
    sys.path.insert(0, str(source))
    previous = Path.cwd()
    with tempfile.TemporaryDirectory(prefix="pidrive-ui2-") as temp:
        os.chdir(temp)
        os.environ["XDG_CONFIG_HOME"] = temp
        os.environ["XDG_DATA_HOME"] = temp
        try:
            from PySide6.QtCore import QSettings, Qt, qVersion
            from PySide6.QtGui import QFontInfo, QRawFont
            from PySide6.QtTest import QTest
            from PySide6.QtWidgets import QApplication
            import pandas as pd
            from piTrainer.main_window import MainWindow
            from piTrainer.version import APP_VERSION

            QSettings.setDefaultFormat(QSettings.IniFormat)
            for scope in (QSettings.UserScope, QSettings.SystemScope):
                for fmt in (QSettings.IniFormat, QSettings.NativeFormat):
                    QSettings.setPath(fmt, scope, temp)
            app = QApplication([])
            app.setStyle("Fusion")
            typography = None
            if (source / "piTrainer" / "ui" / "typography.py").is_file():
                from piTrainer.ui.typography import apply_local_typography
                typography = apply_local_typography(app)
                assert typography["ui"]["family"] and typography["mono"]["family"], typography
            if args.theme is not None:
                from piTrainer.ui.theme import apply_application_palette, save_theme, saved_theme, set_theme, theme_color
                from piTrainer.ui.styles import build_stylesheet
                assert save_theme(args.theme)
                assert set_theme(saved_theme()) == args.theme
                apply_application_palette(app)
                app.setStyleSheet(build_stylesheet())
            window = MainWindow()
            try:
                window.show()
                app.processEvents()
                tabs = window.tabs
                bar = tabs.tabBar()
                expected = ["1 Data", "2 Preprocess", "3 Train", "4 Validate",
                            "5 Export", "6 TFLite Check"]
                assert [tabs.tabText(i) for i in range(tabs.count())] == expected
                # The previous Windows offscreen captures passed interaction tests
                # but rendered missing-glyph boxes. Fail evidence qualification if
                # the actual tab font lacks basic Latin glyphs.
                raw_font = QRawFont.fromFont(bar.font())
                probe_text = "DataPreprocessTrainValidateExportTFLiteCheck0123456789"
                glyphs = list(raw_font.glyphIndexesForString(probe_text)) if raw_font.isValid() else []
                font_probe = {"platform": app.platformName(), "family": QFontInfo(bar.font()).family(),
                              "valid": raw_font.isValid(), "probe": probe_text,
                              "glyphs": glyphs}
                (output / "font_probe.json").write_text(json.dumps(font_probe, indent=2), encoding="utf-8")
                if sys.platform == "win32":
                    assert app.platformName() == "windows", font_probe
                assert len(glyphs) == len(probe_text) and all(glyphs), font_probe
                manifest = {"revision": args.revision, "version": APP_VERSION,
                            "qt_version": qVersion(), "os": platform.system(),
                            "qt_platform": app.platformName(), "fixture": "empty-workspace",
                            "captures": [], "readiness": [], "font_probe": font_probe,
                            "local_typography": typography}
                if args.theme is not None:
                    from piTrainer.ui.theme import appearance_settings, current_theme
                    assert current_theme() == args.theme
                    assert theme_color("bg_app") == ("#14171C" if args.theme == "dark" else "#F4F6FA")
                    assert theme_color("bg_app") in app.styleSheet()
                    other = "light" if args.theme == "dark" else "dark"
                    appearance_settings().setValue("fixture_preserved", "yes")
                    window._appearance_actions[other].trigger()
                    assert saved_theme() == other and current_theme() == args.theme
                    assert appearance_settings().value("fixture_preserved") == "yes"
                    window._appearance_actions[args.theme].trigger()
                    assert saved_theme() == args.theme
                    manifest["theme"] = args.theme
                    manifest["preference_roundtrip"] = True
                    manifest["actual_palette_window"] = app.palette().window().color().name()
                    assert manifest["actual_palette_window"].lower() == theme_color("bg_app").lower()

                def check_visible_status():
                    label = getattr(window, "workflow_readiness_label", None)
                    if not args.require_readable_status:
                        return None
                    assert label is not None and label.isVisible()
                    i = tabs.currentIndex()
                    tip = tabs.tabToolTip(i)
                    assert label.text() == tip.split(" — ", 1)[0]
                    assert label.toolTip() == tip
                    assert label.accessibleName() == expected[i] + " — " + tip
                    return label.text()

                def check_names(state):
                    names = [bar.accessibleTabName(i) for i in range(6)]
                    tips = [tabs.tabToolTip(i) for i in range(6)]
                    if args.require_readable_status:
                        for i, (name, tip) in enumerate(zip(names, tips)):
                            assert name == expected[i] + " — " + tip, (i, name, tip)
                    manifest["readiness"].append({"state": state, "names": names, "tooltips": tips,
                                                  "visible_status": check_visible_status()})

                assert window.state.filtered_df.empty
                check_names("empty")
                original = window.state.filtered_df
                try:
                    window.state.filtered_df = pd.DataFrame([{"steering": 0.2, "throttle": 0.3}])
                    window.refresh_workflow_readiness()
                    assert tabs.tabToolTip(0).startswith("Done")
                    assert tabs.tabToolTip(1).startswith("Inputs available")
                    check_names("one synthetic row")
                    tabs.setCurrentIndex(1)
                    app.processEvents()
                    check_names("one synthetic row, Preprocess")
                    tabs.setCurrentIndex(0)
                finally:
                    window.state.filtered_df = original
                    window.refresh_workflow_readiness()
                check_names("empty restored")
                manifest["prerequisite_navigation"] = []
                if args.require_readable_status and hasattr(window, "workflow_prerequisite_button"):
                    for stage, destination in ((1, 0), (2, 0), (3, 0), (4, 2), (5, 0)):
                        tabs.setCurrentIndex(stage)
                        app.processEvents()
                        assert window.workflow_detail_label.text() == tabs.tabToolTip(stage)
                        assert window.workflow_prerequisite_button.isVisible()
                        start = time.perf_counter()
                        QTest.mouseClick(window.workflow_prerequisite_button, Qt.LeftButton)
                        app.processEvents()
                        assert tabs.currentIndex() == destination
                        assert window.state.filtered_df.empty and window.state.model is None
                        manifest["prerequisite_navigation"].append({
                            "stage": expected[stage], "destination": expected[destination],
                            "clicks": 1, "elapsed_ms": (time.perf_counter() - start) * 1000,
                        })
                    tabs.setCurrentIndex(0)
                    app.processEvents()

                for width, height in ((1024, 768), (1440, 900)):
                    window.resize(width, height)
                    tabs.setCurrentIndex(0)
                    window.activateWindow()
                    bar.setFocus(Qt.OtherFocusReason)
                    app.processEvents()
                    for i, name in enumerate(expected):
                        if i:
                            QTest.keyClick(bar, Qt.Key_Right)
                            app.processEvents()
                        assert tabs.currentIndex() == i, (name, tabs.currentIndex())
                        assert tabs.currentWidget().isVisible()
                        QTest.qWait(100)
                        visible_status = check_visible_status()
                        pixmap = window.grab()
                        target = output / f"{width}-{i+1}.png"
                        assert not pixmap.isNull() and pixmap.save(str(target), "PNG")
                        manifest["captures"].append({
                            "page": name, "file": target.name, "visible_status": visible_status,
                            "requested": [width, height],
                            "actual": [pixmap.width(), pixmap.height()],
                            "logical_window": [window.width(), window.height()],
                            "device_pixel_ratio": pixmap.devicePixelRatio(),
                            "available_screen": [window.screen().availableGeometry().width(),
                                                 window.screen().availableGeometry().height()],
                            "requested_geometry_met": [window.width(), window.height()] == [width, height],
                            "sha256": hashlib.sha256(target.read_bytes()).hexdigest(),
                        })
                    QTest.keyClick(bar, Qt.Key_Left)
                    assert tabs.currentIndex() == 4
                assert len(manifest["captures"]) == 12
                (output / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
                print(f"Captured {len(manifest['captures'])} native Qt widget images; readiness and tab navigation verified")
            finally:
                window.close()
                app.processEvents()
        finally:
            os.chdir(previous)


if __name__ == "__main__":
    main()
