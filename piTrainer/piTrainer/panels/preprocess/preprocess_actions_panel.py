from __future__ import annotations

from PySide6.QtWidgets import QGroupBox, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget

from ...ui.layout_widgets import CollapsibleSection, style_next_step_button


class PreprocessActionsPanel(QGroupBox):
    def __init__(
        self,
        preview_callback,
        apply_callback,
        reset_callback,
        sync_callback,
        save_settings_callback,
        save_data_callback,
        defaults_callback,
        auto_callback,
    ) -> None:
        super().__init__('Actions')

        guide = QLabel(
            'After loading sessions, click Auto Preprocess. Defaults add one horizontal flip copy per frame.'
        )
        guide.setWordWrap(True)
        guide.setProperty('role', 'hint')

        self.auto_btn = QPushButton('Auto Preprocess')
        style_next_step_button(self.auto_btn, 'Auto Preprocess')
        self.auto_btn.setToolTip('Load defaults, add horizontal flips, and make the active training dataset.')
        self.auto_btn.clicked.connect(auto_callback)

        # Keep the historical attribute used by the page banner, but point it to
        # the new one-click main action.
        self.apply_btn = self.auto_btn

        default_btn = QPushButton('Recommended Defaults')
        default_btn.setProperty('role', 'amber')
        default_btn.setToolTip('Reset to safe defaults and preview the result.')
        default_btn.clicked.connect(defaults_callback)

        preview_btn = QPushButton('Preview Recipe')
        preview_btn.setProperty('role', 'amber')
        preview_btn.setToolTip('Check row counts before applying custom settings.')
        preview_btn.clicked.connect(preview_callback)

        self.confirm_btn = QPushButton('Apply Recipe')
        self.confirm_btn.setProperty('role', 'primary')
        self.confirm_btn.setToolTip('Apply the current recipe to the active training dataset.')
        self.confirm_btn.clicked.connect(apply_callback)

        reset_btn = QPushButton('Reset')
        reset_btn.setProperty('role', 'secondary')
        reset_btn.clicked.connect(reset_callback)

        save_settings_btn = QPushButton('Save Settings')
        save_settings_btn.setProperty('role', 'secondary')
        save_settings_btn.clicked.connect(save_settings_callback)

        save_data_btn = QPushButton('Save Data')
        save_data_btn.setProperty('role', 'secondary')
        save_data_btn.clicked.connect(save_data_callback)

        sync_btn = QPushButton('Sync Image Size')
        sync_btn.setProperty('role', 'amber')
        sync_btn.clicked.connect(sync_callback)

        setup_row = QHBoxLayout()
        setup_row.addWidget(default_btn)
        setup_row.addWidget(preview_btn)

        maintenance = QWidget()
        maintenance_layout = QVBoxLayout(maintenance)
        maintenance_layout.setContentsMargins(0, 0, 0, 0)
        maintenance_layout.setSpacing(6)
        maintenance_layout.addWidget(reset_btn)
        maintenance_layout.addWidget(save_settings_btn)
        maintenance_layout.addWidget(save_data_btn)
        maintenance_layout.addWidget(sync_btn)

        layout = QVBoxLayout(self)
        layout.addWidget(guide)
        layout.addLayout(setup_row)
        layout.addWidget(self.auto_btn)
        layout.addWidget(self.confirm_btn)
        layout.addWidget(CollapsibleSection('Save + tools', maintenance, expanded=False))
        layout.addStretch(1)
