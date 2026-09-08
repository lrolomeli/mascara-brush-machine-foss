"""Vista de Depuracion por Pasos.

Muestra el estado de los pasos de la secuencia y permite avanzar paso a paso.
"""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QVBoxLayout,
    QWidget,
)

from hmi.ui.widgets import IndustrialButton, SectionFrame, ServoPositionDisplay


class ManualView(QWidget):
    """Vista de depuracion paso a paso."""

    step_next = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._build_ui()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setSpacing(16)
        root.setContentsMargins(20, 20, 20, 20)

        title = QLabel("DEPURACION POR PASOS")
        title.setFont(QFont("Segoe UI", 20, QFont.Weight.Bold))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("color: #e94560; padding: 10px;")
        root.addWidget(title)

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

    def update_data(self, data: dict) -> None:
        self._step_alambre.set_value(data.get("Paso_Alambre", 0))
        self._step_pinza.set_value(data.get("Paso_Pinza", 0))
