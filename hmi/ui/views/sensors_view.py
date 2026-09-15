"""Vista de Sensores en Vivo.

Muestra todos los sensores de la maquina con su estado en tiempo real.
Grid de 2 columnas con LED + nombre completo del sensor.
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QVBoxLayout,
    QWidget,
)

from hmi.ui.widgets import SimpleLED

SENSORS = [
    ("S8", "FALTA CERDA"),
    ("S9", "ORIENTADOR LISTO"),
    ("S10", "CAMINO LIBRE RASURADORA"),
    ("S11", "RASURADORA BAJANDO"),
    ("S12", "TIJERA ARRIBA LISTO"),
    ("S13", "CEPILLO CORTADO FIN DE CICLO"),
    ("S14", "PINZA ABAJO"),
    ("S15", "CENTRADO DE PINZA"),
    ("S16", "PINZA ARRIBA"),
    ("S17", "PINZA ADELANTE"),
    ("S18", "ENTRA CIZALLA"),
    ("S19", "REGRESA CUCHILLA DOBLADORA"),
    ("S20", "ALAMBRE EN POS. FINAL LENGÜETA"),
    ("S21", "PEINE CARGADO DE NYLON"),
    ("S22", "ALAMBRE EN POS. INICIAL LENGÜETA"),
    ("S23", "PRESION NEUMATICA DE MAQUINA"),
]


class SensorsView(QWidget):
    """Vista de sensores en vivo con grid de 2 columnas."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._sensor_leds: dict[str, SimpleLED] = {}
        self._build_ui()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setSpacing(20)
        root.setContentsMargins(24, 24, 24, 24)

        title = QLabel("SENSORES EN VIVO")
        title.setFont(QFont("Segoe UI", 24, QFont.Weight.Bold))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("color: #e94560; background: transparent; padding: 10px;")
        root.addWidget(title)

        grid = QGridLayout()
        grid.setSpacing(15)
        grid.setAlignment(Qt.AlignmentFlag.AlignCenter)

        for idx, (tag, name) in enumerate(SENSORS):
            row = idx // 2
            col = idx % 2

            row_container = QHBoxLayout()
            row_container.setSpacing(10)
            row_container.setContentsMargins(5, 5, 5, 5)

            led = SimpleLED(14)
            led.set_on(False)
            row_container.addWidget(led)

            card = QWidget()
            card.setStyleSheet("""
                QWidget {
                    background-color: #1a1a2e;
                    border: 1px solid #333333;
                    border-radius: 8px;
                }
            """)

            card_layout = QHBoxLayout(card)
            card_layout.setContentsMargins(12, 8, 12, 8)

            name_label = QLabel(f"{tag} - {name}")
            name_label.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
            name_label.setStyleSheet("color: #cccccc; background: transparent;")
            card_layout.addWidget(name_label)

            row_container.addWidget(card)

            self._sensor_leds[tag] = led

            if col == 0:
                grid.addLayout(row_container, row, 0)
            else:
                grid.addLayout(row_container, row, 1)

        root.addLayout(grid)
        root.addStretch()

    def update_data(self, data: dict) -> None:
        for tag, led in self._sensor_leds.items():
            value = data.get(tag, False)
            led.set_on(bool(value))
