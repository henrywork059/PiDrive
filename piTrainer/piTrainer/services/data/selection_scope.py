"""Read-only, source-row-safe scope reporting for the Data page (R37).

The Data Record Preview deliberately hides generated derivatives. Counts are
observations of the loaded active DataFrame, current preview filter, and actual
QTableView source-row selection, not a second selection/proxy model.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable

import pandas as pd

from .visibility_service import synthetic_row_mask


@dataclass(frozen=True)
class SelectionScope:
    """Counts from the *loaded* sessions, rather than the currently checked list."""

    visible: int
    selected_visible: int
    all_active: int
    hidden: int | None
    generated_active: int
    selected_generated: int

    def toolbar_text(self) -> str:
        hidden = str(self.hidden) if self.hidden is not None else 'Unavailable'
        return (
            f'Visible: {self.visible}  |  Selected visible: {self.selected_visible}'
            f'  |  All active: {self.all_active}  |  Hidden: {hidden}'
            f'  |  Generated: {self.generated_active}'
        )

    def detail_text(self) -> str:
        return (
            'Visible = filtered, editable source frames. '
            'Selected visible = rows targeted by bulk edits/hide. '
            'All active = non-hidden rows in loaded sessions, including generated rows. '
            'Hidden = distinct frames hidden in loaded session metadata. '
            'Generated = active synthetic derivatives; excluded from Data review by default.'
        )


def count_selected_generated(records: list[dict[str, Any]]) -> int:
    """Use the shared NaN-safe dataframe mask for selected source rows."""
    return int(synthetic_row_mask(pd.DataFrame(records)).sum()) if records else 0


def summarize_selection(
    active_df: pd.DataFrame,
    preview_df: pd.DataFrame,
    selected_records: Iterable[dict[str, Any]],
    *,
    hidden_count: int | None = None,
) -> SelectionScope:
    """Report counts without modifying any selection, DataFrame or sort order."""
    active = active_df if isinstance(active_df, pd.DataFrame) else pd.DataFrame()
    preview = preview_df if isinstance(preview_df, pd.DataFrame) else pd.DataFrame()
    records = list(selected_records)
    generated_total = int(synthetic_row_mask(active).sum()) if not active.empty else 0
    return SelectionScope(
        visible=len(preview),
        selected_visible=len(records),
        all_active=len(active),
        hidden=max(0, int(hidden_count)) if hidden_count is not None else None,
        generated_active=generated_total,
        selected_generated=count_selected_generated(records),
    )


def selected_visible_impact(records: Iterable[dict[str, Any]]) -> str:
    """Exact selected-view row count; never implies all active rows are targeted."""
    selected = list(records)
    generated = count_selected_generated(selected)
    return (
        f'Affected scope: {len(selected)} selected visible frame(s). '
        f'Generated derivatives included: {generated} of {len(selected)}. '
        'Unselected visible frames and other active loaded frames are not targeted.'
    )
