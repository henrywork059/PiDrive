from __future__ import annotations

import pandas as pd
from PySide6.QtWidgets import QGroupBox, QLabel, QVBoxLayout


class PreprocessSummaryPanel(QGroupBox):
    def __init__(self) -> None:
        super().__init__('Source Summary')
        self.info_label = QLabel('Load sessions on the Data tab to start preprocessing.')
        self.info_label.setWordWrap(True)
        self.preview_label = QLabel('No preview calculated yet.')
        self.preview_label.setWordWrap(True)
        self.preview_label.setProperty('role', 'muted')

        layout = QVBoxLayout(self)
        layout.addWidget(self.info_label)
        layout.addWidget(self.preview_label)
        layout.addStretch(1)

    def set_summary(self, dataset_df: pd.DataFrame, filtered_df: pd.DataFrame, selected_sessions: list[str], train_config) -> None:
        dataset_rows = len(dataset_df)
        filtered_rows = len(filtered_df)
        dataset_sessions = len(set(dataset_df.get('session', []))) if not dataset_df.empty else 0
        filtered_sessions = len(set(filtered_df.get('session', []))) if not filtered_df.empty else 0
        selected = len(selected_sessions)

        if dataset_df.empty:
            self.info_label.setText(
                'No dataset loaded yet. Use the Data tab to choose a record root and load one or more sessions.'
            )
            return

        steering = pd.to_numeric(filtered_df.get('steering', pd.Series(dtype=float)), errors='coerce')
        throttle = pd.to_numeric(filtered_df.get('throttle', pd.Series(dtype=float)), errors='coerce')
        steering_text = 'n/a'
        throttle_text = 'n/a'
        if not filtered_df.empty and steering.notna().any():
            steering_text = f"{float(steering.min()):.3f} to {float(steering.max()):.3f}"
        if not filtered_df.empty and throttle.notna().any():
            throttle_text = f"{float(throttle.min()):.3f} to {float(throttle.max()):.3f}"

        synthetic_rows = 0
        if not filtered_df.empty and 'aug_variant' in filtered_df.columns:
            synthetic_rows = int(filtered_df['aug_variant'].fillna('original').astype(str).ne('original').sum())

        self.info_label.setText(
            'Selected sessions: {selected} | Loaded rows: {dataset_rows} across {dataset_sessions} session(s)\n'
            'Active training rows: {filtered_rows} across {filtered_sessions} session(s) | Synthetic rows: {synthetic_rows}\n'
            'Active steering range: {steering_text} | Active speed range: {throttle_text}\n'
            'Current train image size: {img_w}x{img_h} | Model: {model_size} | Seed: {seed}'.format(
                selected=selected,
                dataset_rows=dataset_rows,
                dataset_sessions=dataset_sessions,
                filtered_rows=filtered_rows,
                filtered_sessions=filtered_sessions,
                synthetic_rows=synthetic_rows,
                steering_text=steering_text,
                throttle_text=throttle_text,
                img_w=train_config.img_w,
                img_h=train_config.img_h,
                model_size=getattr(train_config, 'model_size', 'Small CNN'),
                seed=getattr(train_config, 'seed', 42),
            )
        )

    def set_preview_counts(self, summary: dict[str, float | int | str]) -> None:
        self.preview_label.setText(
            'Preview -> rows: {rows_after}/{rows_before} | dedup removed: {duplicate_rows_removed} | '
            'stride kept: {rows_after_stride}/{rows_after_dedup} | '
            'straight kept: {straight_rows_after_balance}/{straight_rows_before_balance} | '
            'turn boost added: {turn_rows_added} | generated: {generated_rows} '
            '(mirror {mirror_rows_added}, color {color_rows_added}) | '
            'steering: {steering_min:.3f} to {steering_max:.3f} | speed: {throttle_min:.3f} to {throttle_max:.3f}'.format(
                **summary
            )
        )
