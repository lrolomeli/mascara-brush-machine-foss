"""Vista de Produccion (Automatico).

Botones Start, Cycle Stop, Pause, E-Stop + LEDs de sensores y estado.
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

from hmi.ui.widgets import IndustrialButton, SectionFrame, StatusLED


class AutoView(QWidget):
    """Vista de produccion automatica."""

    cmd_start = Signal(bool)
    cmd_cycle_stop = Signal(bool)
    cmd_pause = Signal(bool)
    cmd_estop = Signal(bool)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._build_ui()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setSpacing(16)
        root.setContentsMargins(20, 20, 20, 20)

        title = QLabel("PRODUCCION AUTOMATICA")
        title.setFont(QFont("Segoe UI", 20, QFont.Weight.Bold))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("color: #e94560; padding: 10px;")
        root.addWidget(title)

        controls_frame = SectionFrame("Controles de Ciclo")
        cl = controls_frame.content_layout
        cl.setSpacing(12)

        btn_row = QHBoxLayout()
        self._btn_start = IndustrialButton("INICIO", "start", 180, 90)
        self._btn_start.toggled.connect(self.cmd_start.emit)
        btn_row.addWidget(self._btn_start)

        self._btn_pause = IndustrialButton("PAUSA", "pause", 180, 90)
        self._btn_pause.toggled.connect(self.cmd_pause.emit)
        btn_row.addWidget(self._btn_pause)

        self._btn_cycle_stop = IndustrialButton("PARO CICLO", "cycle_stop", 180, 90)
        self._btn_cycle_stop.toggled.connect(self.cmd_cycle_stop.emit)
        btn_row.addWidget(self._btn_cycle_stop)

        self._btn_estop = IndustrialButton("E-STOP", "emergency", 220, 100)
        self._btn_estop._setup_emergency()
        self._btn_estop.toggled.connect(self.cmd_estop.emit)
        btn_row.addWidget(self._btn_estop)
        cl.addLayout(btn_row)
        root.addWidget(controls_frame)

        status_frame = SectionFrame("Estado de Maquina")
        sl = status_frame.content_layout

        state_row = QHBoxLayout()
        state_row.setSpacing(20)

        self._led_auto = StatusLED("Auto", size=18)
        self._led_manual = StatusLED("Manual", size=18)
        self._led_step = StatusLED("Paso", size=18)
        self._led_debug = StatusLED("Debug", size=18)
        self._led_connected = StatusLED("PLC", size=18,
                                         color_on="#2196f3", color_off="#f44336")

        state_row.addWidget(self._led_auto)
        state_row.addWidget(self._led_manual)
        state_row.addWidget(self._led_step)
        state_row.addWidget(self._led_debug)
        state_row.addWidget(self._led_connected)
        sl.addLayout(state_row)

        sensor_row = QHBoxLayout()
        sensor_row.setSpacing(30)
        s1_frame = SectionFrame("Sensores")
        s1l = s1_frame.content_layout
        self._led_s1 = StatusLED("Sensor 1", size=20)
        s1l.addWidget(self._led_s1, alignment=Qt.AlignmentFlag.AlignCenter)
        self._led_s2 = StatusLED("Sensor 2", size=20)
        s1l.addWidget(self._led_s2, alignment=Qt.AlignmentFlag.AlignCenter)
        sensor_row.addWidget(s1_frame)
        sl.addLayout(sensor_row)

        root.addWidget(status_frame)
        root.addStretch()

    def update_data(self, data: dict) -> None:
        self._led_s1.set_on(data.get("SENSOR_1", False))
        self._led_s2.set_on(data.get("SENSOR_2", False))

        state = data.get("MACHINE_STATE", 0)
        self._led_auto.set_on(state == 1)
        self._led_manual.set_on(state == 2)
        self._led_step.set_on(state == 3)
        self._led_debug.set_on(state == 4)

    def set_connected(self, connected: bool) -> None:
        self._led_connected.set_on(connected)
