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


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True, help="piTrainer component root")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--revision", required=True)
    parser.add_argument("--require-readable-status", action="store_true")
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
            window = MainWindow()
            try:
                window.show()
                app.processEvents()
                tabs = window.tabs
                bar = tabs.tabBar()
                expected = ["1 Data", "2 Preprocess", "3 Train", "4 Validate",
                            "5 Export", "6 TFLite Check"]
                assert [tabs.tabText(i) for i in range(tabs.count())] == expected
                manifest = {"revision": args.revision, "version": APP_VERSION,
                            "qt_version": qVersion(), "os": platform.system(),
                            "qt_platform": app.platformName(), "fixture": "empty-workspace",
                            "captures": [], "readiness": []}

                def check_names(state):
                    names = [bar.accessibleTabName(i) for i in range(6)]
                    tips = [tabs.tabToolTip(i) for i in range(6)]
                    if args.require_readable_status:
                        for i, (name, tip) in enumerate(zip(names, tips)):
                            assert name == expected[i] + " — " + tip, (i, name, tip)
                    manifest["readiness"].append({"state": state, "names": names, "tooltips": tips})

                assert window.state.filtered_df.empty
                check_names("empty")
                original = window.state.filtered_df
                try:
                    window.state.filtered_df = pd.DataFrame([{"steering": 0.2, "throttle": 0.3}])
                    window.refresh_workflow_readiness()
                    assert tabs.tabToolTip(0).startswith("Done")
                    assert tabs.tabToolTip(1).startswith("Inputs available")
                    check_names("one synthetic row")
                finally:
                    window.state.filtered_df = original
                    window.refresh_workflow_readiness()
                check_names("empty restored")

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
                        pixmap = window.grab()
                        target = output / f"{width}-{i+1}.png"
                        assert not pixmap.isNull() and pixmap.save(str(target), "PNG")
                        manifest["captures"].append({
                            "page": name, "file": target.name,
                            "requested": [width, height],
                            "actual": [pixmap.width(), pixmap.height()],
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
