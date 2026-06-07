from __future__ import annotations

import pandas as pd
from PySide6.QtWidgets import QMessageBox

from ..services.data.delete_service import hide_frames_from_training, purge_hidden_frames, recover_hidden_frames
from ..services.data.stats_service import calculate_basic_stats


class DataPageVisibilityMixin:
    def _remove_identities_from_dataframe(self, df: pd.DataFrame, identities: list[tuple[str, str, str, str]]) -> pd.DataFrame:
        if df.empty or not identities:
            return df.copy()
        remove_mask = pd.Series([False] * len(df), index=df.index)
        for identity in identities:
            mask = self._record_mask(df, identity)
            if len(mask) == len(df):
                remove_mask |= mask
        return df[~remove_mask].copy().reset_index(drop=True)

    def _hide_records_from_loaded_data(self, identities: list[tuple[str, str, str, str]]) -> None:
        for df_attr in ['dataset_df', 'filtered_df', 'train_df', 'val_df']:
            df = getattr(self.state, df_attr)
            if isinstance(df, pd.DataFrame):
                setattr(self.state, df_attr, self._remove_identities_from_dataframe(df, identities))
        self.current_preview_source_df = self._remove_identities_from_dataframe(self.current_preview_source_df, identities)

    def _active_session_names_for_visibility_actions(self) -> list[str]:
        selected = [str(session).strip() for session in self.state.selected_sessions if str(session).strip()]
        if selected:
            return selected
        if not self.state.dataset_df.empty and 'session' in self.state.dataset_df.columns:
            names = self.state.dataset_df['session'].fillna('').astype(str).str.strip().tolist()
            return [name for index, name in enumerate(names) if name and name not in names[:index]]
        return []

    def _reload_loaded_sessions_after_visibility_change(self, status_message: str) -> None:
        sessions = self._active_session_names_for_visibility_actions()
        if sessions:
            self.state.selected_sessions = sessions
            self.session_source_panel.set_selected_sessions(sessions)
            self._load_sessions(sessions)
        else:
            self.refresh_from_state()
        self.image_preview_panel.clear_preview()
        self.bulk_edit_panel.set_selected_count(0)
        self.main_window.set_status_message(status_message)

    def recover_last_hidden_frames(self) -> None:
        self.preview_panel.stop_autoplay()
        sessions = self._active_session_names_for_visibility_actions()
        count = self.data_control_panel.recover_count()
        result = recover_hidden_frames(self.state.records_root_path, sessions, recover_all=False, count=count)
        recovered_count = int(result.get('recovered_count', 0) or 0)
        metadata_rows_changed = int(result.get('metadata_rows_changed', 0) or 0)
        failed_messages = list(result.get('failed_messages', []))

        if recovered_count:
            self._reload_loaded_sessions_after_visibility_change(
                f"Recovered {recovered_count} hidden frame(s) with {metadata_rows_changed} metadata row(s) changed."
            )
            return
        QMessageBox.information(self, 'Recover Frames', '\n'.join(failed_messages[:8]) if failed_messages else 'No hidden frames were recovered.')
        self.main_window.set_status_message('No hidden frames were recovered.')

    def recover_all_hidden_frames(self) -> None:
        self.preview_panel.stop_autoplay()
        sessions = self._active_session_names_for_visibility_actions()
        result = recover_hidden_frames(self.state.records_root_path, sessions, recover_all=True)
        recovered_count = int(result.get('recovered_count', 0) or 0)
        metadata_rows_changed = int(result.get('metadata_rows_changed', 0) or 0)
        failed_messages = list(result.get('failed_messages', []))

        if recovered_count:
            self._reload_loaded_sessions_after_visibility_change(
                f"Recovered all hidden frames: {recovered_count} frame(s), {metadata_rows_changed} metadata row(s) changed."
            )
            return
        QMessageBox.information(self, 'Recover All', '\n'.join(failed_messages[:8]) if failed_messages else 'No hidden frames were recovered.')
        self.main_window.set_status_message('No hidden frames were recovered.')

    def purge_hidden_frames_shortcut(self) -> None:
        self.preview_panel.stop_autoplay()
        sessions = self._active_session_names_for_visibility_actions()
        if not sessions:
            QMessageBox.information(self, 'Permanent Delete', 'Load or select a session first.')
            return

        confirm = QMessageBox.warning(
            self,
            'Delete Hidden Frames Permanently?',
            'This permanently deletes hidden rows and unreferenced image files from the loaded/selected sessions.\n\n'
            'This cannot be undone. Continue?',
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if confirm != QMessageBox.Yes:
            self.main_window.set_status_message('Permanent delete cancelled.')
            return

        result = purge_hidden_frames(self.state.records_root_path, sessions)
        purged_count = int(result.get('purged_count', 0) or 0)
        rows_removed = int(result.get('metadata_rows_removed', 0) or 0)
        image_files_deleted = int(result.get('image_files_deleted', 0) or 0)
        failed_messages = list(result.get('failed_messages', []))
        skipped_files = list(result.get('skipped_files', []))

        if purged_count:
            self._reload_loaded_sessions_after_visibility_change(
                f"Permanent delete: {purged_count} hidden frame(s), {rows_removed} metadata row(s), {image_files_deleted} image file(s)."
            )
            if skipped_files:
                QMessageBox.information(
                    self,
                    'Permanent Delete',
                    'Delete finished, but some files were kept:\n' + '\n'.join(skipped_files[:8]),
                )
            return
        QMessageBox.information(self, 'Permanent Delete', '\n'.join(failed_messages[:8]) if failed_messages else 'No hidden frames were deleted permanently.')
        self.main_window.set_status_message('No hidden frames were deleted permanently.')

    def delete_selected_frame(self) -> None:
        self.preview_panel.stop_autoplay()
        records = self.preview_panel.selected_records()
        if not records:
            QMessageBox.information(self, 'Hide Selected', 'Select one or more rows first.')
            return
        if not self.data_control_panel.deletion_confirmed():
            QMessageBox.information(
                self,
                'Hide Selected',
                'Tick "Confirm Hide" in 2 Hide & Recover before hiding frames. '
                'Images stay on disk.',
            )
            return

        identities = [self._record_identity(record) for record in records]
        result = hide_frames_from_training(self.state.records_root_path, records)
        hidden_count = int(result.get('hidden_count', 0) or 0)
        metadata_rows_changed = int(result.get('metadata_rows_changed', 0) or 0)
        failed_messages = list(result.get('failed_messages', []))

        if hidden_count:
            self._hide_records_from_loaded_data(identities)
            self.stats_panel.set_stats(calculate_basic_stats(self.state.filtered_df))
            self.apply_preview_filter()
            self.image_preview_panel.clear_preview()
            self.bulk_edit_panel.set_selected_count(0)
            self.main_window.on_dataset_loaded()
            self.main_window.set_status_message(
                f"Hidden {hidden_count} selected frame(s) from training. "
                f"Changed {metadata_rows_changed} metadata row(s). Image files were kept."
                + (f" {len(failed_messages)} failed." if failed_messages else '')
            )
        if failed_messages:
            QMessageBox.warning(self, 'Hide Selected', '\n'.join(failed_messages[:8]))
