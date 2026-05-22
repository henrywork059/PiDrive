from __future__ import annotations

from .formatting import stylesheet_tokens


def build_stylesheet(density: str = "comfortable") -> str:
    values = stylesheet_tokens(density)
    css = """
    QWidget {
        font-size: @BASE_FONT@px;
        color: #e6e8ee;
        background: #111722;
    }
    QMainWindow {
        background: #111722;
    }
    QToolTip {
        background: #1b2433;
        color: #f7fbff;
        border: 1px solid #4d85d1;
        padding: 6px;
    }
    QToolBar {
        background: #171f2c;
        border-bottom: 1px solid #2a3140;
        spacing: 8px;
        padding: 6px;
    }
    QMainWindow::separator {
        background: #56a7ff;
        width: 5px;
        height: 5px;
    }
    QStatusBar {
        background: #101620;
        color: #c6cad4;
        border-top: 1px solid #2a3140;
        padding: 3px 8px;
    }
    QFrame[role='pageShell'] {
        background: #0d131d;
        border: none;
    }
    QFrame#pageBanner {
        background: #142238;
        border: 1px solid #315074;
        border-left: 5px solid #5eb2ff;
        border-radius: 9px;
    }
    QLabel#pageBannerTitle {
        color: #ffffff;
        background: transparent;
        font-size: @BANNER_TITLE@px;
        font-weight: 900;
        letter-spacing: 0.2px;
    }
    QLabel#pageBannerSummary {
        color: #c8d8ee;
        background: transparent;
        font-size: @BASE_FONT@px;
        line-height: 1.25em;
    }
    QLabel#pageBannerNext {
        color: #eafff0;
        background: #1f7d42;
        border: 1px solid #77df9a;
        border-radius: 9px;
        padding: 7px 9px;
        font-weight: 800;
    }
    QDockWidget {
        color: #f7fbff;
        font-weight: 700;
    }
    QDockWidget::title {
        background: #223a5a;
        color: #ffffff;
        padding: 7px 10px;
        border: 1px solid #4d85d1;
        border-bottom: none;
    }
    #dockPageFiller {
        background: #0e131b;
        border: none;
    }
    QGroupBox {
        border: 1px solid #303a4b;
        border-radius: 9px;
        margin-top: 9px;
        padding: 10px 8px 8px 8px;
        background: #171f2c;
        font-weight: 650;
        color: #f4f7ff;
    }
    QGroupBox::title {
        subcontrol-origin: margin;
        left: 12px;
        padding: 0 5px 0 5px;
    }
    QGroupBox[role='formGroup'] {
        border-color: #34465f;
        background: #151f2d;
    }
    QFrame[role='splitterPanel'] QGroupBox[role='formGroup'] {
        margin-top: 8px;
    }
    QPushButton {
        min-height: @BUTTON_MIN@px;
        padding: 4px 10px;
        background: #263245;
        color: #eef2fb;
        border: 1px solid #3b4d67;
        border-radius: 7px;
        font-weight: 600;
    }
    QPushButton:hover {
        background: #31445e;
        border-color: #5a8cd0;
    }
    QPushButton:pressed {
        background: #213044;
    }
    QPushButton:disabled {
        background: #1a1f28;
        color: #6f7788;
        border-color: #2a3140;
    }
    QPushButton[role='primary'] {
        background: #2f6fb3;
        border-color: #7fc2ff;
        color: #ffffff;
    }
    QPushButton[role='primary']:hover {
        background: #3f82cc;
    }
    QPushButton[role='nextStep'] {
        min-height: @NEXT_MIN@px;
        padding: 7px 12px;
        background: #208242;
        border: 2px solid #70e096;
        color: #ffffff;
        border-radius: 9px;
        font-weight: 850;
    }
    QPushButton[role='nextStep']:hover {
        background: #2d9b52;
        border-color: #a8f3bd;
    }
    QPushButton[role='nextStep']:pressed {
        background: #166a34;
    }
    QPushButton[role='nextStep']:disabled {
        background: #1b3023;
        color: #8fa994;
        border-color: #31533a;
    }
    QPushButton[role='nextStep'][pulse='true'] {
        background: #2a9550;
        border-color: #b9f6c9;
    }
    QPushButton[role='danger'] {
        background: #5b2630;
        border-color: #c75d70;
        color: #fff2f4;
    }
    QPushButton[role='secondary'] {
        background: #202b3c;
        color: #dbe5f5;
    }
    QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox, QListWidget, QTextEdit, QPlainTextEdit, QTableWidget {
        min-height: @INPUT_MIN@px;
        background: #0d131d;
        color: #e6e8ee;
        border: 1px solid #344055;
        border-radius: 7px;
        selection-background-color: #335b9a;
        selection-color: #ffffff;
    }
    QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus, QComboBox:focus, QTextEdit:focus, QPlainTextEdit:focus, QTableWidget:focus, QListWidget:focus {
        border: 1px solid #67adff;
    }
    QPlainTextEdit {
        padding: 8px;
        font-family: Consolas, 'Cascadia Mono', monospace;
        border-radius: 9px;
    }
    QTableWidget {
        gridline-color: #283347;
        alternate-background-color: #121a26;
        background: #0d131d;
        border-radius: 9px;
    }
    QTableWidget::item {
        padding: 5px;
    }
    QTableWidget::item:selected, QListWidget::item:selected {
        background: #315b91;
        color: #ffffff;
    }
    #sessionListWidget {
        padding: 7px;
    }
    #sessionRow {
        background: #121c28;
        border: 1px solid #2d3a4d;
        border-radius: 9px;
    }
    #sessionRow:hover {
        background: #172536;
        border: 1px solid #4d79a8;
    }
    #sessionRowCheckbox {
        spacing: 0px;
        background: transparent;
        margin-top: 1px;
    }
    #sessionRowCheckbox::indicator {
        width: 20px;
        height: 20px;
        border-radius: 5px;
        border: 2px solid #7fd3ff;
        background: #102033;
    }
    #sessionRowCheckbox::indicator:hover {
        border-color: #b4ecff;
        background: #15304b;
    }
    #sessionRowCheckbox::indicator:checked {
        background: #18b2ff;
        border: 2px solid #eef9ff;
    }
    #sessionRowLabel {
        color: #f5f8ff;
        background: transparent;
        font-weight: 600;
        padding-top: 1px;
    }
    QHeaderView::section {
        background: #1d2837;
        color: #e6e8ee;
        border: 1px solid #344055;
        padding: 5px;
        font-weight: 700;
    }
    QTabWidget::pane {
        border: 1px solid #303a4b;
        background: #111722;
    }
    QTabWidget[role='contentTabs']::pane {
        border: 1px solid #303a4b;
        border-radius: 8px;
        background: #101722;
    }
    QTabWidget[role='contentTabs'] QTabBar::tab {
        min-width: @WORKFLOW_TAB_MIN@px;
    }
    QTabWidget#mainWorkflowTabs::pane {
        border: 0px;
        background: #0d131d;
    }
    QTabWidget#mainWorkflowTabs QTabBar::tab {
        min-width: @MAIN_TAB_MIN@px;
        padding: 8px 14px;
        margin-right: 5px;
        border-top-left-radius: 10px;
        border-top-right-radius: 10px;
    }
    QTabWidget#mainWorkflowTabs QTabBar::tab:selected {
        background: #31537a;
        border-color: #82c4ff;
    }
    QTabBar::tab {
        min-width: 104px;
        padding: 7px 9px;
        background: #17202d;
        color: #cfd5df;
        border: 1px solid #303a4b;
        border-bottom: none;
        margin-right: 3px;
        border-top-left-radius: 7px;
        border-top-right-radius: 7px;
        font-weight: 700;
    }
    QTabBar::tab:selected {
        background: #2a3a51;
        color: #ffffff;
        border-color: #568bd0;
    }
    QTabBar::tab:hover:!selected {
        background: #202d3e;
    }
    QTabWidget[role='workflowTabs']::pane {
        background: #101722;
        border: 1px solid #303a4b;
        border-radius: 8px;
    }
    QTabWidget[role='workflowTabs'] QTabBar::tab {
        min-width: @WORKFLOW_TAB_MIN@px;
        padding: 7px 9px;
        font-size: 12px;
    }
    QTabWidget[role='workflowTabs'] QTabBar::tab:selected {
        background: #27415f;
        border-color: #6ab2ff;
    }
    QProgressBar {
        min-height: 22px;
        border: 1px solid #344055;
        border-radius: 7px;
        text-align: center;
        background: #0d131d;
        color: #e6e8ee;
    }
    QProgressBar::chunk {
        background: #4d85d1;
        border-radius: 6px;
    }
    QCheckBox {
        color: #f3f7ff;
        spacing: 8px;
        background: transparent;
    }
    QCheckBox::indicator {
        width: 18px;
        height: 18px;
        border-radius: 5px;
        border: 2px solid #7fbaff;
        background: #101722;
    }
    QCheckBox::indicator:hover {
        border-color: #a9d2ff;
        background: #162132;
    }
    QCheckBox::indicator:checked {
        background: #56a7ff;
        border: 2px solid #cfe7ff;
        image: none;
    }

    #controlStack {
        background: #101722;
        border: none;
    }
    QScrollArea {
        background: #101722;
        border: none;
    }
    QScrollArea[role='workflowScroll'] {
        border: 0px;
        border-radius: 8px;
    }
    QToolButton#collapsibleSectionHeader {
        background: #1e2b3d;
        color: #f7fbff;
        border: 1px solid #374d67;
        border-radius: 9px;
        padding: 7px 9px;
        font-weight: 800;
        text-align: left;
    }
    QToolButton#collapsibleSectionHeader:hover {
        background: #293b53;
        border-color: #67adff;
    }
    QToolButton#collapsibleSectionHeader:checked {
        background: #233550;
        border-color: #5c91d6;
    }
    QFrame#collapsibleSectionBody {
        background: #151d29;
        border: 1px solid #303a4b;
        border-top: none;
        border-bottom-left-radius: 9px;
        border-bottom-right-radius: 9px;
    }
    QWidget#collapsibleSection {
        background: transparent;
    }
    QLabel#sidebarIntro, QLabel#quickHint {
        background: #142033;
        color: #d7e7ff;
        border: 1px solid #2e4b70;
        border-radius: 9px;
        padding: 7px 9px;
        font-weight: 500;
    }
    QLabel[role='muted'] {
        color: #98a5bb;
    }
    QLabel[role='hint'] {
        color: #c8d8ee;
    }
    QLabel[role='statValue'] {
        color: #ffffff;
        background: #101a28;
        border: 1px solid #2e4b70;
        border-radius: 8px;
        padding: 5px 8px;
        font-weight: 850;
    }
    QLabel[role='summaryLine'] {
        color: #dce8f8;
        background: #101a28;
        border: 1px solid #283c58;
        border-radius: 9px;
        padding: 7px 9px;
    }
    QLabel[role='summaryBlock'] {
        color: #eaf2ff;
        background: #101a28;
        border: 1px solid #2e4b70;
        border-radius: 9px;
        padding: 7px 9px;
    }

    QSplitter[role='pageSplitter'] {
        background: #0d131d;
    }
    QSplitter[role='pageSplitter']::handle {
        background: #223047;
        border: 1px solid #394f71;
        border-radius: 3px;
        margin: 2px;
    }
    QSplitter[role='pageSplitter']::handle:hover {
        background: #35608e;
        border-color: #78baff;
    }
    QFrame[role='splitterPanel'] {
        background: #111722;
        border: 1px solid #303a4b;
        border-radius: 9px;
    }
    QLabel#splitterPanelTitle {
        color: #f4f7fb;
        background: #1c293b;
        border: 1px solid #33445c;
        border-radius: 9px;
        padding: 7px 9px;
        font-weight: 850;
    }
    QLabel#splitterPanelSubtitle {
        color: #aebbd0;
        background: transparent;
        padding: 0px 3px 2px 3px;
    }
    QScrollBar:vertical {
        background: #0d131d;
        width: @SCROLLBAR@px;
        margin: 0px;
    }
    QScrollBar::handle:vertical {
        background: #374d67;
        min-height: @BUTTON_MIN@px;
        border-radius: 6px;
    }
    QScrollBar::handle:vertical:hover {
        background: #517396;
    }
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
        height: 0px;
    }
    QScrollBar:horizontal {
        background: #0d131d;
        height: @SCROLLBAR@px;
        margin: 0px;
    }
    QScrollBar::handle:horizontal {
        background: #374d67;
        min-width: 28px;
        border-radius: 6px;
    }
    """
    for key, value in values.items():
        css = css.replace(f"@{key}@", str(value))
    return css
