from __future__ import annotations

import numpy as np

from ...ui.theme import theme_color
from ...ui.plot_style import style_plot_axis, style_plot_legend


def render_validation_plot(ax, result: dict, plot_type: str) -> None:
    steering_true = np.asarray(result['steering_true'])
    throttle_true = np.asarray(result['throttle_true'])
    steering_pred = np.asarray(result['steering_pred'])
    throttle_pred = np.asarray(result['throttle_pred'])
    steering_error = np.asarray(result['steering_error'])
    throttle_error = np.asarray(result['throttle_error'])

    style_plot_axis(ax)

    if plot_type == 'Prediction vs Ground Truth':
        ax.scatter(steering_true, steering_pred, alpha=0.72, label='Steering', color=theme_color('plot_steering'))
        ax.scatter(throttle_true, throttle_pred, alpha=0.72, marker='x', label='Speed', color=theme_color('plot_speed'))
        combined = np.concatenate([steering_true, throttle_true, steering_pred, throttle_pred])
        lo, hi = float(np.min(combined)), float(np.max(combined))
        if lo == hi:
            lo, hi = lo - 1.0, hi + 1.0
        ax.plot([lo, hi], [lo, hi], linestyle='--', linewidth=1.2, color=theme_color('plot_reference'))
        ax.set_xlabel('Ground truth (normalized)')
        ax.set_ylabel('Prediction (normalized)')
        ax.set_title('Prediction vs Ground Truth')
        style_plot_legend(ax)
        return

    if plot_type == 'Prediction Error Histogram':
        ax.hist(steering_error, bins=30, alpha=0.72, label='Steering Error', color=theme_color('plot_steering'), edgecolor=theme_color('bg_panel'))
        ax.hist(throttle_error, bins=30, alpha=0.72, label='Speed Error', color=theme_color('plot_error'), edgecolor=theme_color('bg_panel'))
        ax.axvline(0.0, linestyle='--', linewidth=1.2, color=theme_color('plot_reference'))
        ax.set_xlabel('Prediction error (normalized)')
        ax.set_ylabel('Frame count')
        ax.set_title('Prediction Error Histogram')
        style_plot_legend(ax)
        return

    sample_count = min(120, len(steering_true))
    x = np.arange(sample_count)
    ax.plot(x, steering_true[:sample_count], label='Steering GT', color=theme_color('plot_steering'), linewidth=1.8)
    ax.plot(x, steering_pred[:sample_count], label='Steering Pred', color=theme_color('primary_hover'), linewidth=1.5, linestyle='--')
    ax.plot(x, throttle_true[:sample_count], label='Speed GT', color=theme_color('plot_speed'), linewidth=1.8)
    ax.plot(x, throttle_pred[:sample_count], label='Speed Pred', color=theme_color('warning_hover'), linewidth=1.5, linestyle='--')
    ax.set_xlabel('Sample index (frame)')
    ax.set_ylabel('Normalized control value')
    ax.set_title('Sample Prediction Trace')
    style_plot_legend(ax)

