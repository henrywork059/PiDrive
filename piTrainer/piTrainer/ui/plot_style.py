"""Shared Matplotlib presentation only; never change samples or axis limits."""
from .theme import theme_color


def style_plot_axis(ax):
    ax.figure.patch.set_facecolor(theme_color("plot_bg"))
    ax.set_facecolor(theme_color("plot_axis"))
    ax.tick_params(colors=theme_color("text_secondary"), labelsize=9, length=3)
    ax.xaxis.label.set_color(theme_color("text_secondary"))
    ax.yaxis.label.set_color(theme_color("text_secondary"))
    ax.title.set_color(theme_color("text_primary"))
    ax.title.set_fontsize(11)
    for spine in ax.spines.values():
        spine.set_color(theme_color("border"))
    ax.set_axisbelow(True)
    ax.grid(True, color=theme_color("plot_grid"), alpha=0.55)


def style_plot_legend(ax, *, loc="best"):
    legend = ax.legend(loc=loc, fontsize=9)
    if legend is not None:
        legend.get_frame().set_facecolor(theme_color("plot_bg"))
        legend.get_frame().set_edgecolor(theme_color("border"))
        for label in legend.get_texts():
            label.set_color(theme_color("text_primary"))
    return legend
