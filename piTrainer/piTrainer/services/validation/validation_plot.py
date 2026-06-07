from __future__ import annotations

import numpy as np

from ...ui.theme import theme_color


def render_validation_plot(ax, result: dict, plot_type: str) -> None:
    steering_true = np.asarray(result['steering_true'])
    throttle_true = np.asarray(result['throttle_true'])
    steering_pred = np.asarray(result['steering_pred'])
    throttle_pred = np.asarray(result['throttle_pred'])
    steering_error = np.asarray(result['steering_error'])
    throttle_error = np.asarray(result['throttle_error'])

    ax.set_facecolor(theme_color('plot_axis'))
    ax.tick_params(colors=theme_color('text_secondary'))
    for spine in ax.spines.values():
        spine.set_color(theme_color('border'))

    label_color = theme_color('text_secondary')
    title_color = theme_color('text_primary')
    ax.xaxis.label.set_color(label_color)
    ax.yaxis.label.set_color(label_color)
    ax.title.set_color(title_color)
    ax.grid(True, color=theme_color('plot_grid'), alpha=0.35)

    def _style_legend() -> None:
        legend = ax.legend(loc='best')
        if legend is None:
            return
        legend.get_frame().set_facecolor(theme_color('plot_bg'))
        legend.get_frame().set_edgecolor(theme_color('border'))
        for text in legend.get_texts():
            text.set_color(theme_color('text_secondary'))

    if plot_type == 'Prediction vs Ground Truth':
        ax.scatter(steering_true, steering_pred, alpha=0.72, label='Steering', color=theme_color('plot_steering'))
        ax.scatter(throttle_true, throttle_pred, alpha=0.72, label='Speed', color=theme_color('plot_speed'))
        combined = np.concatenate([steering_true, throttle_true, steering_pred, throttle_pred])
        lo, hi = float(np.min(combined)), float(np.max(combined))
        if lo == hi:
            lo, hi = lo - 1.0, hi + 1.0
        ax.plot([lo, hi], [lo, hi], linestyle='--', linewidth=1.2, color=theme_color('plot_reference'))
        ax.set_xlabel('Ground Truth')
        ax.set_ylabel('Prediction')
        ax.set_title('Prediction vs Ground Truth')
        _style_legend()
        return

    if plot_type == 'Prediction Error Histogram':
        ax.hist(steering_error, bins=30, alpha=0.72, label='Steering Error', color=theme_color('plot_steering'), edgecolor=theme_color('bg_panel'))
        ax.hist(throttle_error, bins=30, alpha=0.72, label='Speed Error', color=theme_color('plot_error'), edgecolor=theme_color('bg_panel'))
        ax.axvline(0.0, linestyle='--', linewidth=1.2, color=theme_color('plot_reference'))
        ax.set_xlabel('Prediction Error')
        ax.set_ylabel('Count')
        ax.set_title('Prediction Error Histogram')
        _style_legend()
        return

    sample_count = min(120, len(steering_true))
    x = np.arange(sample_count)
    ax.plot(x, steering_true[:sample_count], label='Steering GT', color=theme_color('plot_steering'), linewidth=1.8)
    ax.plot(x, steering_pred[:sample_count], label='Steering Pred', color=theme_color('primary_hover'), linewidth=1.5)
    ax.plot(x, throttle_true[:sample_count], label='Speed GT', color=theme_color('plot_speed'), linewidth=1.8)
    ax.plot(x, throttle_pred[:sample_count], label='Speed Pred', color=theme_color('warning_hover'), linewidth=1.5)
    ax.set_xlabel('Sample Index')
    ax.set_ylabel('Value')
    ax.set_title('Sample Prediction Trace')
    _style_legend()

