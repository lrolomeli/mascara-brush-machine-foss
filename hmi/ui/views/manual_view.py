"""Vista de Modo Manual y Paso a Paso.

Rejilla de 10 toggles de valvula + indicador de paso actual.
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


class ManualView(QWidget):
    """Vista de control manual de valvulas y paso a paso."""

    valve_command = Signal(int, bool)
    step_next = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._valve_widgets: dict[int, ValveToggle] = {}
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

        valves_frame = SectionFrame("Valvulas Neumaticas")
        vl = valves_frame.content_layout

        grid = QGridLayout()
        grid.setSpacing(16)
        for i in range(1, 11):
            vt = ValveToggle(i)
            vt.toggled_signal.connect(self._on_valve_toggled)
            self._valve_widgets[i] = vt
            row = (i - 1) // 5
            col = (i - 1) % 5
            grid.addWidget(vt, row, col)
        vl.addLayout(grid)
        root.addWidget(valves_frame)

        step_frame = SectionFrame("Modo Paso a Paso")
        stl = step_frame.content_layout

        step_row = QHBoxLayout()
        self._step_display = ServoPositionDisplay("Paso Actual")
        step_row.addWidget(self._step_display)

        self._btn_step_next = IndustrialButton("PASO SIGUIENTE", "neutral", 200, 80)
        self._btn_step_next.clicked.connect(self.step_next.emit)
        step_row.addWidget(self._btn_step_next)
        step_row.addStretch()
        stl.addLayout(step_row)
        root.addWidget(step_frame)

        root.addStretch()

    def _on_valve_toggled(self, number: int, state: bool) -> None:
        self.valve_command.emit(number, state)

    def update_data(self, data: dict) -> None:
        for i in range(1, 11):
            tag = f"VALVE_{i}"
            if tag in data:
                self._valve_widgets[i].set_state(data[tag])

        self._step_display.set_value(data.get("STEP_NUMBER", 0))
