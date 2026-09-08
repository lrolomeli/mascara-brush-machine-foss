"""Vista de Actuadores (Modo Manual).

Permite probar cada salida fisica una a una (forzado manual).
Requiere modo MANUAL para funcionar.
"""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QGridLayout,
    QLabel,
    QVBoxLayout,
    QWidget,
)

from hmi.ui.widgets import SectionFrame, ValveToggle

DEBUG_OUTPUTS = [
    ("CMD_Y1", "Y1 Orientadores"),
    ("CMD_Y3", "Y3 Chucks"),
    ("CMD_Y5", "Y5 Sale Pinza"),
    ("CMD_Y6", "Y6 Sube Pinza"),
    ("CMD_Y7", "Y7 Sube Tijera"),
    ("CMD_Y8", "Y8 Cierra Tijera"),
    ("CMD_Y9", "Y9 Pinza"),
    ("CMD_Y10", "Y10 Abre Pinza"),
    ("CMD_Y11", "Y11 Orienta"),
    ("CMD_Y12", "Y12 Cachador"),
    ("CMD_Y14", "Y14 Baja Pinza"),
    ("CMD_Y15", "Y15 P/Dobladora"),
    ("CMD_Y16", "Y16 Lengueta"),
    ("CMD_Y17", "Y17 Cizalla"),
    ("CMD_Y18", "Y18 Empuja Alambre"),
    ("CMD_Y24", "Y24 Cachador"),
    ("CMD_M1", "M1 Retorcido"),
    ("CMD_M2", "M2 Rasurado"),
    ("CMD_M3", "M3 Aspirado"),
]

COLS = 5


class OutputsDebugView(QWidget):
    """Vista de actuadores con forzado manual."""

    output_command = Signal(str, bool)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._toggle_widgets: dict[str, ValveToggle] = {}
        self._build_ui()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setSpacing(12)
        root.setContentsMargins(20, 20, 20, 20)

        title = QLabel("ACTUADORES (FORZADO MANUAL)")
        title.setFont(QFont("Segoe UI", 18, QFont.Weight.Bold))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("color: #e94560; padding: 8px;")
        root.addWidget(title)

        self._warning_label = QLabel("Cambia a modo MANUAL para activar actuadores")
        self._warning_label.setFont(QFont("Segoe UI", 13, QFont.Weight.Bold))
        self._warning_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._warning_label.setStyleSheet("""
            QLabel {
                color: #ff9800;
                background-color: #3d2e00;
                border: 2px solid #ff9800;
                border-radius: 8px;
                padding: 15px;
            }
        """)
        root.addWidget(self._warning_label)

        out_frame = SectionFrame("Salidas")
        outl = out_frame.content_layout

        grid = QGridLayout()
        grid.setSpacing(10)
        for idx, (tag, label) in enumerate(DEBUG_OUTPUTS):
            vt = ValveToggle(idx + 1)
            vt.set_button_text(tag)
            vt.set_label_text(label)
            vt.toggled_signal.connect(self._on_toggled)
            self._toggle_widgets[tag] = vt
            row = idx // COLS
            col = idx % COLS
            grid.addWidget(vt, row, col)
        outl.addLayout(grid)
        root.addWidget(out_frame)

        root.addStretch()

    def _on_toggled(self, index: int, state: bool) -> None:
        tag = DEBUG_OUTPUTS[index - 1][0]
        self.output_command.emit(tag, state)

    def _set_toggles_enabled(self, enabled: bool) -> None:
        for vt in self._toggle_widgets.values():
            vt.setEnabled(enabled)

    def set_mode(self, is_manual: bool) -> None:
        if is_manual:
            self._warning_label.hide()
            self._set_toggles_enabled(True)
        else:
            self._warning_label.show()
            self._set_toggles_enabled(False)

    def update_data(self, data: dict) -> None:
        is_manual = data.get("MODE_MANUAL", False)
        self.set_mode(is_manual)

        for tag, _ in DEBUG_OUTPUTS:
            v = data.get(tag)
            if v is not None:
                self._toggle_widgets[tag].set_state(v)
