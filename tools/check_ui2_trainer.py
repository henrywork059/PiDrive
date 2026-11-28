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
    parser.add_argument("--require-requested-geometry", action="store_true", help="Fail unless original requested native client sizes and actual frames fit.")
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
                    if args.require_requested_geometry:
                        screen_rect = window.screen().availableGeometry()
                        window.move(screen_rect.x() + 4, screen_rect.y() + 4)
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
                            "native_frame": [window.frameGeometry().x(), window.frameGeometry().y(), window.frameGeometry().width(), window.frameGeometry().height()],
                            "native_frame_on_screen": window.screen().availableGeometry().contains(window.frameGeometry()),
                            "screen_dpr": window.screen().devicePixelRatio(),
                            "logical_dpi": window.screen().logicalDotsPerInch(),
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
                                    "native_frame_on_screen": window.screen().availableGeometry().contains(window.frameGeometry()),
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
                            if sys.platform == "win32" and not data["native_frame_on_screen"]:
                                geometry_errors.append(data)
                            if not all(data[key] for key in ("fully_reachable", "tabs_restored",
                                    "action_not_triggered", "enabled_unchanged", "state_unchanged")):
                                geometry_errors.append(data)
                        finally:
                            target_button.clicked.disconnect(observe_click)
                # Inspect all real workspace menu actions and panel focus
                # transitions after the original captures and action probes.
                if hasattr(window, "workspace_menu"):
                    manifest["workspace_panel_navigation"] = []
                    for stage, label in enumerate(expected):
                        tabs.setCurrentIndex(stage)
                        app.processEvents()
                        page = tabs.currentWidget()
                        window._refresh_workspace_menu()
                        titles = page.workspace_panel_titles()
                        actions = window._workspace_panel_actions
                        before = [list(splitter.sizes()) for splitter in page._splitters]
                        panels = []
                        for index, action in enumerate(actions):
                            action.trigger()
                            app.processEvents()
                            frame, header = page._workspace_panels[index]
                            panels.append({"title": titles[index], "menu": action.text(),
                                           "focused": app.focusWidget() is header,
                                           "visible": frame.isVisible() and header.isVisible(),
                                           "accessible_name": header.accessibleName()})
                        next_ok = previous_ok = False
                        if actions:
                            actions[0].trigger()
                            app.processEvents()
                            window._cycle_workspace_panel(1)
                            app.processEvents()
                            next_ok = app.focusWidget() is page._workspace_panels[1 % len(actions)][1]
                            window._cycle_workspace_panel(-1)
                            app.processEvents()
                            previous_ok = app.focusWidget() is page._workspace_panels[0][1]
                        after = [list(splitter.sizes()) for splitter in page._splitters]
                        data = {"stage": label, "panels": panels, "next": next_ok,
                                "previous": previous_ok, "splitters_before": before,
                                "splitters_after": after, "geometry_unchanged": before == after,
                                "session_height_preserved": panel.list_widget.height() == panel._current_session_list_height(),
                                "state_unchanged": window.state.filtered_df.empty and window.state.model is None}
                        target = output / f"panel-navigation-{stage+1}.png"
                        pixmap = window.grab()
                        assert not pixmap.isNull() and pixmap.save(str(target), "PNG")
                        data.update(file=target.name, sha256=hashlib.sha256(target.read_bytes()).hexdigest())
                        manifest["workspace_panel_navigation"].append(data)
                        if (not panels or len(actions) != len(titles)
                            or not all(p["focused"] and p["visible"] and p["accessible_name"] == p["title"] + " panel" for p in panels)
                            or not all(data[k] for k in ("next", "previous", "geometry_unchanged",
                                                       "session_height_preserved", "state_unchanged"))):
                            geometry_errors.append(data)
                # Keep all historical empty-workspace captures and add actual
                # on-disk image/label fixtures for populated Data/Preprocess.
                if hasattr(window.preprocess_page, "refresh_source_scope"):
                    from PIL import Image, ImageDraw
                    from piTrainer.services.preprocess.preprocess_service import apply_preprocessing_recipe
                    from piTrainer.services.data.record_loader_service import load_records_dataframe, build_filtered_dataframe
                    root = Path(temp) / "vd1j-recordings"
                    sessions = ["2026-11-24/manual_a", "2026-11-25/manual_b"]
                    metadata = []
                    for si, name in enumerate(sessions):
                        folder = root / name
                        (folder / "frames").mkdir(parents=True)
                        rows = []
                        for j in range(6):
                            image = Image.new("RGB", (320, 240), (43, 61, 80))
                            draw = ImageDraw.Draw(image)
                            draw.polygon([(0, 239), (125, 85), (195, 85), (319, 239)], fill=(105, 110, 115))
                            draw.line([(160, 96), (160 + (j - 2)*18, 239)], fill=(245, 220, 90), width=4)
                            draw.text((12, 12), f"Synthetic session {si+1} frame {j}", fill="white")
                            image.save(folder / "frames" / f"{j}.jpg")
                            rows.append({"frame_id": f"f{j}", "frame": f"frames/{j}.jpg",
                                         "timestamp_utc": f"2026-11-{24+si}T00:00:0{j}Z",
                                         "steering": (j - 3 + si)/5, "throttle": .4 + j*.05,
                                         "mode": "manual"})
                        labels = folder / "labels.jsonl"
                        labels.write_text("".join(json.dumps(row)+"\n" for row in rows), encoding="utf-8")
                        metadata.append(labels)
                    hashes = [hashlib.sha256(p.read_bytes()).hexdigest() for p in metadata]
                    data_page = window.data_page
                    preprocess = window.preprocess_page
                    tabs.setCurrentIndex(0)
                    window.state.records_root = str(root)
                    data_page.session_source_panel.path_edit.setText(str(root))
                    data_page.refresh_sessions()
                    data_page.session_source_panel.set_selected_sessions(sessions)
                    data_page.load_selected_sessions()
                    app.processEvents()
                    expected_rows = build_filtered_dataframe(load_records_dataframe(root, sessions), False)
                    assert len(expected_rows) == len(window.state.filtered_df) == 12
                    pd.testing.assert_frame_equal(window.state.filtered_df, expected_rows)
                    records = data_page.preview_panel
                    assert len(records.df) == 12
                    records.model.sort(records.model.columns.index("steering"), Qt.DescendingOrder)
                    target_record = records.df.iloc[0].to_dict()
                    assert records.select_record_identity(records.record_identity(target_record))
                    app.processEvents()
                    QTest.qWait(250)
                    assert records.record_identity(data_page.image_preview_panel.current_record) == records.record_identity(target_record)
                    assert data_page.image_preview_panel.image_label.pixmap() is not None
                    assert not data_page.image_preview_panel.image_label.pixmap().isNull()
                    assert records.select_adjacent_record(1)
                    QTest.qWait(250)
                    assert records.record_identity(data_page.image_preview_panel.current_record) == records.record_identity(records.selected_record())
                    manifest["populated_review"] = []
                    def capture_populated(name, details):
                        target = output / f"populated-{name}.png"
                        pixmap = window.grab()
                        assert not pixmap.isNull() and pixmap.save(str(target), "PNG")
                        manifest["populated_review"].append(dict(details, file=target.name,
                            sha256=hashlib.sha256(target.read_bytes()).hexdigest()))
                    capture_populated("data", {"loaded": 12, "visible": len(records.df),
                        "selected_identity": list(records.record_identity(records.selected_record())),
                        "summary": records.summary_label.text(), "actual_image": True})
                    data_page.filter_panel.text_edit.setText("manual_b")
                    data_page.apply_preview_filter()
                    assert len(records.df) == 6 and len(data_page.plot_panel.df) == 6
                    assert len(preprocess._source_df()) == 6
                    data_page.filter_panel.text_edit.setText("no-matching-records")
                    data_page.apply_preview_filter()
                    assert records.df.empty and preprocess._source_df().empty
                    assert len(window.state.filtered_df) == 12
                    tabs.setCurrentIndex(1)
                    app.processEvents()
                    assert "no rows" in preprocess.result_panel.status_label.text()
                    capture_populated("empty-scope", {"visible": 0, "active": 12,
                        "source": preprocess.summary_panel.source_scope_label.text(),
                        "readiness": preprocess.result_panel.status_label.text()})
                    preprocess.filter_panel.source_combo.setCurrentText("All loaded rows")
                    assert len(preprocess._source_df()) == 12
                    preprocess.filter_panel.source_combo.setCurrentText("Visible table rows")
                    assert preprocess._source_df().empty
                    data_page.filter_panel.text_edit.setText("manual_b")
                    data_page.apply_preview_filter()
                    source_df = preprocess._source_df()
                    recipe = preprocess.current_recipe()
                    transformed, summary = apply_preprocessing_recipe(source_df, recipe)
                    assert len(source_df) == 6
                    preprocess.preview_recipe()
                    deadline = time.monotonic() + 20
                    while preprocess.task_runner.active and time.monotonic() < deadline:
                        QTest.qWait(50)
                    assert not preprocess.task_runner.active
                    assert len(window.state.filtered_df) == 12
                    assert window.state.model is None
                    assert "Not applied yet" in preprocess.result_panel.status_label.text()
                    capture_populated("preprocess", {"source_rows": len(source_df),
                        "expected_output_rows": len(transformed), "preview_summary": summary,
                        "active_unchanged": True})
                    assert [hashlib.sha256(p.read_bytes()).hexdigest() for p in metadata] == hashes
                if args.require_requested_geometry:
                    geometry_errors.extend({"requested_geometry": item} for item in manifest["captures"]
                                           if not item["requested_geometry_met"] or not item["native_frame_on_screen"])
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
