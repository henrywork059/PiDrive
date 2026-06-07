from __future__ import annotations

from pathlib import Path

import pandas as pd

from ..panels.data.preview_panel import PreviewPanel
from ..services.data.stats_service import calculate_basic_stats
from ..services.data.visibility_service import is_synthetic_record, without_synthetic_rows


class DataPageSupportMixin:
    @staticmethod
    def _record_identity(record) -> tuple[str, str, str, str]:
        return PreviewPanel.record_identity(record)

    @staticmethod
    def _bulk_edit_target_key(record) -> tuple[str, str, str, str]:
        return (
            str(record.get('session', '') or ''),
            str(record.get('frame_id', '') or ''),
            Path(str(record.get('abs_image', '') or record.get('image_path', '') or record.get('frame', '') or '')).name,
            str(record.get('ts', '') or ''),
        )

    @staticmethod
    def _record_mask(df: pd.DataFrame, identity: tuple[str, str, str, str]):
        if df.empty:
            return pd.Series([], dtype=bool)

        def column_text(column: str) -> pd.Series:
            return DataPageSupportMixin._column_text(df, column)

        session, frame_id, ts, abs_image = identity
        return (
            column_text('session') == session
        ) & (
            column_text('frame_id') == frame_id
        ) & (
            column_text('ts') == ts
        ) & (
            column_text('abs_image') == abs_image
        )

    @staticmethod
    def _review_dataframe(df: pd.DataFrame) -> pd.DataFrame:
        """Return Data-page review rows with generated/synthetic copies hidden by default."""
        return without_synthetic_rows(df).reset_index(drop=True) if isinstance(df, pd.DataFrame) else pd.DataFrame()

    @staticmethod
    def _column_text(df: pd.DataFrame, column: str) -> pd.Series:
        if column in df.columns:
            series = df[column]
            return series.astype(object).where(series.notna(), '').astype(str)
        return pd.Series([''] * len(df), index=df.index, dtype=str)

    def _find_source_record_for_synthetic(self, record: dict) -> dict | None:
        if not record or not is_synthetic_record(record):
            return None
        source_frame_id = str(record.get('source_frame_id', '') or '').strip()
        if not source_frame_id:
            return None
        session = str(record.get('session', '') or '').strip()
        abs_image = str(record.get('abs_image', '') or '').strip()
        ts = str(record.get('ts', '') or '').strip()

        candidates = [
            self.current_preview_source_df,
            self._review_dataframe(self.state.filtered_df),
            self._review_dataframe(self.state.dataset_df),
        ]
        for df in candidates:
            if not isinstance(df, pd.DataFrame) or df.empty or 'frame_id' not in df.columns:
                continue
            mask = self._column_text(df, 'frame_id').str.strip().eq(source_frame_id)
            if session:
                mask &= self._column_text(df, 'session').str.strip().eq(session)
            if not mask.any() and abs_image:
                # Some older rows may not have a stable source_frame_id. Fall back
                # to the shared source image when it is in the same session.
                mask = self._column_text(df, 'abs_image').str.strip().eq(abs_image)
                if session:
                    mask &= self._column_text(df, 'session').str.strip().eq(session)
            if not mask.any() and ts:
                relaxed = self._column_text(df, 'frame_id').str.strip().eq(source_frame_id)
                relaxed &= self._column_text(df, 'ts').str.strip().eq(ts)
                if session:
                    relaxed &= self._column_text(df, 'session').str.strip().eq(session)
                mask = relaxed
            if mask.any():
                return df.loc[mask].iloc[0].to_dict()
        return None

    def _focus_target_record(self, record: dict) -> dict:
        self.last_focus_redirected_to_source = False
        self.last_focus_source_frame_id = ''
        source_record = self._find_source_record_for_synthetic(record)
        if source_record:
            self.last_focus_redirected_to_source = True
            self.last_focus_source_frame_id = str(record.get('source_frame_id', '') or '')
            return source_record
        return record

    def schedule_plot_refresh_from_preview(self) -> None:
        self.single_edit_plot_timer.start()

    def refresh_plot_from_preview(self) -> None:
        if hasattr(self, 'plot_panel'):
            self.plot_panel.set_dataframe(self.preview_panel.df)

    def refresh_from_state(self) -> None:
        self.current_preview_source_df = self._review_dataframe(self.state.filtered_df)
        self.stats_panel.set_stats(calculate_basic_stats(self.state.filtered_df))
        self.apply_preview_filter()
