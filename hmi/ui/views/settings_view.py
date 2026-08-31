"""Vista de Configuracion.

Selector de perfil de PLC, campos IP/Puerto, boton test de conexion.
"""

from __future__ import annotations

import json
from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QVBoxLayout,
    QWidget,
)

from hmi.ui.widgets import IndustrialButton, SectionFrame, StatusLED


CONFIG_DIR = Path(__file__).resolve().parents[3] / "config"
PROFILES_DIR = CONFIG_DIR / "plc_profiles"


class SettingsView(QWidget):
    """Vista de configuracion de PLC y red."""

    profile_changed = Signal(str)
    connection_test = Signal(str, int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._build_ui()
        self._discover_profiles()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setSpacing(16)
        root.setContentsMargins(20, 20, 20, 20)

        title = QLabel("CONFIGURACION")
        title.setFont(QFont("Segoe UI", 20, QFont.Weight.Bold))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("color: #e94560; padding: 10px;")
        root.addWidget(title)

        plc_frame = SectionFrame("Seleccion de PLC")
        pl = plc_frame.content_layout

        profile_row = QHBoxLayout()
        prof_lbl = QLabel("Perfil de PLC:")
        prof_lbl.setStyleSheet("color: #cccccc; font-size: 14px;")
        profile_row.addWidget(prof_lbl)
        self._profile_combo = QComboBox()
        self._profile_combo.setMinimumWidth(300)
        self._profile_combo.setStyleSheet("""
            QComboBox {
                background-color: #0d1117;
                color: #ffffff;
                border: 1px solid #555555;
                border-radius: 4px;
                padding: 8px 12px;
                font-size: 14px;
            }
            QComboBox::drop-down { border: none; }
            QComboBox QAbstractItemView {
                background-color: #1a1a2e;
                color: #ffffff;
                selection-background-color: #e94560;
            }
        """)
        self._profile_combo.currentIndexChanged.connect(self._on_profile_changed)
        profile_row.addWidget(self._profile_combo, stretch=1)
        pl.addLayout(profile_row)

        self._profile_desc = QLabel("")
        self._profile_desc.setStyleSheet("color: #888888; font-size: 12px; border: none;")
        pl.addWidget(self._profile_desc)
        root.addWidget(plc_frame)

        net_frame = SectionFrame("Red PLC")
        nl = net_frame.content_layout

        ip_row = QHBoxLayout()
        ip_lbl = QLabel("IP:")
        ip_lbl.setStyleSheet("color: #cccccc; font-size: 14px;")
        ip_row.addWidget(ip_lbl)
        self._ip_input = QLineEdit("192.168.1.10")
        self._ip_input.setStyleSheet("""
            QLineEdit {
                background-color: #0d1117;
                color: #ffffff;
                border: 1px solid #555555;
                border-radius: 4px;
                padding: 8px 12px;
                font-size: 14px;
            }
        """)
        ip_row.addWidget(self._ip_input, stretch=1)
        nl.addLayout(ip_row)

        port_row = QHBoxLayout()
        port_lbl = QLabel("Puerto:")
        port_lbl.setStyleSheet("color: #cccccc; font-size: 14px;")
        port_row.addWidget(port_lbl)
        self._port_input = QLineEdit("502")
        self._port_input.setMaximumWidth(120)
        self._port_input.setStyleSheet("""
            QLineEdit {
                background-color: #0d1117;
                color: #ffffff;
                border: 1px solid #555555;
                border-radius: 4px;
                padding: 8px 12px;
                font-size: 14px;
            }
        """)
        port_row.addWidget(self._port_input)
        port_row.addStretch()
        nl.addLayout(port_row)

        test_row = QHBoxLayout()
        self._btn_test = IndustrialButton("TEST CONEXION", "neutral", 200, 60)
        self._btn_test.clicked.connect(self._on_test)
        test_row.addWidget(self._btn_test)

        self._led_status = StatusLED("Estado", size=18,
                                      color_on="#00e676", color_off="#f44336")
        test_row.addWidget(self._led_status)
        test_row.addStretch()
        nl.addLayout(test_row)

        self._status_label = QLabel("Desconectado")
        self._status_label.setStyleSheet("color: #f44336; font-size: 14px; border: none;")
        nl.addWidget(self._status_label)
        root.addWidget(net_frame)

        root.addStretch()

    def _discover_profiles(self) -> None:
        self._profiles = {}
        if PROFILES_DIR.exists():
            for f in sorted(PROFILES_DIR.glob("*.json")):
                with open(f, "r", encoding="utf-8") as fh:
                    data = json.load(fh)
                name = data.get("name", f.stem)
                self._profiles[name] = str(f)
                self._profile_combo.addItem(name)

    def _on_profile_changed(self, index: int) -> None:
        name = self._profile_combo.currentText()
        if name in self._profiles:
            with open(self._profiles[name], "r", encoding="utf-8") as f:
                data = json.load(f)
            self._profile_desc.setText(data.get("description", ""))
            self.profile_changed.emit(self._profiles[name])

    def _on_test(self) -> None:
        ip = self._ip_input.text().strip()
        try:
            port = int(self._port_input.text().strip())
        except ValueError:
            port = 502
        self.connection_test.emit(ip, port)

    def set_connection_status(self, connected: bool) -> None:
        self._led_status.set_on(connected)
        if connected:
            self._status_label.setText("Conectado")
            self._status_label.setStyleSheet("color: #00e676; font-size: 14px; border: none;")
        else:
            self._status_label.setText("Desconectado")
            self._status_label.setStyleSheet("color: #f44336; font-size: 14px; border: none;")

    def get_current_profile_path(self) -> str:
        name = self._profile_combo.currentText()
        return self._profiles.get(name, "")

    def get_connection_params(self) -> tuple[str, int]:
        ip = self._ip_input.text().strip() or "192.168.1.10"
        try:
            port = int(self._port_input.text().strip())
        except ValueError:
            port = 502
        return ip, port
