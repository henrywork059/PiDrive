from __future__ import annotations

import pandas as pd
from PySide6.QtWidgets import QMessageBox

from ..services.data.merge_service import merge_sessions
from ..services.data.record_loader_service import build_filtered_dataframe, load_records_dataframe
from ..services.data.session_service import list_sessions
from ..services.data.stats_service import calculate_basic_stats


class DataPageSessionMixin:
    @staticmethod
    def _normalise_session_selection(sessions: list[str] | tuple[str, ...] | set[str]) -> list[str]:
        """Return non-empty session names with duplicates removed, preserving order."""
        result: list[str] = []
        seen: set[str] = set()
        for session in sessions:
            name = str(session or '').strip()
            if not name or name in seen:
                continue
            result.append(name)
            seen.add(name)
        return result

    def _current_session_selection_for_focus(self) -> list[str]:
        """Return the user's current Session Source selection without narrowing it.

        Validation's **Edit in Data** action should focus one frame in Data, but it
        must not turn a multi-session selection into a single selected session.
        Prefer the live Session Source checkboxes, then fall back to the app
        state, and finally to the sessions already loaded in the Data dataframe.
        """
        selected = self._normalise_session_selection(self.session_source_panel.selected_sessions())
        if selected:
            return selected

        selected = self._normalise_session_selection(self.state.selected_sessions)
        if selected:
            return selected

        if not self.state.dataset_df.empty and 'session' in self.state.dataset_df.columns:
            return self._normalise_session_selection(
                self.state.dataset_df['session'].fillna('').astype(str).tolist()
            )
        return []

    def _session_selection_with_focus_target(self, target_session: str) -> list[str]:
        """Keep the existing session selection and add the focus target if needed."""
        sessions = self._current_session_selection_for_focus()
        target = str(target_session or '').strip()
        if target and target not in sessions:
            sessions.append(target)
        return sessions

    def refresh_sessions(self) -> None:
        self.state.available_sessions = list_sessions(self.state.records_root_path)
        self.session_source_panel.set_sessions(self.state.available_sessions)
        if self.state.available_sessions == ['.'] and not self.session_source_panel.selected_sessions():
            self.session_source_panel.set_selected_sessions(['.'])
            self.state.selected_sessions = ['.']
        sync_working_folder = getattr(self.main_window, 'sync_working_folder_from_loaded_sessions', None)
        if callable(sync_working_folder):
            sync_working_folder(show_status=False)
        self.main_window.set_status_message(
            f"Found {len(self.state.available_sessions)} session(s) under {self.state.records_root_path}."
        )

    def load_selected_sessions(self) -> None:
        selected = self.session_source_panel.selected_sessions()
        self.state.selected_sessions = selected
        self._load_sessions(selected)

    def on_session_selection_changed(self, selected: list[str]) -> None:
        """Keep save/export defaults aligned as soon as session selection changes."""
        self.state.selected_sessions = list(selected)
        sync_working_folder = getattr(self.main_window, 'sync_working_folder_from_loaded_sessions', None)
        if callable(sync_working_folder):
            sync_working_folder(show_status=False)

    def _load_sessions(self, selected: list[str]) -> None:
        df = load_records_dataframe(self.state.records_root_path, selected)
        filtered = build_filtered_dataframe(df, self.state.train_config.only_manual)
        self.state.dataset_df = df
        self.state.filtered_df = filtered
        self.state.train_df = filtered.iloc[0:0].copy()
        self.state.val_df = filtered.iloc[0:0].copy()
        self.state.model = None
        self.state.history = {}
        self.current_preview_source_df = self._review_dataframe(filtered)

        sync_working_folder = getattr(self.main_window, 'sync_working_folder_from_loaded_sessions', None)
        if callable(sync_working_folder):
            sync_working_folder()

        stats = calculate_basic_stats(filtered)
        self.stats_panel.set_stats(stats)
        self.apply_preview_filter()
        self.main_window.on_dataset_loaded()

    def focus_record(self, record: dict | None) -> bool:
        if not record:
            return False
        target_record = self._focus_target_record(dict(record))
        session = str(target_record.get('session', '')).strip()
        if not session:
            return False

        current_sessions = set(self.state.dataset_df.get('session', pd.Series(dtype=str)).astype(str).tolist()) if not self.state.dataset_df.empty else set()
        need_reload = session not in current_sessions
        if need_reload:
            sessions_to_load = self._session_selection_with_focus_target(session)
            self.session_source_panel.set_selected_sessions(sessions_to_load)
            # Re-apply the full load list after the checkbox update. If a
            # session is not visible in the current scan list for any reason,
            # set_selected_sessions() can only check visible rows, but the
            # reload still needs the complete list including the focus target.
            self.state.selected_sessions = sessions_to_load
            self._load_sessions(sessions_to_load)
            if self.last_focus_redirected_to_source:
                reloaded_target = self._find_source_record_for_synthetic(record)
                if reloaded_target:
                    target_record = reloaded_target
        else:
            # Keep the user's multi-session checkbox selection intact. Do not
            # call set_selected_sessions() here, because that would clear any
            # selected sessions except the one frame being edited.
            preserved_selection = self._current_session_selection_for_focus()
            if preserved_selection:
                self.state.selected_sessions = preserved_selection

        identity = self._record_identity(target_record)
        self.filter_panel.reset()
        self.apply_preview_filter(select_identity=identity)
        found = self.preview_panel.select_record_identity(identity)
        if found:
            self.on_preview_record_selected(self.preview_panel.selected_record())
        return bool(found)

    def merge_selected_sessions(self) -> None:
        selected = self.session_source_panel.selected_sessions()
        if len(selected) < 2:
            QMessageBox.information(self, 'Merge Sessions', 'Select at least 2 sessions first.')
            return

        merged_name = self.merge_sessions_panel.merged_session_name()
        if not merged_name:
            merged_name = f'merged_{selected[0]}_{selected[-1]}'
            self.merge_sessions_panel.set_merged_session_name(merged_name)

        confirm = QMessageBox.question(
            self,
            'Merge Sessions',
            'Create one merged session from the selected sessions?'
            + f"\n\nSource sessions: {', '.join(selected)}"
            + f"\nTarget session: {merged_name}",
        )
        if confirm != QMessageBox.Yes:
            return

        ok, message, details = merge_sessions(self.state.records_root_path, selected, merged_name)
        if not ok:
            QMessageBox.warning(self, 'Merge Sessions', message)
            self.main_window.set_status_message(message)
            return

        target_session = str(details.get('target_session', merged_name))
        self.state.selected_sessions = selected.copy()
        self.refresh_sessions()
        if self.merge_sessions_panel.should_load_after_merge():
            self.state.selected_sessions = [target_session]
            self.session_source_panel.set_selected_sessions([target_session])
            self._load_sessions([target_session])
        else:
            self.session_source_panel.set_selected_sessions(selected)
            self.main_window.set_status_message(message)

        QMessageBox.information(self, 'Merge Sessions', message)
