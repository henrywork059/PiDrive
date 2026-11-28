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
            from PySide6.QtCore import QSettings, Qt, QRect, qVersion
            from PySide6.QtGui import QFontInfo, QRawFont, QRegion
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

                panel = window.data_page.session_source_panel
                new_action = panel.load_btn.objectName() == "sessionLoadPrimaryAction"
                geometry_errors = []
                manifest["data_action_geometry"] = []

                def check_load_action(profile):
                    button = panel.load_btn
                    rect = QRect(button.mapTo(window, button.rect().topLeft()), button.size())
                    hit = window.childAt(rect.center())
                    visible = QRegion(button.rect()).subtracted(button.visibleRegion()).isEmpty()
                    reachable = (button.isVisible() and window.rect().contains(rect)
                                 and visible and (hit is button or
                                 (hit is not None and button.isAncestorOf(hit))))
                    data = {"profile": profile, "window": [window.width(), window.height()],
                            "rect": [rect.x(), rect.y(), rect.width(), rect.height()],
                            "fully_reachable": reachable,
                            "list_height": panel.list_widget.height(),
                            "saved_list_height": panel._current_session_list_height(),
                            "density": window._ui_density}
                    if hasattr(panel, "refresh_session_list_geometry"):
                        data["list_min_height"] = panel.list_widget.minimumHeight()
                        data["list_max_height"] = panel.list_widget.maximumHeight()
                        data["list_height_matches_preference"] = (
                            data["list_height"] == data["saved_list_height"]
                            == data["list_min_height"] == data["list_max_height"])
                    manifest["data_action_geometry"].append(data)
                    if not reachable or not data.get("list_height_matches_preference", True):
                        geometry_errors.append(data)

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
                        if i == 0 and new_action:
                            check_load_action(f"requested-{width}x{height}")
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
                # Native Windows runners can have a smaller physical desktop.
                # Keep both historical requested profiles unchanged; separately
                # qualify an honestly labelled client size that fits the screen.
                if new_action and sys.platform == "win32":
                    tabs.setCurrentIndex(0)
                    app.processEvents()
                    screen = window.screen().availableGeometry()
                    chrome_w = max(0, window.frameGeometry().width() - window.width())
                    chrome_h = max(0, window.frameGeometry().height() - window.height())
                    fit = [min(1024, screen.width() - chrome_w - 8),
                           min(768, screen.height() - chrome_h - 8)]
                    window.resize(*fit)
                    window.move(screen.x() + 4, screen.y() + 4)
                    app.processEvents()
                    QTest.qWait(150)
                    frame = window.frameGeometry()
                    actual = [window.width(), window.height()]
                    geometry_met = actual == fit and screen.contains(frame)
                    check_load_action("native-screen-fit")
                    pixmap = window.grab()
                    target = output / "native-screen-fit-data.png"
                    assert not pixmap.isNull() and pixmap.save(str(target), "PNG")
                    manifest["native_screen_fit"] = {
                        "requested_client": fit, "actual_client": actual,
                        "available_screen": [screen.width(), screen.height()],
                        "frame": [frame.x(), frame.y(), frame.width(), frame.height()],
                        "geometry_met": geometry_met, "file": target.name,
                        "sha256": hashlib.sha256(target.read_bytes()).hexdigest()}
                    if not geometry_met:
                        geometry_errors.append(manifest["native_screen_fit"])
                # New navigation-only affordance: exercise each actual target
                # after the historical capture matrix, without running any task.
                if hasattr(window, "workflow_locate_button"):
                    from piTrainer.ui.layout_widgets import CollapsibleSection
                    from PySide6.QtWidgets import QTabWidget
                    if sys.platform != "win32":
                        window.resize(1024, 768)
                    manifest["workspace_action_navigation"] = []
                    targets = (
                        window.data_page.session_source_panel.load_btn,
                        window.preprocess_page.actions_panel.apply_btn,
                        window.train_page.control_panel.start_btn,
                        window.validation_page.actions_panel.run_button,
                        window.export_page.actions_panel.export_btn,
                        window.export_validation_page.actions_panel.run_button,
                    )
                    for stage, target_button in enumerate(targets):
                        tabs.setCurrentIndex(stage)
                        app.processEvents()
                        parent = target_button.parentWidget()
                        changed_tabs = []
                        collapsed = []
                        while parent is not None and parent is not tabs:
                            if isinstance(parent, CollapsibleSection):
                                parent.set_expanded(False)
                                collapsed.append(parent)
                            if isinstance(parent, QTabWidget) and parent.count() > 1:
                                for j in range(parent.count()):
                                    if parent.widget(j).isAncestorOf(target_button):
                                        parent.setCurrentIndex((j + 1) % parent.count())
                                        changed_tabs.append((parent, j))
                                        break
                            parent = parent.parentWidget()
                        app.processEvents()
                        triggered = []
                        def observe_click(*_):
                            triggered.append(True)
                        target_button.clicked.connect(observe_click)
                        try:
                            enabled_before = target_button.isEnabled()
                            QTest.mouseClick(window.workflow_locate_button, Qt.LeftButton)
                            QTest.qWait(150)
                            rect = QRect(target_button.mapTo(window, target_button.rect().topLeft()),
                                         target_button.size())
                            hit = window.childAt(rect.center())
                            region_ok = QRegion(target_button.rect()).subtracted(
                                target_button.visibleRegion()).isEmpty()
                            data = {"stage": expected[stage], "action": target_button.text(),
                                    "window": [window.width(), window.height()],
                                    "rect": [rect.x(), rect.y(), rect.width(), rect.height()],
                                    "fully_reachable": (target_button.isVisible()
                                        and window.rect().contains(rect) and region_ok
                                        and (hit is target_button or
                                             (hit is not None and target_button.isAncestorOf(hit)))),
                                    "tabs_restored": all(t.currentIndex() == j for t, j in changed_tabs),
                                    "sections_exercised": len(collapsed),
                                    "tabs_exercised": len(changed_tabs),
                                    "action_not_triggered": not triggered,
                                    "enabled_unchanged": target_button.isEnabled() == enabled_before,
                                    "state_unchanged": window.state.filtered_df.empty and window.state.model is None}
                            pixmap = window.grab()
                            path = output / f"locate-stage-{stage + 1}.png"
                            assert not pixmap.isNull() and pixmap.save(str(path), "PNG")
                            data.update(file=path.name, sha256=hashlib.sha256(path.read_bytes()).hexdigest())
                            manifest["workspace_action_navigation"].append(data)
                            if not all(data[key] for key in ("fully_reachable", "tabs_restored",
                                    "action_not_triggered", "enabled_unchanged", "state_unchanged")):
                                geometry_errors.append(data)
                        finally:
                            target_button.clicked.disconnect(observe_click)
                manifest["geometry_errors"] = geometry_errors
                (output / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
                assert not geometry_errors, geometry_errors
                print(f"Captured {len(manifest['captures'])} native Qt widget images; readiness and tab navigation verified")
            finally:
                window.close()
                app.processEvents()
        finally:
            os.chdir(previous)


if __name__ == "__main__":
    main()
