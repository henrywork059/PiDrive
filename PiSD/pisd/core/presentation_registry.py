from __future__ import annotations

from copy import deepcopy
from typing import Any


COLOR_PALETTE: dict[str, str] = {
    "page_bg": "#07101d",
    "surface": "#0f172a",
    "surface_soft": "#1e293b",
    "line": "#334155",
    "text": "#e5eefc",
    "muted": "#98adc9",
    "primary": "#38bdf8",
    "ok": "#22c55e",
    "warning": "#f59e0b",
    "danger": "#e11d48",
    "recording": "#ef4444",
    "capture": "#14b8a6",
}

PRESENTATION_DEFAULTS: dict[str, Any] = {
    "theme": "dark",
    "layoutMode": "auto",
    "density": "compact",
    "fontScale": 1.0,
    "panelGap": 10,
    "panelRadius": 14,
    "borderStrength": 1.0,
    "shadowStrength": 0.20,
    "minPanelWidth": 280,
    "previewAspect": "16 / 9",
    "previewFit": "contain",
    "panelPadding": 0.86,
    "panelHeaderMode": "compact",
    "buttonScale": 0.92,
    "consoleHeight": 180,
    "cardAccent": "subtle",
    # This may tune panel proportions only. It must never be used to move
    # semantic panels between page regions.
    "adaptivePanels": True,
    "statusPanelHWeight": 1,
    "statusPanelVWeight": 1,
    "previewPanelHWeight": 2,
    "previewPanelVWeight": 2,
    "controlPanelHWeight": 1,
    "controlPanelVWeight": 1,
    "settingsPanelHWeight": 1,
    "settingsPanelVWeight": 1,
    "logPanelHWeight": 2,
    "logPanelVWeight": 1,
    "autoSave": True,
}

PRESENTATION_CONTROLS: list[str] = list(PRESENTATION_DEFAULTS.keys())

DESIGN_SYSTEM_ASSETS: dict[str, list[str]] = {
    "css_order": [
        "css/panel_presentation_global.css",
        "page-specific css",
        "css/unified_layout.css",
        "css/pisd_design_system.css",
    ],
    "js_order": [
        "js/panel_presentation_global.js",
        "page-specific js",
    ],
}

PAGE_LAYOUT_CONTRACTS: dict[str, dict[str, Any]] = {
    "front_page": {
        "path": "/",
        "purpose": "Compact mode selection and quick status.",
        "semantic_order": ["hero/status", "mode cards", "quick actions"],
    },
    "manual_drive": {
        "path": "/manual-drive",
        "purpose": "Simple user driving page with camera, compact status, drag pad, capture, recording, and STOP.",
        "desktop_grid_areas": [
            "status drive",
            "preview drive",
            "preview stop",
            "log log",
        ],
        "mobile_order": ["status", "preview", "drive", "stop", "log"],
        "fixed_rule": "Status and Camera Preview must remain stacked in the main column; Manual Control stays in the right control column on PC/iPad layouts. Presentation settings may resize but must not reorder these regions.",
    },
    "settings": {
        "path": "/settings",
        "purpose": "Single source for saved runtime and presentation settings.",
        "desktop_regions": ["save/apply", "panel style", "manual defaults", "camera", "motor", "response"],
    },
    "testing": {
        "path": "/testing",
        "purpose": "API/settings/FPS testing page, not final user control UI.",
    },
    "dashboard": {
        "path": "/dashboard",
        "purpose": "Main dashboard shell retained for development comparison.",
    },
    "panel_presentation": {
        "path": "/panel-presentation",
        "purpose": "Tuning page for shared panel style variables saved through settings.",
    },
    "panel_testing": {
        "path": "/panel-testing",
        "purpose": "Panel contract/layout lab. This is not the shared style source of truth.",
    },
}

STYLE_DEVELOPMENT_RULES: list[str] = [
    "Do not create new one-off panel shapes on individual pages.",
    "Use pisd_design_system.css for final cross-page layout, panel, button, and form decisions.",
    "Use panel_presentation_global.js only to apply saved CSS variables and data attributes.",
    "Page CSS may add component-specific details, but it must not override semantic page order.",
    "Manual Drive desktop grid is status above preview in the main column and drive/stop in the control column; mobile order is status -> preview -> controls -> stop -> log.",
    "Recording outputs must use one folder per continuous recording session. Manual single captures must share recordings/single_captures/YYYY-MM-DD with frames, manifest.json, and records.jsonl metadata.",
    "When adding a new page, load pisd_design_system.css last and use versioned static_asset links.",
]


def get_presentation_defaults() -> dict[str, Any]:
    return deepcopy(PRESENTATION_DEFAULTS)


def build_presentation_manifest(version: str) -> dict[str, Any]:
    return {
        "app": "PiSD",
        "version": version,
        "defaults": get_presentation_defaults(),
        "controls": list(PRESENTATION_CONTROLS),
        "assets": deepcopy(DESIGN_SYSTEM_ASSETS),
        "page_layout_contracts": deepcopy(PAGE_LAYOUT_CONTRACTS),
        "color_palette": deepcopy(COLOR_PALETTE),
        "development_rules": list(STYLE_DEVELOPMENT_RULES),
    }
