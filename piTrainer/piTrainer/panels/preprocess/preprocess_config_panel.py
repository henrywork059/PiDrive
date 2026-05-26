from __future__ import annotations

from PySide6.QtWidgets import (
    QCheckBox,
    QDoubleSpinBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from ...app_state import AppState
from ...ui.layout_widgets import CollapsibleSection, standardize_form_layout


class PreprocessConfigPanel(QGroupBox):
    def __init__(self, state: AppState) -> None:
        super().__init__('Preprocess Recipe')
        self.state = state

        help_label = QLabel(
            'Recommended defaults now add one horizontal flip copy for every active frame. Open the advanced sections only when you intentionally need turning boost or mild camera-variant augmentation.'
        )
        help_label.setWordWrap(True)
        help_label.setProperty('role', 'muted')

        self.turn_boost = QCheckBox('Boost turning examples')
        self.turn_threshold = QDoubleSpinBox()
        self.turn_threshold.setRange(0.01, 1.0)
        self.turn_threshold.setDecimals(3)
        self.turn_threshold.setSingleStep(0.01)
        self.turn_threshold.setValue(0.18)
        self.turn_copies = QSpinBox()
        self.turn_copies.setRange(1, 8)
        self.turn_copies.setValue(1)

        self.mirror_enabled = QCheckBox('Add one horizontal flip copy for every row')
        self.mirror_enabled.setChecked(True)
        self.color_variants = QSpinBox()
        self.color_variants.setRange(0, 4)
        self.color_variants.setValue(0)
        self.color_variants.setToolTip('Adds mild exposure / white-balance variants only.')

        self.image_h = QSpinBox()
        self.image_h.setRange(32, 1080)
        self.image_w = QSpinBox()
        self.image_w.setRange(32, 1920)

        self.turn_row = self._make_range_row(self.turn_threshold, self.turn_copies)

        layout = QVBoxLayout(self)
        layout.setSpacing(8)
        layout.addWidget(help_label)
        layout.addWidget(CollapsibleSection('Output Image Size', self._size_section(), expanded=True))
        layout.addWidget(CollapsibleSection('Advanced: Turning Boost', self._turning_section(), expanded=False))
        layout.addWidget(CollapsibleSection('Default augmentation: Horizontal Flip + Advanced Color', self._variant_section(), expanded=False))
        layout.addStretch(1)

        self.turn_boost.toggled.connect(self._update_enabled_state)
        self.sync_from_state()
        self._update_enabled_state()

    def _section_form(self) -> tuple[QWidget, QFormLayout]:
        widget = QWidget()
        form = QFormLayout(widget)
        form.setContentsMargins(0, 0, 0, 0)
        standardize_form_layout(form)
        return widget, form

    def _turning_section(self) -> QWidget:
        widget, form = self._section_form()
        form.addRow(self.turn_boost)
        form.addRow('Turn threshold / extra copies', self.turn_row)
        return widget

    def _variant_section(self) -> QWidget:
        widget, form = self._section_form()
        form.addRow(self.mirror_enabled)
        form.addRow('Mild exposure / WB variants', self.color_variants)
        return widget

    def _size_section(self) -> QWidget:
        widget, form = self._section_form()
        form.addRow('Output image height', self.image_h)
        form.addRow('Output image width', self.image_w)
        return widget

    def _make_range_row(self, left, right) -> QWidget:
        container = QWidget()
        row = QHBoxLayout(container)
        row.setContentsMargins(0, 0, 0, 0)
        row.addWidget(left)
        row.addWidget(right)
        return container

    def _update_enabled_state(self) -> None:
        turn_enabled = self.turn_boost.isChecked()
        self.turn_threshold.setEnabled(turn_enabled)
        self.turn_copies.setEnabled(turn_enabled)

    def sync_from_state(self) -> None:
        self.image_h.setValue(self.state.train_config.img_h)
        self.image_w.setValue(self.state.train_config.img_w)

    def reset_to_defaults(self) -> None:
        self.turn_boost.setChecked(False)
        self.turn_threshold.setValue(0.18)
        self.turn_copies.setValue(1)
        self.mirror_enabled.setChecked(True)
        self.color_variants.setValue(0)
        self.image_h.setValue(self.state.train_config.img_h)
        self.image_w.setValue(self.state.train_config.img_w)
        self._update_enabled_state()

    def load_from_recipe(self, recipe: dict[str, object]) -> None:
        if not recipe:
            return
        self.turn_boost.setChecked(bool(recipe.get('turn_boost', False)))
        self.turn_threshold.setValue(float(recipe.get('turn_threshold', 0.18) or 0.18))
        self.turn_copies.setValue(max(1, int(recipe.get('turn_copies', 1) or 1)))
        self.mirror_enabled.setChecked(bool(recipe.get('mirror_enabled', False)))
        self.color_variants.setValue(max(0, int(recipe.get('color_variants', 0) or 0)))
        self.image_h.setValue(max(32, int(recipe.get('image_height', self.state.train_config.img_h) or self.state.train_config.img_h)))
        self.image_w.setValue(max(32, int(recipe.get('image_width', self.state.train_config.img_w) or self.state.train_config.img_w)))
        self._update_enabled_state()

    def recipe(self) -> dict[str, object]:
        return {
            'turn_boost': self.turn_boost.isChecked(),
            'turn_threshold': self.turn_threshold.value(),
            'turn_copies': self.turn_copies.value(),
            'mirror_enabled': self.mirror_enabled.isChecked(),
            'color_variants': self.color_variants.value(),
            'image_height': self.image_h.value(),
            'image_width': self.image_w.value(),
        }
