from __future__ import annotations

from .formatting import stylesheet_tokens


def build_stylesheet(density: str = "comfortable") -> str:
    values = stylesheet_tokens(density)
    css = """
    QWidget {
        font-size: @BASE_FONT@px;
        color: @COLOR_TEXT_SECONDARY@;
        background: @COLOR_BG_PANEL@;
    }
    QMainWindow {
        background: @COLOR_BG_APP@;
    }
    QToolTip {
        background: @COLOR_BG_OVERLAY@;
        color: @COLOR_TEXT_PRIMARY@;
        border: 1px solid @COLOR_PRIMARY_BORDER@;
        padding: 6px;
    }
    QToolBar {
        background: @COLOR_BG_PANEL_ALT@;
        border-bottom: 1px solid @COLOR_BORDER_SUBTLE@;
        spacing: 8px;
        padding: 6px;
    }
    QMainWindow::separator {
        background: @COLOR_PRIMARY@;
        width: 4px;
        height: 4px;
    }
    QStatusBar {
        background: @COLOR_BG_APP@;
        color: @COLOR_TEXT_MUTED@;
        border-top: 1px solid @COLOR_BORDER_SUBTLE@;
        padding: 3px 8px;
    }
    QFrame[role='pageShell'] {
        background: @COLOR_BG_SHELL@;
        border: none;
    }
    QFrame#pageBanner {
        background: @COLOR_INFO_SURFACE@;
        border: 1px solid @COLOR_BORDER_STRONG@;
        border-left: 4px solid @COLOR_INFO@;
        border-radius: 7px;
    }
    QLabel#pageBannerTitle {
        color: @COLOR_TEXT_PRIMARY@;
        background: transparent;
        font-size: @BANNER_TITLE@px;
        font-weight: 900;
        letter-spacing: 0.2px;
    }
    QLabel#pageBannerSummary {
        color: @COLOR_TEXT_SECONDARY@;
        background: transparent;
        font-size: @BASE_FONT@px;
        line-height: 1.25em;
    }
    QPushButton#pageBannerNextButton {
        color: @COLOR_TEXT_ON_DARK@;
        background: @COLOR_SUCCESS@;
        border: 1px solid @COLOR_SUCCESS_BORDER@;
        border-radius: 8px;
        padding: 4px 10px;
        font-weight: 850;
        text-align: center;
    }
    QPushButton#pageBannerNextButton:hover {
        background: @COLOR_SUCCESS_HOVER@;
        border-color: @COLOR_SUCCESS_BORDER@;
    }
    QPushButton#pageBannerNextButton:pressed {
        background: @COLOR_SUCCESS_ACTIVE@;
    }
    QDockWidget {
        color: @COLOR_TEXT_PRIMARY@;
        font-weight: 700;
    }
    QDockWidget::title {
        background: @COLOR_BG_PANEL_LIFT@;
        color: @COLOR_TEXT_PRIMARY@;
        padding: 7px 10px;
        border: 1px solid @COLOR_PRIMARY_BORDER@;
        border-bottom: none;
    }
    #dockPageFiller {
        background: @COLOR_BG_SHELL@;
        border: none;
    }
    QGroupBox {
        border: 1px solid @COLOR_BORDER_SUBTLE@;
        border-radius: 9px;
        margin-top: 9px;
        padding: 10px 8px 8px 8px;
        background: @COLOR_BG_PANEL_ALT@;
        font-weight: 650;
        color: @COLOR_TEXT_PRIMARY@;
    }
    QGroupBox::title {
        subcontrol-origin: margin;
        left: 12px;
        padding: 0 5px 0 5px;
        color: @COLOR_TEXT_PRIMARY@;
    }
    QGroupBox[role='formGroup'] {
        border-color: @COLOR_BORDER@;
        background: @COLOR_BG_PANEL@;
    }
    QFrame[role='splitterPanel'] QGroupBox[role='formGroup'] {
        margin-top: 8px;
    }
    QPushButton {
        min-height: @BUTTON_MIN@px;
        padding: 4px 10px;
        background: @COLOR_BG_PANEL_LIFT@;
        color: @COLOR_TEXT_SECONDARY@;
        border: 1px solid @COLOR_BORDER@;
        border-radius: 7px;
        font-weight: 600;
    }
    QPushButton:hover {
        background: @COLOR_BG_OVERLAY@;
        border-color: @COLOR_PRIMARY_HOVER@;
        color: @COLOR_TEXT_PRIMARY@;
    }
    QPushButton:pressed {
        background: @COLOR_BG_INPUT_ALT@;
    }
    QPushButton:disabled {
        background: @COLOR_BG_INPUT@;
        color: @COLOR_TEXT_DISABLED@;
        border-color: @COLOR_BORDER_SUBTLE@;
    }
    QPushButton[role='primary'] {
        background: @COLOR_SUCCESS@;
        border-color: @COLOR_SUCCESS_BORDER@;
        color: @COLOR_TEXT_ON_DARK@;
        font-weight: 760;
    }
    QPushButton[role='primary']:hover {
        background: @COLOR_SUCCESS_HOVER@;
        border-color: @COLOR_SUCCESS_BORDER@;
    }
    QPushButton[role='primary']:pressed {
        background: @COLOR_SUCCESS_ACTIVE@;
    }
    QPushButton[role='nextStep'] {
        min-height: @NEXT_MIN@px;
        padding: 7px 12px;
        background: @COLOR_SUCCESS@;
        border: 2px solid @COLOR_SUCCESS_BORDER@;
        color: @COLOR_TEXT_ON_DARK@;
        border-radius: 9px;
        font-weight: 850;
    }
    QPushButton[role='nextStep']:hover {
        background: @COLOR_SUCCESS_HOVER@;
        border-color: @COLOR_SUCCESS_BORDER@;
    }
    QPushButton[role='nextStep']:pressed {
        background: @COLOR_SUCCESS_ACTIVE@;
    }
    QPushButton[role='nextStep']:disabled {
        background: @COLOR_SUCCESS_SURFACE@;
        color: @COLOR_TEXT_DISABLED@;
        border-color: @COLOR_BORDER_SUBTLE@;
    }
    QPushButton[role='nextStep'][pulse='true'] {
        background: @COLOR_SUCCESS_HOVER@;
        border-color: @COLOR_TEXT_PRIMARY@;
    }
    QPushButton[role='nextStep'][spotlight='true'] {
        background: @COLOR_SUCCESS_HOVER@;
        border: 3px solid @COLOR_TEXT_PRIMARY@;
        color: @COLOR_TEXT_ON_DARK@;
    }
    QPushButton[role='danger'] {
        background: @COLOR_DANGER@;
        border-color: @COLOR_DANGER_BORDER@;
        color: @COLOR_TEXT_ON_DARK@;
    }
    QPushButton[role='danger']:hover {
        background: @COLOR_DANGER_HOVER@;
    }
    QPushButton[role='danger']:pressed {
        background: @COLOR_DANGER_ACTIVE@;
    }
    QPushButton[role='secondary'] {
        background: @COLOR_BG_PANEL_LIFT@;
        color: @COLOR_TEXT_SECONDARY@;
    }
    QPushButton[role='amber'] {
        background: @COLOR_WARNING@;
        border-color: @COLOR_WARNING_BORDER@;
        color: @COLOR_TEXT_ON_WARNING@;
        font-weight: 800;
    }
    QPushButton[role='amber']:hover {
        background: @COLOR_WARNING_HOVER@;
        border-color: @COLOR_WARNING_BORDER@;
        color: @COLOR_TEXT_ON_WARNING@;
    }
    QPushButton[role='amber']:pressed {
        background: @COLOR_WARNING_ACTIVE@;
        color: @COLOR_TEXT_ON_WARNING@;
    }
    QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox, QListWidget, QTextEdit, QPlainTextEdit, QTableWidget, QTableView {
        min-height: @INPUT_MIN@px;
        background: @COLOR_BG_INPUT@;
        color: @COLOR_TEXT_SECONDARY@;
        border: 1px solid @COLOR_BORDER@;
        border-radius: 7px;
        selection-background-color: @COLOR_SELECTION@;
        selection-color: @COLOR_TEXT_ON_DARK@;
    }
    QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus, QComboBox:focus, QTextEdit:focus, QPlainTextEdit:focus, QTableWidget:focus, QTableView:focus, QListWidget:focus {
        border: 1px solid @COLOR_INFO@;
    }
    QPlainTextEdit {
        padding: 8px;
        font-family: Consolas, 'Cascadia Mono', monospace;
        border-radius: 9px;
    }
    QTableWidget, QTableView {
        gridline-color: @COLOR_BORDER_SUBTLE@;
        alternate-background-color: @COLOR_TABLE_ALT@;
        background: @COLOR_BG_INPUT@;
        border-radius: 9px;
    }
    QTableWidget::item, QTableView::item {
        padding: 5px;
    }
    QTableWidget::item:selected, QTableView::item:selected, QListWidget::item:selected {
        background: @COLOR_SELECTION@;
        color: @COLOR_TEXT_ON_DARK@;
    }
    QTableView#recordPreviewTable {
        alternate-background-color: @COLOR_BG_PANEL_LIFT@;
        selection-background-color: @COLOR_WARNING@;
        selection-color: @COLOR_TEXT_ON_WARNING@;
    }
    QTableView#recordPreviewTable::item {
        border-bottom: 1px solid @COLOR_BORDER_SUBTLE@;
    }
    QTableView#recordPreviewTable::item:selected {
        background: @COLOR_WARNING@;
        color: @COLOR_TEXT_ON_WARNING@;
        border: 1px solid @COLOR_WARNING_BORDER@;
        font-weight: 900;
    }
    #sessionListWidget {
        padding: 7px;
    }
    #sessionRow {
        background: @COLOR_BG_INPUT_ALT@;
        border: 1px solid @COLOR_BORDER_SUBTLE@;
        border-radius: 9px;
    }
    #sessionRow:hover {
        background: @COLOR_INFO_SURFACE@;
        border: 1px solid @COLOR_INFO@;
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
        border: 2px solid @COLOR_INFO@;
        background: @COLOR_BG_INPUT@;
    }
    #sessionRowCheckbox::indicator:hover {
        border-color: @COLOR_INFO_HOVER@;
        background: @COLOR_INFO_SURFACE@;
    }
    #sessionRowCheckbox::indicator:checked {
        background: @COLOR_INFO@;
        border: 2px solid @COLOR_TEXT_PRIMARY@;
    }
    #sessionRowLabel {
        color: @COLOR_TEXT_PRIMARY@;
        background: transparent;
        font-weight: 600;
        padding-top: 1px;
    }
    QHeaderView::section {
        background: @COLOR_BG_PANEL_LIFT@;
        color: @COLOR_TEXT_PRIMARY@;
        border: 1px solid @COLOR_BORDER@;
        padding: 5px;
        font-weight: 700;
    }
    QTabWidget::pane {
        border: 1px solid @COLOR_BORDER_SUBTLE@;
        background: @COLOR_BG_PANEL@;
    }
    QTabWidget[role='contentTabs']::pane {
        border: 1px solid @COLOR_BORDER_SUBTLE@;
        border-radius: 8px;
        background: @COLOR_BG_SHELL@;
    }
    QTabWidget[role='contentTabs'] QTabBar::tab {
        min-width: @WORKFLOW_TAB_MIN@px;
    }
    QTabWidget#mainWorkflowTabs::pane {
        border: 0px;
        background: @COLOR_BG_SHELL@;
    }
    QTabWidget#mainWorkflowTabs QTabBar::tab {
        min-width: @MAIN_TAB_MIN@px;
        padding: 8px 14px;
        margin-right: 5px;
        border-top-left-radius: 10px;
        border-top-right-radius: 10px;
    }
    QTabWidget#mainWorkflowTabs QTabBar::tab:selected {
        background: @COLOR_PRIMARY@;
        border-color: @COLOR_PRIMARY_BORDER@;
        color: @COLOR_TEXT_ON_DARK@;
    }
    QTabBar::tab {
        min-width: 104px;
        padding: 7px 9px;
        background: @COLOR_BG_PANEL_ALT@;
        color: @COLOR_TEXT_MUTED@;
        border: 1px solid @COLOR_BORDER_SUBTLE@;
        border-bottom: none;
        margin-right: 3px;
        border-top-left-radius: 7px;
        border-top-right-radius: 7px;
        font-weight: 700;
    }
    QTabBar::tab:selected {
        background: @COLOR_BG_PANEL_LIFT@;
        color: @COLOR_TEXT_PRIMARY@;
        border-color: @COLOR_PRIMARY@;
    }
    QTabBar::tab:hover:!selected {
        background: @COLOR_INFO_SURFACE@;
        color: @COLOR_TEXT_PRIMARY@;
        border-color: @COLOR_INFO@;
    }
    QTabWidget[role='workflowTabs']::pane {
        background: @COLOR_BG_SHELL@;
        border: 1px solid @COLOR_BORDER_SUBTLE@;
        border-radius: 8px;
    }
    QTabWidget[role='workflowTabs'] QTabBar::tab {
        min-width: @WORKFLOW_TAB_MIN@px;
        padding: 7px 9px;
        font-size: 12px;
    }
    QTabWidget[role='workflowTabs'] QTabBar::tab:selected {
        background: @COLOR_INFO_SURFACE@;
        border-color: @COLOR_INFO@;
        color: @COLOR_TEXT_PRIMARY@;
    }
    QProgressBar {
        min-height: 22px;
        border: 1px solid @COLOR_BORDER@;
        border-radius: 7px;
        text-align: center;
        background: @COLOR_BG_INPUT@;
        color: @COLOR_TEXT_SECONDARY@;
    }
    QProgressBar::chunk {
        background: @COLOR_PRIMARY@;
        border-radius: 6px;
    }

    QSlider::groove:horizontal {
        height: 7px;
        background: @COLOR_SLIDER_TRACK@;
        border: 1px solid @COLOR_BORDER_SUBTLE@;
        border-radius: 4px;
    }
    QSlider::sub-page:horizontal {
        background: @COLOR_SLIDER_STANDARD_FILL@;
        border-radius: 4px;
    }
    QSlider::add-page:horizontal {
        background: @COLOR_SLIDER_TRACK@;
        border-radius: 4px;
    }
    QSlider::handle:horizontal {
        width: 18px;
        height: 18px;
        margin: -6px 0px;
        background: @COLOR_SLIDER_HANDLE@;
        border: 2px solid @COLOR_SLIDER_HANDLE_BORDER@;
        border-radius: 9px;
    }
    QSlider::handle:horizontal:hover {
        background: @COLOR_SLIDER_HANDLE_HOVER@;
        border-color: @COLOR_TEXT_PRIMARY@;
    }
    QSlider:disabled::groove:horizontal,
    QSlider:disabled::add-page:horizontal,
    QSlider:disabled::sub-page:horizontal {
        background: @COLOR_BG_INPUT@;
        border-color: @COLOR_BORDER_SUBTLE@;
    }
    QSlider:disabled::handle:horizontal {
        background: @COLOR_TEXT_DISABLED@;
        border-color: @COLOR_BORDER_SUBTLE@;
    }
    QCheckBox {
        color: @COLOR_TEXT_PRIMARY@;
        spacing: 8px;
        background: transparent;
    }
    QCheckBox::indicator {
        width: 18px;
        height: 18px;
        border-radius: 5px;
        border: 2px solid @COLOR_INFO@;
        background: @COLOR_BG_INPUT@;
    }
    QCheckBox::indicator:hover {
        border-color: @COLOR_INFO_HOVER@;
        background: @COLOR_INFO_SURFACE@;
    }
    QCheckBox::indicator:checked {
        background: @COLOR_INFO@;
        border: 2px solid @COLOR_TEXT_PRIMARY@;
        image: none;
    }

    #controlStack {
        background: @COLOR_BG_SHELL@;
        border: none;
    }
    QScrollArea {
        background: @COLOR_BG_SHELL@;
        border: none;
    }
    QScrollArea[role='workflowScroll'], QScrollArea[role='panelContentScroll'] {
        border: 0px;
        border-radius: 8px;
    }
    QScrollArea[role='panelContentScroll'] {
        background: transparent;
    }
    QToolButton#collapsibleSectionHeader {
        background: @COLOR_BG_PANEL_LIFT@;
        color: @COLOR_TEXT_PRIMARY@;
        border: 1px solid @COLOR_BORDER@;
        border-radius: 9px;
        padding: 7px 9px;
        font-weight: 800;
        text-align: left;
    }
    QToolButton#collapsibleSectionHeader:hover {
        background: @COLOR_INFO_SURFACE@;
        border-color: @COLOR_INFO@;
    }
    QToolButton#collapsibleSectionHeader:checked {
        background: @COLOR_BG_OVERLAY@;
        border-color: @COLOR_PRIMARY@;
    }
    QFrame#collapsibleSectionBody {
        background: @COLOR_BG_PANEL@;
        border: 1px solid @COLOR_BORDER_SUBTLE@;
        border-top: none;
        border-bottom-left-radius: 9px;
        border-bottom-right-radius: 9px;
    }
    QWidget#collapsibleSection {
        background: transparent;
    }
    QLabel#sidebarIntro, QLabel#quickHint {
        background: @COLOR_INFO_SURFACE@;
        color: @COLOR_TEXT_SECONDARY@;
        border: 1px solid @COLOR_BORDER_STRONG@;
        border-radius: 9px;
        padding: 7px 9px;
        font-weight: 500;
    }
    QLabel[role='muted'] {
        color: @COLOR_TEXT_MUTED@;
    }
    QLabel[role='hint'] {
        color: @COLOR_TEXT_SECONDARY@;
    }
    QLabel[role='statValue'] {
        color: @COLOR_TEXT_PRIMARY@;
        background: @COLOR_BG_INPUT_ALT@;
        border: 1px solid @COLOR_INFO@;
        border-radius: 8px;
        padding: 5px 8px;
        font-weight: 850;
    }
    QLabel[role='summaryLine'] {
        color: @COLOR_TEXT_SECONDARY@;
        background: @COLOR_BG_INPUT_ALT@;
        border: 1px solid @COLOR_BORDER@;
        border-radius: 9px;
        padding: 7px 9px;
    }

    QLabel[role='preprocessStatus'] {
        color: @COLOR_TEXT_SECONDARY@;
        background: @COLOR_BG_INPUT_ALT@;
        border: 1px solid @COLOR_BORDER@;
        border-radius: 9px;
        padding: 8px 10px;
        font-weight: 750;
    }
    QLabel[role='preprocessStatus'][status='running'],
    QLabel[role='preprocessStatus'][status='preview'] {
        color: @COLOR_TEXT_ON_WARNING@;
        background: @COLOR_WARNING@;
        border: 1px solid @COLOR_WARNING_BORDER@;
    }
    QLabel[role='preprocessStatus'][status='done'] {
        color: @COLOR_TEXT_ON_DARK@;
        background: @COLOR_SUCCESS@;
        border: 1px solid @COLOR_SUCCESS_BORDER@;
        font-weight: 900;
    }
    QLabel[role='preprocessStatus'][status='warning'] {
        color: @COLOR_TEXT_ON_DARK@;
        background: @COLOR_DANGER@;
        border: 1px solid @COLOR_DANGER_BORDER@;
        font-weight: 850;
    }

    QLabel[role='summaryBlock'] {
        color: @COLOR_TEXT_PRIMARY@;
        background: @COLOR_BG_INPUT_ALT@;
        border: 1px solid @COLOR_INFO@;
        border-radius: 9px;
        padding: 7px 9px;
    }

    QSplitter[role='pageSplitter'] {
        background: @COLOR_BG_SHELL@;
    }
    QSplitter[role='pageSplitter']::handle {
        background: @COLOR_SPLITTER@;
        border: 1px solid @COLOR_SPLITTER_BORDER@;
        border-radius: 2px;
        margin: 1px;
    }
    QSplitter[role='pageSplitter']::handle:hover {
        background: @COLOR_SPLITTER_HOVER@;
        border-color: @COLOR_PRIMARY_BORDER@;
    }
    QFrame[role='splitterPanel'] {
        background: @COLOR_BG_PANEL@;
        border: 1px solid @COLOR_BORDER_SUBTLE@;
        border-radius: 9px;
    }
    QLabel#splitterPanelTitle {
        color: @COLOR_TEXT_PRIMARY@;
        background: @COLOR_BG_PANEL_LIFT@;
        border: 1px solid @COLOR_BORDER@;
        border-left: 3px solid @COLOR_INFO@;
        border-radius: 9px;
        padding: 7px 9px;
        font-weight: 850;
    }
    QLabel#splitterPanelSubtitle {
        color: @COLOR_TEXT_MUTED@;
        background: transparent;
        padding: 0px 3px 2px 3px;
    }
    QScrollBar:vertical {
        background: @COLOR_SCROLL_TRACK@;
        width: @SCROLLBAR@px;
        margin: 0px;
    }
    QScrollBar::handle:vertical {
        background: @COLOR_SCROLL_HANDLE@;
        min-height: @BUTTON_MIN@px;
        border-radius: 3px;
    }
    QScrollBar::handle:vertical:hover {
        background: @COLOR_SCROLL_HANDLE_HOVER@;
    }
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
        height: 0px;
    }
    QScrollBar:horizontal {
        background: @COLOR_SCROLL_TRACK@;
        height: @SCROLLBAR@px;
        margin: 0px;
    }
    QScrollBar::handle:horizontal {
        background: @COLOR_SCROLL_HANDLE@;
        min-width: 24px;
        border-radius: 3px;
    }
    QScrollBar::handle:horizontal:hover {
        background: @COLOR_SCROLL_HANDLE_HOVER@;
    }
    QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
        width: 0px;
    }
    QAbstractScrollArea::corner {
        background: @COLOR_SCROLL_TRACK@;
    }
    """
    for key, value in values.items():
        css = css.replace(f"@{key}@", str(value))
    return css
