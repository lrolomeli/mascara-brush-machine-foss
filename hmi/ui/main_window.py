"""Ventana Principal del HMI Industrial.

QTabWidget fullscreen 1920x1080 con tema oscuro de alto contraste.
Integra todas las vistas y el worker de comunicaciones.
"""

from __future__ import annotations

import logging
from pathlib import Path

from PySide6.QtCore import Qt, Slot
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QMainWindow,
    QMessageBox,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from hmi.comms.modbus_worker import ModbusWorker
from hmi.ui.views.auto_view import AutoView
from hmi.ui.views.debug_view import DebugView
from hmi.ui.views.manual_view import ManualView
from hmi.ui.views.outputs_debug_view import OutputsDebugView
from hmi.ui.views.servo_view import ServoView
from hmi.ui.views.settings_view import SettingsView

logger = logging.getLogger(__name__)

CONFIG_DIR = Path(__file__).resolve().parents[2] / "config"


class MainWindow(QMainWindow):
    """Ventana principal HMI."""

    def __init__(self, worker: ModbusWorker):
        super().__init__()
        self._worker = worker
        self.setWindowTitle("HMI Industrial - Maquina Ma1")
        self.setMinimumSize(1920, 1080)
        self._build_ui()
        self._connect_signals()

    def _build_ui(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)

        self._tabs = QTabWidget()
        self._tabs.setFont(QFont("Segoe UI", 13, QFont.Weight.Bold))
        self._tabs.setStyleSheet("""
            QTabWidget::pane {
                border: none;
                background-color: #0f0f23;
            }
            QTabBar::tab {
                background-color: #1a1a2e;
                color: #aaaaaa;
                padding: 12px 24px;
                margin-right: 2px;
                border-top-left-radius: 6px;
                border-top-right-radius: 6px;
                min-width: 160px;
                min-height: 30px;
            }
            QTabBar::tab:selected {
                background-color: #16213e;
                color: #e94560;
                font-weight: bold;
            }
            QTabBar::tab:hover {
                background-color: #1f1f3a;
            }
        """)

        self._auto_view = AutoView()
        self._manual_view = ManualView()
        self._servo_view = ServoView()

        tag_names = list(self._worker.adapter.profile.tags.keys())
        self._debug_view = DebugView(tag_names)
        self._outputs_debug_view = OutputsDebugView()
        self._settings_view = SettingsView()

        self._tabs.addTab(self._auto_view, "Produccion")
        self._tabs.addTab(self._manual_view, "Manual / Paso")
        self._tabs.addTab(self._servo_view, "Servo")
        self._tabs.addTab(self._outputs_debug_view, "Depar. Salidas")
        self._tabs.addTab(self._debug_view, "Depuracion")
        self._tabs.addTab(self._settings_view, "Configuracion")

        root.addWidget(self._tabs)

    def _connect_signals(self) -> None:
        self._worker.data_ready.connect(self._on_data)
        self._worker.connection_status.connect(self._on_connection)
        self._worker.error_occurred.connect(self._on_error)

        self._auto_view.cmd_start.connect(
            lambda v: self._worker.enqueue_write("CMD_START", v))
        self._auto_view.cmd_cycle_stop.connect(
            lambda v: self._worker.enqueue_write("CMD_CYCLE_STOP", v))
        self._auto_view.cmd_pause.connect(
            lambda v: self._worker.enqueue_write("CMD_PAUSE", v))
        self._auto_view.cmd_estop.connect(
            lambda v: self._worker.enqueue_write("CMD_ESTOP", v))

        self._manual_view.output_command.connect(
            lambda tag, v: self._worker.enqueue_write(tag, v))
        self._manual_view.step_next.connect(self._on_step_next)

        self._outputs_debug_view.output_command.connect(
            lambda tag, v: self._worker.enqueue_write(tag, v))

        self._servo_view.jog_fwd.connect(
            lambda v: self._worker.enqueue_write("SERVO_JOG_FWD", v))
        self._servo_view.jog_rev.connect(
            lambda v: self._worker.enqueue_write("SERVO_JOG_REV", v))
        self._servo_view.speed_changed.connect(
            lambda v: self._worker.enqueue_write("SERVO_SPEED", v))
        self._servo_view.position_changed.connect(
            lambda v: self._worker.enqueue_write("SERVO_POS_TARGET", v))

        self._debug_view.read_tag_request.connect(self._on_debug_read)
        self._debug_view.write_tag_request.connect(self._on_debug_write)

        self._settings_view.profile_changed.connect(self._on_profile_changed)
        self._settings_view.connection_test.connect(self._on_connection_test)

    @Slot(dict)
    def _on_data(self, data: dict) -> None:
        self._auto_view.update_data(data)
        self._manual_view.update_data(data)
        self._outputs_debug_view.update_data(data)
        self._servo_view.update_data(data)

    @Slot(bool)
    def _on_connection(self, connected: bool) -> None:
        self._auto_view.set_connected(connected)
        self._settings_view.set_connection_status(connected)

    @Slot(str)
    def _on_error(self, msg: str) -> None:
        self._debug_view.log_error(msg)

    def _on_debug_read(self, tag: str) -> None:
        try:
            value = self._worker.adapter.read_tag(tag)
            self._debug_view.log_response(tag, value)
        except Exception as e:
            self._debug_view.log_error(str(e))

    def _on_debug_write(self, tag: str, value: str) -> None:
        parsed = self._parse_value(value)
        self._worker.enqueue_write(tag, parsed)

    @Slot()
    def _on_step_next(self) -> None:
        # Pulso en BTN_STEP para avanzar un paso en modo paso a paso
        self._worker.enqueue_write("BTN_STEP", True)
        self._worker.enqueue_write("BTN_STEP", False)

    @staticmethod
    def _parse_value(raw: str) -> bool | int:
        low = raw.strip().lower()
        if low in ("true", "1", "on"):
            return True
        if low in ("false", "0", "off"):
            return False
        try:
            return int(raw)
        except ValueError:
            return 0

    @Slot(str)
    def _on_profile_changed(self, profile_path: str) -> None:
        self._worker.load_new_profile(profile_path)
        tag_names = list(self._worker.adapter.profile.tags.keys())
        self._debug_view.set_tag_names(tag_names)
        logger.info("Perfil cambiado a: %s", self._worker.adapter.profile.name)

    @Slot(str, int)
    def _on_connection_test(self, ip: str, port: int) -> None:
        self._worker.adapter.set_connection(ip, port)
        ok = self._worker.adapter.connect()
        self._worker.connection_status.emit(ok)
        if ok:
            QMessageBox.information(self, "Conexion", f"Conectado a {ip}:{port}")
            self._worker.adapter.disconnect()
        else:
            QMessageBox.warning(self, "Conexion", f"No se pudo conectar a {ip}:{port}")
