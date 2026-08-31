"""Vista de Depuracion de Salidas (Modo Manual).

Permite probar cada salida fisica una a una (forzado manual) y observar
en vivo la reaccion de los sensores. Complementa la vista Manual: esta es
especifica para el diagnostico individual por salida (activacion-manual-valvula.st).
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

from hmi.ui.widgets import IndustrialButton, SectionFrame, StatusLED, ValveToggle

# Salidas forzables una a una: (tag CMD, etiqueta)
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

# Sensores a mostrar en vivo
SENSORS = [
    ("S8", "Cerda"),
    ("S9", "Orientador"),
    ("S10", "Pinza Pos"),
    ("S11", "Rasurador"),
    ("S12", "Tijera Arr"),
    ("S13", "Cepillo"),
    ("S14", "Pinza Abajo"),
    ("S15", "Pinza Fuera"),
    ("S16", "Pinza Arriba"),
    ("S17", "Pinza Adent"),
    ("S18", "Cuchilla"),
    ("S19", "R. Alambre"),
    ("S20", "Lengueta"),
    ("S21", "Peine Atras"),
    ("S22", "Alambre Adv"),
    ("S23", "Presion"),
]

COLS = 5


class OutputsDebugView(QWidget):
    """Vista de depuracion individual de salidas y lectura de sensores."""

    output_command = Signal(str, bool)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._toggle_widgets: dict[str, ValveToggle] = {}
        self._sensor_leds: dict[str, StatusLED] = {}
        self._build_ui()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setSpacing(12)
        root.setContentsMargins(20, 20, 20, 20)

        title = QLabel("DEPURACIÓN DE SALIDAS (FORZADO MANUAL)")
        title.setFont(QFont("Segoe UI", 18, QFont.Weight.Bold))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("color: #e94560; padding: 8px;")
        root.addWidget(title)

        notice = QLabel("Activa MODE_MANUAL en el PLC para forzar salidas. Prueba una a una y observa los sensores.")
        notice.setAlignment(Qt.AlignmentFlag.AlignCenter)
        notice.setStyleSheet("color: #ff9800; font-size: 12px;")
        root.addWidget(notice)

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

        sens_frame = SectionFrame("Sensores en Vivo")
        sl = sens_frame.content_layout

        sens_row1 = QHBoxLayout()
        sens_row2 = QHBoxLayout()
        sens_row1.setSpacing(10)

        # Repartir sensores en dos filas
        half = (len(SENSORS) + 1) // 2
        for i, (tag, name) in enumerate(SENSORS):
            led = StatusLED(f"{tag} {name}", size=16)
            self._sensor_leds[tag] = led
            row = sens_row1 if i < half else sens_row2
            row.addWidget(led)

        sl.addLayout(sens_row1)
        sl.addLayout(sens_row2)
        root.addWidget(sens_frame)

        root.addStretch()

    def _on_toggled(self, index: int, state: bool) -> None:
        tag = DEBUG_OUTPUTS[index - 1][0]
        self.output_command.emit(tag, state)

    def update_data(self, data: dict) -> None:
        # Actualizar estado de los toggles desde el PLC (memoria CMD leida)
        for tag, _ in DEBUG_OUTPUTS:
            v = data.get(tag)
            if v is not None:
                self._toggle_widgets[tag].set_state(v)

        # Actualizar LEDs de sensores
        for tag, _ in SENSORS:
            led = self._sensor_leds.get(tag)
            if led and tag in data:
                led.set_on(bool(data[tag]))
