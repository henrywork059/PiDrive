from __future__ import annotations

from typing import Mapping

# Central semantic colour tokens used by Qt stylesheets and matplotlib plots.
# Keep new colours here so pages and panels do not grow one-off palettes.
THEME_COLORS: Mapping[str, str] = {
    "bg_app": "#14171C",
    "bg_shell": "#14171C",
    "bg_panel": "#20252D",
    "bg_panel_alt": "#292F39",
    "bg_panel_lift": "#303846",
    "bg_input": "#191D24",
    "bg_input_alt": "#20252D",
    "bg_overlay": "#292F39",
    "text_primary": "#EDF1F7",
    "text_secondary": "#EDF1F7",
    "text_muted": "#A5AFBF",
    "text_disabled": "#8591A4",
    "text_on_dark": "#ffffff",
    "text_on_warning": "#14110a",
    "border_subtle": "#363F4B",
    "border": "#64748B",
    "border_strong": "#8492A6",
    "primary": "#6495FF",
    "primary_hover": "#8BADFF",
    "primary_active": "#315FD1",
    "primary_border": "#6495FF",
    "info": "#57C5E8",
    "info_hover": "#93E0F5",
    "info_surface": "#203144",
    "success": "#22c55e",
    "success_hover": "#34d399",
    "success_active": "#15803d",
    "success_surface": "#20362A",
    "success_border": "#86efac",
    "warning": "#facc15",
    "warning_hover": "#fde047",
    "warning_active": "#ca8a04",
    "warning_surface": "#3B321F",
    "warning_border": "#fef08a",
    "danger": "#B91C2C",
    "danger_hover": "#9F1239",
    "danger_active": "#5f1026",
    "danger_border": "#fb7185",
    "selection": "#315FD1",
    "selection_hover": "#315FD1",
    "table_alt": "#292F39",
    "scroll_track": "#14171C",
    "scroll_handle": "#64748B",
    "scroll_handle_hover": "#64748b",
    "splitter": "#363F4B",
    "splitter_hover": "#6495FF",
    "splitter_border": "#64748B",
    "slider_track": "#363F4B",
    "slider_standard_fill": "#6495FF",
    "slider_center_fill": "#22d3ee",
    "slider_center_marker": "#EDF1F7",
    "slider_handle": "#EDF1F7",
    "slider_handle_hover": "#d7e2f2",
    "slider_handle_border": "#22d3ee",
    "plot_bg": "#20252D",
    "plot_axis": "#14171C",
    "plot_grid": "#363F4B",
    "plot_steering": "#6495FF",
    "plot_speed": "#facc15",
    "plot_error": "#fb7185",
    "plot_reference": "#A5AFBF",
}


# Resolve the saved palette before creating widgets or plots.
_DARK_COLORS = dict(THEME_COLORS)
_LIGHT_COLORS = {**_DARK_COLORS, **{
    "bg_app": "#F4F6FA",
    "bg_shell": "#F4F6FA",
    "bg_panel": "#FFFFFF",
    "bg_panel_alt": "#E7EBF1",
    "bg_panel_lift": "#E7EBF1",
    "bg_input": "#FFFFFF",
    "bg_input_alt": "#F4F6FA",
    "bg_overlay": "#FFFFFF",
    "text_primary": "#20252D",
    "text_secondary": "#20252D",
    "text_muted": "#566171",
    "text_disabled": "#64748B",
    "border_subtle": "#CED5DF",
    "border": "#64748B",
    "border_strong": "#64748B",
    "primary": "#315FD1",
    "primary_hover": "#2546A5",
    "primary_active": "#2448AA",
    "primary_border": "#315FD1",
    "info": "#115E75",
    "info_hover": "#155E75",
    "info_surface": "#E1EFF9",
    "success": "#22C55E",
    "success_hover": "#34D399",
    "success_active": "#166534",
    "success_surface": "#E5F5E9",
    "success_border": "#166534",
    "warning": "#FACC15",
    "warning_hover": "#FDE047",
    "warning_active": "#92400E",
    "warning_surface": "#FFF1D6",
    "warning_border": "#92400E",
    "danger": "#B91C2C",
    "danger_hover": "#9F1239",
    "danger_active": "#7F1D1D",
    "danger_border": "#B91C2C",
    "selection": "#315FD1",
    "selection_hover": "#2546A5",
    "table_alt": "#F4F6FA",
    "scroll_track": "#E7EBF1",
    "scroll_handle": "#64748B",
    "scroll_handle_hover": "#475569",
    "splitter": "#CED5DF",
    "splitter_hover": "#315FD1",
    "splitter_border": "#64748B",
    "slider_track": "#CED5DF",
    "slider_standard_fill": "#315FD1",
    "slider_center_fill": "#115E75",
    "slider_center_marker": "#20252D",
    "slider_handle": "#FFFFFF",
    "slider_handle_hover": "#E7EBF1",
    "slider_handle_border": "#64748B",
    "plot_bg": "#FFFFFF",
    "plot_axis": "#F4F6FA",
    "plot_grid": "#CED5DF",
    "plot_steering": "#315FD1",
    "plot_speed": "#92400E",
    "plot_error": "#B91C1C",
    "plot_reference": "#566171"
}}
_ACTIVE_THEME = "dark"

def set_theme(name: str) -> str:
    global _ACTIVE_THEME
    _ACTIVE_THEME = name if name in ("dark", "light") else "dark"
    THEME_COLORS.update(_LIGHT_COLORS if _ACTIVE_THEME == "light" else _DARK_COLORS)
    return _ACTIVE_THEME

def current_theme() -> str:
    return _ACTIVE_THEME

def appearance_settings():
    from PySide6.QtCore import QSettings
    return QSettings("PiDrive", "piTrainerAppearance")

def saved_theme() -> str:
    name = appearance_settings().value("theme", "dark", type=str)
    return name if name in ("dark", "light") else "dark"

def save_theme(name: str) -> bool:
    from PySide6.QtCore import QSettings
    if name not in ("dark", "light"):
        return False
    settings = appearance_settings()
    settings.setValue("theme", name)
    settings.sync()
    return settings.status() == QSettings.Status.NoError

def theme_color(name: str, default: str = "#ffffff") -> str:
    """Return a central piTrainer theme colour."""
    return THEME_COLORS.get(name, default)
