from __future__ import annotations

import pandas as pd
from PySide6.QtWidgets import QApplication, QMessageBox

from ..services.data.edit_service import update_frame_controls_many
from ..services.data.model_deploy_service import run_model_deploy
from ..services.data.stats_service import calculate_basic_stats
from .data_page_support import DataPageSupportMixin


class DataPageDeployMixin:
    @staticmethod
    def _prediction_value(record: dict, key: str) -> float | None:
        value = record.get(key)
        if value is None and key == 'pred_throttle':
            value = record.get('pred_speed')
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _has_deployed_prediction(record: dict) -> bool:
        return DataPageDeployMixin._prediction_value(record, 'pred_steering') is not None and DataPageDeployMixin._prediction_value(record, 'pred_throttle') is not None

    def _set_record_prediction_fields(
        self,
        identity: tuple[str, str, str, str],
        *,
        pred_steering: float,
        pred_throttle: float,
        steering_diff: float,
        speed_diff: float,
    ) -> None:
        for field_name, value in {
            'pred_steering': pred_steering,
            'pred_throttle': pred_throttle,
            'steering_diff': steering_diff,
            'speed_diff': speed_diff,
        }.items():
            self._update_record_field_in_loaded_data(identity, field_name, float(value))

    @staticmethod
    def _identity_series_for_df(df: pd.DataFrame) -> pd.Series:
        if not isinstance(df, pd.DataFrame) or df.empty:
            return pd.Series([], dtype=object)

        def column_text(column: str) -> pd.Series:
            return DataPageSupportMixin._column_text(df, column)

        return pd.Series(
            list(zip(
                column_text('session'),
                column_text('frame_id'),
                column_text('ts'),
                column_text('abs_image'),
            )),
            index=df.index,
            dtype=object,
        )

    def _apply_prediction_map_to_dataframe(
        self,
        df: pd.DataFrame,
        prediction_map: dict[tuple[str, str, str, str], dict[str, float]],
    ) -> None:
        if not isinstance(df, pd.DataFrame) or df.empty or not prediction_map:
            return
        for field_name in ('pred_steering', 'pred_throttle', 'steering_diff', 'speed_diff'):
            if field_name not in df.columns:
                df[field_name] = pd.NA
        keys = self._identity_series_for_df(df)
        for index, identity in keys.items():
            values = prediction_map.get(identity)
            if not values:
                continue
            for field_name, value in values.items():
                df.at[index, field_name] = float(value)

    def _merge_deploy_predictions(self, deploy_rows: list[dict]) -> list[tuple[str, str, str, str]]:
        prediction_map: dict[tuple[str, str, str, str], dict[str, float]] = {}
        updated_identities: list[tuple[str, str, str, str]] = []
        seen: set[tuple[str, str, str, str]] = set()
        for row in deploy_rows:
            identity = self._record_identity(row)
            if not any(identity):
                continue
            pred_steering = float(row.get('pred_steering', 0.0) or 0.0)
            pred_throttle = float(row.get('pred_throttle', row.get('pred_speed', 0.0)) or 0.0)
            steering_diff = float(row.get('steering_diff', abs(pred_steering - float(row.get('target_steering', 0.0) or 0.0))) or 0.0)
            speed_diff = float(row.get('speed_diff', abs(pred_throttle - float(row.get('target_speed', 0.0) or 0.0))) or 0.0)
            prediction_map[identity] = {
                'pred_steering': pred_steering,
                'pred_throttle': pred_throttle,
                'steering_diff': steering_diff,
                'speed_diff': speed_diff,
            }
            if identity not in seen:
                updated_identities.append(identity)
                seen.add(identity)

        if prediction_map:
            for df_attr in ['dataset_df', 'filtered_df']:
                self._apply_prediction_map_to_dataframe(getattr(self.state, df_attr), prediction_map)
            self._apply_prediction_map_to_dataframe(self.current_preview_source_df, prediction_map)
        return updated_identities

    def deploy_model_to_visible_frames(self) -> None:
        self.preview_panel.stop_autoplay()
        visible_df = self.preview_panel.df.copy()
        if visible_df.empty:
            QMessageBox.information(self, 'Deploy Model', 'No visible frames. Load a session or loosen the filter first.')
            return

        requested_rows = len(visible_df)
        max_rows = self.model_deploy_panel.max_rows()
        target_rows = min(requested_rows, max_rows) if max_rows and max_rows > 0 else requested_rows
        self.main_window.set_status_message(f'Deploying model to {target_rows} visible frame(s)...')
        QApplication.processEvents()

        try:
            result = run_model_deploy(
                visible_df,
                self.state.train_config,
                self.state.model,
                model_source=self.model_deploy_panel.model_source(),
                model_path=self.model_deploy_panel.model_path(),
                batch_size=self.model_deploy_panel.batch_size(),
                max_rows=self.model_deploy_panel.max_rows(),
            )
        except Exception as exc:
            QMessageBox.warning(self, 'Deploy Model', f'Model deploy failed:\n{exc}')
            self.main_window.set_status_message('Model deploy failed.')
            return

        deploy_rows = list(result.get('deploy_rows', []))
        if not deploy_rows:
            QMessageBox.information(self, 'Deploy Model', 'No model outputs were produced.')
            self.main_window.set_status_message('No model outputs were produced.')
            return

        updated_identities = self._merge_deploy_predictions(deploy_rows)
        first_identity = updated_identities[0] if updated_identities else None
        self.apply_preview_filter(select_identity=first_identity)
        self.preview_panel.focus_table_for_keyboard()
        source = str(result.get('model_source', self.model_deploy_panel.model_source()) or self.model_deploy_panel.model_source())
        self.main_window.set_status_message(f'Deployed {len(updated_identities)} frame(s) using {source}.')

    def sort_by_steering_diff(self) -> None:
        if not self.preview_panel.sort_by_column_desc('steering_diff'):
            QMessageBox.information(self, 'Sort Diff', 'Deploy a model first to show steering differences.')
            return
        self.preview_panel.focus_table_for_keyboard()
        self.main_window.set_status_message('Sorted by largest steering difference.')

    def sort_by_speed_diff(self) -> None:
        if not self.preview_panel.sort_by_column_desc('speed_diff'):
            QMessageBox.information(self, 'Sort Diff', 'Deploy a model first to show speed differences.')
            return
        self.preview_panel.focus_table_for_keyboard()
        self.main_window.set_status_message('Sorted by largest speed difference.')

    def apply_deployed_outputs_to_selected(self) -> None:
        self.preview_panel.stop_autoplay()
        records = self.preview_panel.selected_records()
        eligible = [dict(record) for record in records if self._has_deployed_prediction(record)]
        if not eligible:
            QMessageBox.information(self, 'Apply AI Output', 'Select rows with deployed AI output first.')
            return
        if not self.model_deploy_panel.apply_confirmed():
            QMessageBox.information(self, 'Apply AI Output', 'Tick "Confirm Apply" before overwriting selected labels.')
            return

        confirm = QMessageBox.warning(
            self,
            'Apply AI Output?',
            f'This overwrites steering and speed labels for {len(eligible)} selected frame(s) using deployed AI output.\n\nContinue?',
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if confirm != QMessageBox.Yes:
            self.main_window.set_status_message('Apply AI output cancelled.')
            return

        update_records: list[dict] = []
        for record in eligible:
            pred_steering = float(self._prediction_value(record, 'pred_steering') or 0.0)
            pred_throttle = float(self._prediction_value(record, 'pred_throttle') or 0.0)
            updated = dict(record)
            updated['steering'] = pred_steering
            updated['throttle'] = pred_throttle
            update_records.append(updated)

        result = update_frame_controls_many(self.state.records_root_path, update_records)
        matched_key_set = {tuple(key) for key in result.get('matched_keys', [])}
        updated_records = [
            record for record in update_records
            if self._bulk_edit_target_key(record) in matched_key_set
        ]

        for record in updated_records:
            identity = self._record_identity(record)
            pred_steering = float(record.get('steering', 0.0) or 0.0)
            pred_throttle = float(record.get('throttle', 0.0) or 0.0)
            self._update_record_field_in_loaded_data(identity, 'steering', pred_steering)
            self._update_record_field_in_loaded_data(identity, 'throttle', pred_throttle)
            self._set_record_prediction_fields(
                identity,
                pred_steering=pred_steering,
                pred_throttle=pred_throttle,
                steering_diff=0.0,
                speed_diff=0.0,
            )

        self.stats_panel.set_stats(calculate_basic_stats(self.state.filtered_df))
        first_identity = self._record_identity(updated_records[0]) if updated_records else None
        self.apply_preview_filter(select_identity=first_identity)
        self.preview_panel.focus_table_for_keyboard()
        self.main_window.on_dataset_loaded()

        failed_messages = list(result.get('failed_messages', []))
        updated_count = int(result.get('updated_count', 0) or 0)
        rows_changed = int(result.get('metadata_rows_changed', 0) or 0)
        if updated_count:
            self.main_window.set_status_message(
                f'Applied AI output to {updated_count} selected frame(s); {rows_changed} metadata row(s) changed.'
                + (f' {len(failed_messages)} failed.' if failed_messages else '')
            )
        else:
            self.main_window.set_status_message('No AI output was applied.')
        if failed_messages:
            QMessageBox.warning(self, 'Apply AI Output', '\n'.join(failed_messages[:8]))
