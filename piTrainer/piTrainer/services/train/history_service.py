from __future__ import annotations



def build_plot_series(history: dict[str, list[float]]):
    for key, values in history.items():
        clean = [v for v in values if v is not None]
        if not clean:
            continue
        xs = list(range(1, len(clean) + 1))
        yield key, xs, clean
