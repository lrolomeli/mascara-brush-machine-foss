"""Vista de Produccion (Automatico) - Simplificada sin controles."""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QVBoxLayout,
    QWidget,
)

from hmi.ui.widgets import StatusLED


class AutoView(QWidget):
    """Vista de produccion simplificada (controles en sidebar derecho)."""

    cmd_start = Signal(bool)
    cmd_cycle_stop = Signal(bool)
    cmd_reset = Signal(bool)
    cmd_continuous = Signal(bool)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet("background-color: #0f0f23;")
        self._build_ui()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setSpacing(20)
        root.setContentsMargins(24, 24, 24, 24)

        self._build_header(root)
        self._build_status_section(root)
        root.addStretch()

    def _build_header(self, root: QVBoxLayout) -> None:
        header_layout = QHBoxLayout()

        title = QLabel("SELECCION")
        title.setFont(QFont("Segoe UI", 28, QFont.Weight.Bold))
        title.setStyleSheet("color: #e94560; background: transparent;")
        header_layout.addWidget(title)

        header_layout.addStretch()

        self._led_connected = StatusLED("PLC", size=22,
                                         color_on="#00e676", color_off="#ff1744")
        header_layout.addWidget(self._led_connected)

        root.addLayout(header_layout)

    def _build_status_section(self, root: QVBoxLayout) -> None:
        status_layout = QHBoxLayout()
        status_layout.setSpacing(30)

        auto_frame = self._make_status_card("AUTOMATICO", "#00e676")
        self._led_auto = auto_frame.findChild(QLabel, "status_value")
        status_layout.addWidget(auto_frame)

        manual_frame = self._make_status_card("MANUAL", "#ff9800")
        self._led_manual = manual_frame.findChild(QLabel, "status_value")
        status_layout.addWidget(manual_frame)

        paso_frame = self._make_status_card("PASO A PASO", "#2196f3")
        self._led_step = paso_frame.findChild(QLabel, "status_value")
        status_layout.addWidget(paso_frame)

        debug_frame = self._make_status_card("DEBUG", "#9c27b0")
        self._led_debug = debug_frame.findChild(QLabel, "status_value")
        status_layout.addWidget(debug_frame)

        status_layout.addStretch()

        root.addLayout(status_layout)

    def _make_status_card(self, text: str, color: str) -> QWidget:
        frame = QWidget()
        frame.setStyleSheet(f"""
            QWidget {{
                background-color: #16213e;
                border: 2px solid {color};
                border-radius: 8px;
                min-width: 120px;
            }}
        """)

        layout = QVBoxLayout(frame)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setSpacing(4)

        title = QLabel(text)
        title.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet(f"color: {color}; background: transparent;")
        layout.addWidget(title)

        status_value = QLabel("OFF")
        status_value.setObjectName("status_value")
        status_value.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        status_value.setAlignment(Qt.AlignmentFlag.AlignCenter)
        status_value.setStyleSheet("color: #555555; background: transparent;")
        layout.addWidget(status_value)

        return frame

    def update_data(self, data: dict) -> None:
        state = data.get("MACHINE_STATE", 0)

        self._led_auto.setStyleSheet(f"""
            QLabel {{
                color: {'#00e676' if state == 1 else '#555555'};
                background: transparent;
                font-weight: bold;
                font-size: 14px;
            }}
        """)
        self._led_manual.setStyleSheet(f"""
            QLabel {{
                color: {'#ff9800' if state == 2 else '#555555'};
                background: transparent;
                font-weight: bold;
                font-size: 14px;
            }}
        """)
        self._led_step.setStyleSheet(f"""
            QLabel {{
                color: {'#2196f3' if state == 3 else '#555555'};
                background: transparent;
                font-weight: bold;
                font-size: 14px;
            }}
        """)
        self._led_debug.setStyleSheet(f"""
            QLabel {{
                color: {'#9c27b0' if state == 4 else '#555555'};
                background: transparent;
                font-weight: bold;
                font-size: 14px;
            }}
        """)

    def set_connected(self, connected: bool) -> None:
        self._led_connected.set_on(connected)
