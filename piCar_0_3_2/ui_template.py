# ui_template.py

from ui_base import BASE_HTML
from ui_status_panel import STATUS_PANEL
from ui_viewer_panel import VIEWER_PANEL
from ui_model_panel import MODEL_PANEL
from ui_manual_panel import MANUAL_PANEL
from ui_record_panel import RECORD_PANEL
from ui_script import MAIN_SCRIPT

_html = BASE_HTML
_html = _html.replace("{status_panel}", STATUS_PANEL)
_html = _html.replace("{viewer_panel}", VIEWER_PANEL)
_html = _html.replace("{model_panel}", MODEL_PANEL)
_html = _html.replace("{manual_panel}", MANUAL_PANEL)
_html = _html.replace("{record_panel}", RECORD_PANEL)
_html = _html.replace("{script}", MAIN_SCRIPT)

INDEX_HTML = _html
