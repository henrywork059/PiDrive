from __future__ import annotations

import pandas as pd
from PySide6.QtWidgets import QMessageBox

from ..services.data.edit_service import update_frame_controls_batch, update_frame_controls_many
from ..services.data.filter_service import filter_preview_dataframe
from ..services.data.stats_service import calculate_basic_stats


class DataPageFilterEditMixin:
    def apply_preview_filter(self, select_identity: tuple[str, str, str, str] | None = None) -> None:
        filtered_preview = filter_preview_dataframe(
            self.current_preview_source_df,
            text=self.filter_panel.filter_text(),
            mode=self.filter_panel.selected_mode(),
            speed_range=self.filter_panel.speed_range() if self.filter_panel.speed_filter_enabled() else None,
            steering_range=self.filter_panel.steering_range() if self.filter_panel.steering_filter_enabled() else None,
        )
        self.preview_panel.set_dataframe(filtered_preview)
        if select_identity:
            self.preview_panel.select_record_identity(select_identity)
        self.plot_panel.set_dataframe(filtered_preview)
        if hasattr(self, 'model_deploy_panel'):
            prediction_count = 0
            if 'pred_steering' in filtered_preview.columns and ('pred_throttle' in filtered_preview.columns or 'pred_speed' in filtered_preview.columns):
                prediction_count = int(pd.to_numeric(filtered_preview.get('pred_steering'), errors='coerce').notna().sum())
            self.model_deploy_panel.set_prediction_count(prediction_count)
        if filtered_preview.empty:
            self.image_preview_panel.clear_preview()
        self.main_window.set_status_message(f'Displaying {len(filtered_preview)} preview frame(s).')

    def clear_preview_filter(self) -> None:
        self.filter_panel.reset()
        self.apply_preview_filter()

    def on_overlay_options_changed(self, options: dict[str, bool]) -> None:
        self.image_preview_panel.set_overlay_options(options)
        enabled = [name for name, active in options.items() if active]
        if enabled:
            self.main_window.set_status_message(f"Overlay enabled: {', '.join(enabled)}")
        else:
            self.main_window.set_status_message('Overlay cleared.')

    def on_preview_record_selected(self, record) -> None:
        selected_count = len(self.preview_panel.selected_records())
        self.bulk_edit_panel.set_selected_count(selected_count)
        if hasattr(self, 'model_deploy_panel'):
            self.model_deploy_panel.set_selected_count(selected_count)
        if not record:
            self.image_preview_panel.clear_preview()
            return
        self.image_preview_panel.set_record(record)

    def on_image_record_edited(self, record: dict | list[dict]) -> None:
        if not record:
            return
        if isinstance(record, list):
            self.on_image_records_edited(record)
            return
        self.on_image_records_edited([record])

    def on_image_records_edited(self, records: list[dict]) -> None:
        records = [dict(record) for record in records if record]
        if not records:
            return
        self.preview_panel.stop_autoplay()
        current_record = self.preview_panel.selected_record()
        current_identity = self._record_identity(current_record) if current_record else None

        result = update_frame_controls_many(self.state.records_root_path, records)
        matched_key_set = {tuple(key) for key in result.get('matched_keys', [])}
        updated_records = [
            record for record in records
            if self._bulk_edit_target_key(record) in matched_key_set
        ]
        if not updated_records:
            failed_messages = list(result.get('failed_messages', []))
            self.main_window.set_status_message(failed_messages[0] if failed_messages else 'No frame edit was applied.')
            return

        needs_filter_rebuild = False
        for edited_record in updated_records:
            identity = self._record_identity(edited_record)
            steering = float(edited_record.get('steering', 0.0) or 0.0)
            throttle = float(edited_record.get('throttle', 0.0) or 0.0)
            self._update_record_field_in_loaded_data(identity, 'steering', steering)
            self._update_record_field_in_loaded_data(identity, 'throttle', throttle)
            pred_steering = self._prediction_value(edited_record, 'pred_steering')
            pred_throttle = self._prediction_value(edited_record, 'pred_throttle')
            if pred_steering is not None and pred_throttle is not None:
                self._set_record_prediction_fields(
                    identity,
                    pred_steering=pred_steering,
                    pred_throttle=pred_throttle,
                    steering_diff=abs(pred_steering - steering),
                    speed_diff=abs(pred_throttle - throttle),
                )
                needs_filter_rebuild = True
            needs_filter_rebuild = needs_filter_rebuild or self._single_edit_needs_filter_rebuild(steering=steering, throttle=throttle)

        self.stats_panel.set_stats(calculate_basic_stats(self.state.filtered_df))
        if needs_filter_rebuild:
            self.apply_preview_filter(select_identity=current_identity)
        else:
            for edited_record in updated_records:
                identity = self._record_identity(edited_record)
                preserve_preview_selection = bool(current_identity and current_identity != identity)
                self.preview_panel.update_record_values(
                    identity,
                    {
                        'steering': float(edited_record.get('steering', 0.0) or 0.0),
                        'throttle': float(edited_record.get('throttle', 0.0) or 0.0),
                    },
                    preserve_selection=preserve_preview_selection,
                )
            self.schedule_plot_refresh_from_preview()

        failed_messages = list(result.get('failed_messages', []))
        updated_count = int(result.get('updated_count', 0) or 0)
        rows_changed = int(result.get('metadata_rows_changed', 0) or 0)
        self.main_window.set_status_message(
            f'Updated steering/speed for {updated_count} frame edit(s) with {rows_changed} metadata row(s) changed.'
            + (f' {len(failed_messages)} failed.' if failed_messages else '')
        )
        if updated_records and hasattr(self.main_window, 'on_data_records_edited'):
            self.main_window.on_data_records_edited(updated_records)
        if failed_messages:
            QMessageBox.warning(self, 'Edit Frame Data', '\n'.join(failed_messages[:8]))

    def _single_edit_needs_filter_rebuild(self, *, steering: float, throttle: float) -> bool:
        if self.filter_panel.speed_filter_enabled():
            min_speed, max_speed = self.filter_panel.speed_range()
            if throttle < min_speed or throttle > max_speed:
                return True
        if self.filter_panel.steering_filter_enabled():
            min_steering, max_steering = self.filter_panel.steering_range()
            if steering < min_steering or steering > max_steering:
                return True
        return False

    def select_all_preview_frames_for_bulk_edit(self) -> None:
        selected = self.preview_panel.select_all_records()
        count = len(self.preview_panel.selected_records())
        self.bulk_edit_panel.set_selected_count(count)
        self.main_window.set_status_message(
            f'Selected all {count} visible frame(s) for bulk edit.' if selected else 'No visible frame rows to select for bulk edit.'
        )

    def _update_record_field_in_loaded_data(self, identity: tuple[str, str, str, str], field_name: str, value: float) -> None:
        for df_attr in ['dataset_df', 'filtered_df']:
            df = getattr(self.state, df_attr)
            if isinstance(df, pd.DataFrame) and not df.empty:
                mask = self._record_mask(df, identity)
                if len(mask) == len(df) and mask.any():
                    df.loc[mask, field_name] = float(value)
        if not self.current_preview_source_df.empty:
            mask = self._record_mask(self.current_preview_source_df, identity)
            if len(mask) == len(self.current_preview_source_df) and mask.any():
                self.current_preview_source_df.loc[mask, field_name] = float(value)

    def _update_records_field_in_loaded_data(self, identities: list[tuple[str, str, str, str]], field_name: str, value: float) -> None:
        identity_set = set(identities)
        if not identity_set:
            return

        def update_df(df: pd.DataFrame) -> None:
            if not isinstance(df, pd.DataFrame) or df.empty:
                return

            def column_text(column: str) -> pd.Series:
                return self._column_text(df, column)

            row_keys = zip(
                column_text('session'),
                column_text('frame_id'),
                column_text('ts'),
                column_text('abs_image'),
            )
            mask = pd.Series([key in identity_set for key in row_keys], index=df.index, dtype=bool)
            if mask.any():
                df.loc[mask, field_name] = float(value)

        for df_attr in ['dataset_df', 'filtered_df']:
            update_df(getattr(self.state, df_attr))
        update_df(self.current_preview_source_df)

    def apply_bulk_steering_edit(self, steering: float) -> None:
        self._apply_bulk_control_edit(field_name='steering', field_label='steering', value=float(steering))

    def apply_bulk_speed_edit(self, speed: float) -> None:
        self._apply_bulk_control_edit(field_name='throttle', field_label='speed', value=float(speed))

    def _apply_bulk_control_edit(self, *, field_name: str, field_label: str, value: float) -> None:
        self.preview_panel.stop_autoplay()
        records = self.preview_panel.selected_records()
        if not records:
            QMessageBox.information(self, 'Bulk Edit', 'Select one or more rows first.')
            return
        if not self.bulk_edit_panel.bulk_edit_confirmed():
            QMessageBox.information(
                self,
                'Bulk Edit',
                'Tick "Confirm Overwrite" before bulk editing.',
            )
            return

        count = len(records)
        confirm = QMessageBox.warning(
            self,
            f'Confirm Bulk {field_label.title()} Edit',
            f'This will overwrite {field_label} for {count} selected frame(s) with {value:.3f}.\n\n'
            'The other control value stays unchanged. This cannot be undone in piTrainer. Continue?',
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if confirm != QMessageBox.Yes:
            self.main_window.set_status_message(f'Bulk {field_label} edit cancelled.')
            return

        result = update_frame_controls_batch(
            self.state.records_root_path,
            records,
            steering=value if field_name == 'steering' else 0.0,
            throttle=value if field_name == 'throttle' else 0.0,
            update_steering=(field_name == 'steering'),
            update_throttle=(field_name == 'throttle'),
        )

        matched_key_set = {tuple(key) for key in result.get('matched_keys', [])}
        updated_identities = [
            self._record_identity(record)
            for record in records
            if self._bulk_edit_target_key(record) in matched_key_set
        ]
        if updated_identities:
            self._update_records_field_in_loaded_data(updated_identities, field_name, value)

        failed_messages = list(result.get('failed_messages', []))
        edited_records = [
            record for record in records
            if self._bulk_edit_target_key(record) in matched_key_set
        ]
        self.stats_panel.set_stats(calculate_basic_stats(self.state.filtered_df))
        first_identity = updated_identities[0] if updated_identities else None
        self.apply_preview_filter(select_identity=first_identity)
        if edited_records and hasattr(self.main_window, 'on_data_records_edited'):
            self.main_window.on_data_records_edited(edited_records)

        updated_count = int(result.get('updated_count', 0))
        rows_changed = int(result.get('metadata_rows_changed', 0))
        if updated_count:
            self.main_window.set_status_message(
                f'Updated {field_label} for {updated_count} selected frame(s) with {rows_changed} metadata row(s) changed.'
                + (f' {len(failed_messages)} failed.' if failed_messages else '')
            )
        if failed_messages:
            QMessageBox.warning(self, f'Bulk {field_label.title()} Edit', '\n'.join(failed_messages[:8]))
