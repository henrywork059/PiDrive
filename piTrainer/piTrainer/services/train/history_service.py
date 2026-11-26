from __future__ import annotations



def build_plot_series(history: dict[str, list[float]]):
    for key, values in history.items():
        # Preserve epoch positions and gaps. Matplotlib renders None as a break.
        if not any(value is not None for value in values):
            continue
        xs = list(range(1, len(values) + 1))
        yield key, xs, list(values)
