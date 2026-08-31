"""Vista de Modo Manual y Paso a Paso.

Rejilla de ~20 toggles de salidas fisicas reales (Y*/M*) que fuerzan las
memorias CMD_* del PLC + indicador de paso actual y avance por pasos.
"""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QVBoxLayout,
    QWidget,
)

from hmi.ui.widgets import IndustrialButton, SectionFrame, ServoPositionDisplay, ValveToggle

# Salidas forzables manualmente: (tag CMD, etiqueta)
MANUAL_OUTPUTS = [
    ("CMD_Y1", "Y1 Oriental"),
    ("CMD_Y3", "Y3 Chucks"),
    ("CMD_Y6", "Y6 Cabezal"),
    ("CMD_Y7", "Y7 Tijera"),
    ("CMD_Y8", "Y8 Cierra Tij"),
    ("CMD_Y9", "Y9 Pinza"),
    ("CMD_Y10", "Y10 Pinza"),
    ("CMD_Y11", "Y11 Centra"),
    ("CMD_Y12", "Y12 Pinza"),
    ("CMD_Y14", "Y14 Rasador"),
    ("CMD_Y15", "Y15 P/Doblad"),
    ("CMD_Y16", "Y16 Lengueta"),
    ("CMD_Y17", "Y17 Cizalla"),
    ("CMD_Y18", "Y18 Alambre"),
    ("CMD_Y24", "Y24 Cachador"),
    ("CMD_M1", "M1 Retorcido"),
    ("CMD_M2", "M2 Rasurado"),
    ("CMD_M3", "M3 Aspirado"),
]

COLS = 6


class ManualView(QWidget):
    """Vista de control manual de salidas y paso a paso."""

    output_command = Signal(str, bool)
    step_next = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._toggle_widgets: dict[str, ValveToggle] = {}
        self._build_ui()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setSpacing(16)
        root.setContentsMargins(20, 20, 20, 20)

        title = QLabel("CONTROL MANUAL / PASO A PASO")
        title.setFont(QFont("Segoe UI", 20, QFont.Weight.Bold))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("color: #e94560; padding: 10px;")
        root.addWidget(title)

        out_frame = SectionFrame("Forzado Manual de Salidas (Modo Manual)")
        outl = out_frame.content_layout

        grid = QGridLayout()
        grid.setSpacing(12)
        for idx, (tag, label) in enumerate(MANUAL_OUTPUTS):
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

        step_frame = SectionFrame("Modo Paso a Paso")
        stl = step_frame.content_layout

        step_row = QHBoxLayout()
        self._step_alambre = ServoPositionDisplay("Paso Alambre")
        step_row.addWidget(self._step_alambre)
        self._step_pinza = ServoPositionDisplay("Paso Pinza")
        step_row.addWidget(self._step_pinza)

        self._btn_step_next = IndustrialButton("PASO SIGUIENTE", "neutral", 200, 80)
        self._btn_step_next.clicked.connect(self.step_next.emit)
        step_row.addWidget(self._btn_step_next)
        step_row.addStretch()
        stl.addLayout(step_row)
        root.addWidget(step_frame)

        root.addStretch()

    def _on_toggled(self, index: int, state: bool) -> None:
        tag = MANUAL_OUTPUTS[index - 1][0]
        self.output_command.emit(tag, state)

    def update_data(self, data: dict) -> None:
        # Salidas forzadas: leer estado de la memoria CMD (o salida fisica si existe)
        for tag, _ in MANUAL_OUTPUTS:
            v = data.get(tag)
            if v is not None:
                self._toggle_widgets[tag].set_state(v)

        self._step_alambre.set_value(data.get("Paso_Alambre", 0))
        self._step_pinza.set_value(data.get("Paso_Pinza", 0))
