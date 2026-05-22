from __future__ import annotations

from typing import Any

import pandas as pd

from ...ui.theme import theme_color


def plot_sessions_for_combo(df: pd.DataFrame) -> list[str]:
    if df.empty or 'session' not in df.columns:
        return []
    return sorted(df['session'].dropna().astype(str).unique().tolist())


def filter_plot_dataframe(df: pd.DataFrame, session_name: str) -> pd.DataFrame:
    if df.empty:
        return df.copy()
    if session_name and session_name != 'All loaded sessions' and 'session' in df.columns:
        filtered = df[df['session'].astype(str) == session_name].copy()
        return filtered.reset_index(drop=True)
    return df.reset_index(drop=True).copy()


def build_plot_summary(df: pd.DataFrame) -> dict[str, Any]:
    if df.empty:
        return {
            'rows': 0,
            'sessions': 0,
            'steering_min': 0.0,
            'steering_max': 0.0,
            'steering_mean': 0.0,
            'throttle_min': 0.0,
            'throttle_max': 0.0,
            'throttle_mean': 0.0,
        }

    steering = _numeric_series(df, 'steering')
    throttle = _numeric_series(df, 'throttle')
    sessions = int(df['session'].nunique()) if 'session' in df.columns else 0
    return {
        'rows': int(len(df)),
        'sessions': sessions,
        'steering_min': float(steering.min()),
        'steering_max': float(steering.max()),
        'steering_mean': float(steering.mean()),
        'throttle_min': float(throttle.min()),
        'throttle_max': float(throttle.max()),
        'throttle_mean': float(throttle.mean()),
    }


def render_plot(ax, df: pd.DataFrame, plot_type: str, session_name: str) -> None:
    _style_axis(ax)
    if df.empty:
        ax.text(0.5, 0.5, 'No session data to plot', ha='center', va='center', color=theme_color('text_secondary'), transform=ax.transAxes)
        ax.set_xticks([])
        ax.set_yticks([])
        return

    if plot_type == 'Steering Histogram':
        steering = _numeric_series(df, 'steering')
        ax.hist(steering, bins=20, color=theme_color('plot_steering'), edgecolor=theme_color('bg_panel'))
        ax.set_xlabel('Steering value', color=theme_color('text_secondary'))
        ax.set_ylabel('Frame count', color=theme_color('text_secondary'))
    elif plot_type == 'Speed Histogram':
        throttle = _numeric_series(df, 'throttle')
        ax.hist(throttle, bins=20, color=theme_color('plot_speed'), edgecolor=theme_color('bg_panel'))
        ax.set_xlabel('Speed value', color=theme_color('text_secondary'))
        ax.set_ylabel('Frame count', color=theme_color('text_secondary'))
    elif plot_type == 'Steering vs Speed Scatter':
        steering = _numeric_series(df, 'steering')
        throttle = _numeric_series(df, 'throttle')
        ax.scatter(steering, throttle, s=14, alpha=0.75, color=theme_color('info'))
        ax.set_xlabel('Steering', color=theme_color('text_secondary'))
        ax.set_ylabel('Speed', color=theme_color('text_secondary'))
    elif plot_type == 'Mode Distribution':
        if 'mode' in df.columns:
            counts = df['mode'].fillna('unknown').astype(str).value_counts().sort_index()
            ax.bar(counts.index.tolist(), counts.values.tolist(), color=theme_color('primary'))
            ax.set_xlabel('Mode', color=theme_color('text_secondary'))
            ax.set_ylabel('Frame count', color=theme_color('text_secondary'))
            ax.tick_params(axis='x', rotation=20)
        else:
            ax.text(0.5, 0.5, 'No mode data available', ha='center', va='center', color=theme_color('text_secondary'), transform=ax.transAxes)
    elif plot_type == 'Session Frame Count':
        if 'session' in df.columns:
            counts = df['session'].fillna('unknown').astype(str).value_counts().sort_index()
            ax.bar(counts.index.tolist(), counts.values.tolist(), color=theme_color('primary'))
            ax.set_xlabel('Session', color=theme_color('text_secondary'))
            ax.set_ylabel('Frame count', color=theme_color('text_secondary'))
            ax.tick_params(axis='x', rotation=25)
        else:
            ax.text(0.5, 0.5, 'No session data available', ha='center', va='center', color=theme_color('text_secondary'), transform=ax.transAxes)
    else:
        x = range(len(df))
        steering = _numeric_series(df, 'steering')
        throttle = _numeric_series(df, 'throttle')
        ax.plot(x, steering, label='Steering', linewidth=1.8, color=theme_color('plot_steering'))
        ax.plot(x, throttle, label='Speed', linewidth=1.6, color=theme_color('plot_speed'))
        ax.set_xlabel('Frame index', color=theme_color('text_secondary'))
        ax.set_ylabel('Value', color=theme_color('text_secondary'))
        legend = ax.legend(loc='upper right')
        if legend is not None:
            frame = legend.get_frame()
            frame.set_facecolor(theme_color('plot_bg'))
            frame.set_edgecolor(theme_color('border'))
            for text in legend.get_texts():
                text.set_color(theme_color('text_primary'))

    ax.set_title(f'{plot_type} — {session_name}', color=theme_color('text_primary'))


def _numeric_series(df: pd.DataFrame, column: str) -> pd.Series:
    return pd.to_numeric(df.get(column, pd.Series(dtype=float)), errors='coerce').fillna(0.0)


def _style_axis(ax) -> None:
    ax.set_facecolor(theme_color('plot_axis'))
    ax.tick_params(colors=theme_color('text_secondary'))
    for spine in ax.spines.values():
        spine.set_color(theme_color('border'))
    ax.grid(True, color=theme_color('plot_grid'), alpha=0.35)
