"""Ventana Principal del HMI Industrial.

QMainWindow con sidebar vertical izquierdo (navegacion) y derecho (controles).
"""

from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path

from PySide6.QtCore import Qt, Signal, Slot
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QCheckBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from hmi.comms.modbus_worker import ModbusWorker
from hmi.ui.widgets import ModeToggle
from hmi.ui.views.manual_view import ManualView
from hmi.ui.views.outputs_debug_view import OutputsDebugView
from hmi.ui.views.servo_view import ServoView
from hmi.ui.views.sensors_view import SensorsView
from hmi.ui.views.settings_view import SettingsView

logger = logging.getLogger(__name__)

CONFIG_DIR = Path(__file__).resolve().parents[2] / "config"

TAB_NAMES = [
    ("Sensores", "sensors"),
    ("Actuadores", "outputs"),
    ("Depuracion por pasos", "manual"),
    ("Servo", "servo"),
    ("Configuracion", "settings"),
]


class AlarmBar(QFrame):
    """Barra de alarmas en la parte superior central."""

    alarms_cleared = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._has_alarms = False
        self._build_ui()

    def _build_ui(self) -> None:
        self.setFixedHeight(50)
        self.setStyleSheet("""
            QFrame {
                background-color: #1a0a0a;
                border: 2px solid #ff1744;
                border-radius: 6px;
            }
        """)

        layout = QHBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(15, 5, 10, 5)

        self._title = QLabel("ALARMAS")
        self._title.setStyleSheet("color: #ff1744; font-weight: bold; font-size: 13px;")
        layout.addWidget(self._title)

        self._separator = QLabel("|")
        self._separator.setStyleSheet("color: #555555;")
        self._separator.setVisible(False)
        layout.addWidget(self._separator)

        self._scroll_area = QScrollArea()
        self._scroll_area.setWidgetResizable(True)
        self._scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        self._scroll_area.setStyleSheet("background: transparent; border: none;")
        self._scroll_area.setVisible(False)

        self._alarm_container = QWidget()
        self._alarm_container_layout = QHBoxLayout(self._alarm_container)
        self._alarm_container_layout.setSpacing(15)
        self._alarm_container_layout.addStretch()

        self._scroll_area.setWidget(self._alarm_container)
        layout.addWidget(self._scroll_area)

        layout.addStretch()

        self._btn_clear = QPushButton("Limpiar")
        self._btn_clear.setFixedWidth(80)
        self._btn_clear.setCursor(Qt.CursorShape.PointingHandCursor)
        self._btn_clear.setStyleSheet("""
            QPushButton {
                background-color: #333333;
                color: #ffffff;
                border: 1px solid #ff1744;
                border-radius: 4px;
                padding: 4px 8px;
                font-size: 11px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #ff1744;
            }
        """)
        self._btn_clear.clicked.connect(self._on_clear_alarms)
        layout.addWidget(self._btn_clear)

        self.setVisible(False)

    def _on_clear_alarms(self) -> None:
        self.alarms_cleared.emit()
        self._has_alarms = False
        self.setVisible(False)

    def update_alarms(self, alarms: list[dict]) -> None:
        while self._alarm_container_layout.count():
            item = self._alarm_container_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        self._has_alarms = len(alarms) > 0
        self._separator.setVisible(len(alarms) > 0)
        self._scroll_area.setVisible(len(alarms) > 0)

        for alarm in alarms:
            label = QLabel(f"⚠ {alarm['name']}  {alarm['timestamp']}")
            label.setStyleSheet("color: #ff1744; font-size: 12px; font-weight: bold;")
            self._alarm_container_layout.insertWidget(
                self._alarm_container_layout.count() - 1, label
            )

        self.setVisible(len(alarms) > 0)

    def setVisible(self, visible: bool) -> None:
        if visible and not self._has_alarms:
            visible = False
        super().setVisible(visible)


class MainWindow(QMainWindow):
    """Ventana principal HMI con sidebar de navegacion y controles."""

    def __init__(self, worker: ModbusWorker):
        super().__init__()
        self._worker = worker
        self._current_view = "auto"
        self._is_manual_mode = True
        self.setWindowTitle("HMI Industrial - Maquina Ma1")
        self.setMinimumSize(1920, 1080)
        self._build_ui()
        self._connect_signals()
        self._update_outputs_mode()

    def _build_ui(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)

        main_layout = QHBoxLayout(central)
        main_layout.setSpacing(0)
        main_layout.setContentsMargins(0, 0, 0, 0)

        sidebar = self._build_sidebar()
        main_layout.addWidget(sidebar)

        center_area = QVBoxLayout()
        center_area.setSpacing(10)
        center_area.setContentsMargins(10, 10, 10, 10)

        self._alarm_bar = AlarmBar()
        self._alarm_bar.setMaximumWidth(1200)
        center_area.addWidget(self._alarm_bar)

        self._stacked = QStackedWidget()
        self._stacked.setStyleSheet("""
            QStackedWidget {
                background-color: #0f0f23;
            }
        """)

        self._manual_view = ManualView()
        self._servo_view = ServoView()
        self._sensors_view = SensorsView()
        self._outputs_debug_view = OutputsDebugView()
        self._settings_view = SettingsView()

        self._stacked.addWidget(self._sensors_view)
        self._stacked.addWidget(self._outputs_debug_view)
        self._stacked.addWidget(self._manual_view)
        self._stacked.addWidget(self._servo_view)
        self._stacked.addWidget(self._settings_view)

        center_area.addWidget(self._stacked, 1)

        main_layout.addLayout(center_area, 1)

        controls_panel = self._build_controls_panel()
        main_layout.addWidget(controls_panel)

    def _build_sidebar(self) -> QWidget:
        sidebar = QWidget()
        sidebar.setFixedWidth(200)
        sidebar.setStyleSheet("""
            QWidget {
                background-color: #16213e;
                border-right: 1px solid #333333;
            }
        """)

        layout = QVBoxLayout(sidebar)
        layout.setSpacing(0)
        layout.setContentsMargins(0, 0, 0, 0)

        title = QLabel("MA1")
        title.setFont(QFont("Segoe UI", 24, QFont.Weight.Bold))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("""
            color: #e94560;
            background-color: #0f0f23;
            padding: 20px;
            border-bottom: 2px solid #333333;
        """)
        layout.addWidget(title)

        self._nav_buttons = {}
        for label_text, view_key in TAB_NAMES:
            btn = QPushButton(label_text)
            btn.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setCheckable(True)
            btn.setFlat(True)
            btn.setObjectName(view_key)
            btn.toggled.connect(lambda checked, v=view_key: self._on_nav_toggled(checked, v))
            self._nav_buttons[view_key] = btn
            layout.addWidget(btn)

        layout.addStretch()

        layout.addWidget(self._make_separator())

        self._btn_connection = QPushButton("DESCONECTADO")
        self._btn_connection.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        self._btn_connection.setCursor(Qt.CursorShape.ArrowCursor)
        self._btn_connection.setFlat(True)
        self._btn_connection.setStyleSheet("""
            QPushButton {
                color: #ff1744;
                background-color: transparent;
                border: none;
                padding: 12px;
                text-align: left;
            }
        """)
        layout.addWidget(self._btn_connection)

        return sidebar

    def _build_controls_panel(self) -> QWidget:
        panel = QWidget()
        panel.setFixedWidth(220)
        panel.setStyleSheet("""
            QWidget {
                background-color: #16213e;
                border-left: 1px solid #333333;
            }
        """)

        layout = QVBoxLayout(panel)
        layout.setSpacing(20)
        layout.setContentsMargins(15, 20, 15, 20)

        title = QLabel("CONTROLES")
        title.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("""
            color: #e94560;
            background-color: transparent;
            padding: 10px;
        """)
        layout.addWidget(title)

        layout.addWidget(self._make_separator())

        self._mode_toggle = ModeToggle()
        self._mode_toggle.mode_changed.connect(self._on_mode_changed)
        layout.addWidget(self._mode_toggle)

        self._btn_reset = self._create_rectangular_button("RESET", "#2d2d2d", "#404040", "#606060")
        self._btn_reset.setMinimumHeight(100)
        self._btn_reset.clicked.connect(lambda: self._worker.enqueue_write("CMD_PAUSE", True))
        layout.addWidget(self._btn_reset)

        self._btn_stop = self._create_rectangular_button("PARO", "#b71c1c", "#c62828", "#ef5350")
        self._btn_stop.setMinimumHeight(100)
        self._btn_stop.clicked.connect(lambda: self._worker.enqueue_write("CMD_CYCLE_STOP", True))
        layout.addWidget(self._btn_stop)

        self._btn_start = self._create_rectangular_button("INICIO", "#1b5e20", "#2e7d32", "#4caf50")
        self._btn_start.setMinimumHeight(100)
        self._btn_start.clicked.connect(lambda: self._worker.enqueue_write("CMD_START", True))
        self._btn_start.hide()
        layout.addWidget(self._btn_start)

        layout.addSpacing(25)

        self._toggle_continuous = QCheckBox("CONTINUO")
        self._toggle_continuous.setFont(QFont("Segoe UI", 13, QFont.Weight.Bold))
        self._toggle_continuous.setCursor(Qt.CursorShape.PointingHandCursor)
        self._toggle_continuous.setStyleSheet("""
            QCheckBox {
                color: #aaaaaa;
                background-color: transparent;
                spacing: 10px;
                padding: 8px;
            }
            QCheckBox::indicator {
                width: 24px;
                height: 24px;
                border: 2px solid #555555;
                border-radius: 12px;
                background-color: #1a1a1a;
            }
            QCheckBox::indicator:checked {
                background-color: #4caf50;
                border-color: #4caf50;
            }
            QCheckBox:checked {
                color: #4caf50;
            }
        """)
        self._toggle_continuous.stateChanged.connect(
            lambda s: self._worker.enqueue_write("S4_CONTINUOUS", s == Qt.CheckState.Checked.value)
        )
        layout.addWidget(self._toggle_continuous)
        self._toggle_continuous.hide()

        self._check_debug = QCheckBox("DEBUG")
        self._check_debug.setFont(QFont("Segoe UI", 13, QFont.Weight.Bold))
        self._check_debug.setCursor(Qt.CursorShape.PointingHandCursor)
        self._check_debug.setStyleSheet("""
            QCheckBox {
                color: #aaaaaa;
                background-color: transparent;
                spacing: 10px;
                padding: 8px;
            }
            QCheckBox::indicator {
                width: 24px;
                height: 24px;
                border: 2px solid #555555;
                border-radius: 12px;
                background-color: #1a1a1a;
            }
            QCheckBox::indicator:checked {
                background-color: #ff9800;
                border-color: #ff9800;
            }
            QCheckBox:checked {
                color: #ff9800;
            }
        """)
        self._check_debug.stateChanged.connect(self._on_debug_changed)
        layout.addWidget(self._check_debug)

        layout.addStretch()

        return panel

    def _create_alarm_card(self, name: str, normal_text: str, alarm_text: str,
                           sensor_icon: str, normal_color: str, alarm_color: str) -> QWidget:
        card = QWidget()
        card.setMinimumHeight(100)
        card.setStyleSheet("""
            QWidget {
                background-color: #1a1a2e;
                border: 2px solid #333333;
                border-radius: 10px;
            }
        """)

        layout = QVBoxLayout(card)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setSpacing(6)
        layout.setContentsMargins(12, 12, 12, 12)

        top_row = QHBoxLayout()
        top_row.setSpacing(10)

        icon = AlarmIcon(sensor_icon, 36)
        top_row.addWidget(icon)

        name_label = QLabel(name)
        name_label.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        name_label.setStyleSheet("color: #cccccc; background: transparent;")
        top_row.addWidget(name_label)

        layout.addLayout(top_row)

        status_label = QLabel(normal_text)
        status_label.setFont(QFont("Segoe UI", 13, QFont.Weight.Bold))
        status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        status_label.setStyleSheet(f"color: {normal_color}; background: transparent; font-weight: bold;")
        layout.addWidget(status_label)

        setattr(self, f"_alarm_icon_{name.lower()}", icon)
        setattr(self, f"_alarm_label_{name.lower()}", status_label)
        setattr(self, f"_alarm_normal_text_{name.lower()}", normal_text)
        setattr(self, f"_alarm_alarm_text_{name.lower()}", alarm_text)
        setattr(self, f"_alarm_normal_color_{name.lower()}", normal_color)
        setattr(self, f"_alarm_alarm_color_{name.lower()}", alarm_color)

        return card

    def _create_rectangular_button(self, label: str, dark: str, mid: str, light: str) -> QPushButton:
        btn = QPushButton(label)
        btn.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setMinimumHeight(80)
        btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {mid};
                color: #ffffff;
                border: 2px solid {light};
                border-radius: 8px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: {light};
                border-color: #ffffff;
            }}
            QPushButton:pressed {{
                background-color: {dark};
            }}
        """)
        return btn

    def _make_separator(self) -> QWidget:
        sep = QWidget()
        sep.setStyleSheet("background-color: #333333;")
        sep.setFixedHeight(1)
        return sep

    def _on_nav_toggled(self, checked: bool, view_key: str) -> None:
        if checked:
            self._current_view = view_key
            for key, btn in self._nav_buttons.items():
                btn.setChecked(key == view_key)
            view_index = list(self._nav_buttons.keys()).index(view_key)
            self._stacked.setCurrentIndex(view_index)
            self._update_nav_styles()

    def _update_nav_styles(self) -> None:
        for key, btn in self._nav_buttons.items():
            if key == self._current_view:
                btn.setStyleSheet("""
                    QPushButton {
                        color: #e94560;
                        background-color: #1a1a2e;
                        border-left: 4px solid #e94560;
                        padding: 12px 12px 12px 8px;
                        text-align: left;
                    }
                """)
            else:
                btn.setStyleSheet("""
                    QPushButton {
                        color: #aaaaaa;
                        background-color: transparent;
                        border: none;
                        padding: 12px;
                        text-align: left;
                    }
                    QPushButton:hover {
                        background-color: #1a1a2e;
                        color: #ffffff;
                    }
                """)

    def _connect_signals(self) -> None:
        self._worker.data_ready.connect(self._on_data)
        self._worker.connection_status.connect(self._on_connection)

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

        self._settings_view.profile_changed.connect(self._on_profile_changed)
        self._settings_view.connection_test.connect(self._on_connection_test)

        self._nav_buttons["sensors"].setChecked(True)
        self._update_nav_styles()

    @Slot(dict)
    def _on_data(self, data: dict) -> None:
        self._manual_view.update_data(data)
        self._outputs_debug_view.update_data(data)
        self._servo_view.update_data(data)
        self._sensors_view.update_data(data)

        h3_alarm = data.get("H3", False)
        h8_alarm = data.get("H8", False)

        alarms = []
        if h3_alarm:
            alarms.append({
                'name': 'Falta Nylon Alarma',
                'timestamp': datetime.now().strftime("%H:%M:%S")
            })
        if h8_alarm:
            alarms.append({
                'name': 'Alarma Presion Baja',
                'timestamp': datetime.now().strftime("%H:%M:%S")
            })
        self._alarm_bar.update_alarms(alarms)

        if self._worker._adapter._connected:
            is_manual_from_plc = data.get("MODE_MANUAL", False)
            if is_manual_from_plc != self._is_manual_mode:
                self._is_manual_mode = is_manual_from_plc
                self._mode_toggle.set_mode("MANUAL" if is_manual_from_plc else "AUTOMATIC")

            paso_alambre = data.get("Paso_Alambre", 0)
            paso_pinza = data.get("Paso_Pinza", 0)
            in_reset = (paso_alambre == 0) and (paso_pinza == 0)
            self._update_mode_toggle_state(in_reset)

            continuous_active = data.get("S4_CONTINUOUS", False)
            self._update_debug_state(continuous_active)
        else:
            self._update_mode_toggle_state(True)

        self._update_outputs_mode()

    @Slot(bool)
    def _on_connection(self, connected: bool) -> None:
        self._settings_view.set_connection_status(connected)
        if connected:
            self._btn_connection.setText("CONECTADO")
            self._btn_connection.setStyleSheet("""
                QPushButton {
                    color: #00e676;
                    background-color: transparent;
                    border: none;
                    padding: 12px;
                    text-align: left;
                }
            """)
        else:
            self._btn_connection.setText("DESCONECTADO")
            self._btn_connection.setStyleSheet("""
                QPushButton {
                    color: #ff1744;
                    background-color: transparent;
                    border: none;
                    padding: 12px;
                    text-align: left;
                }
            """)

    @Slot()
    def _on_step_next(self) -> None:
        self._worker.enqueue_write("BTN_STEP", True)
        self._worker.enqueue_write("BTN_STEP", False)

    def _on_mode_changed(self, mode: str) -> None:
        if mode == "AUTOMATIC":
            self._worker.enqueue_write("MODE_AUTO", True)
            self._worker.enqueue_write("MODE_MANUAL", False)
            self._is_manual_mode = False
            self._btn_start.show()
            self._toggle_continuous.show()
            self._check_debug.hide()
        else:
            self._worker.enqueue_write("MODE_AUTO", False)
            self._worker.enqueue_write("MODE_MANUAL", True)
            self._is_manual_mode = True
            self._btn_start.hide()
            self._toggle_continuous.hide()
            self._check_debug.show()

        self._update_outputs_mode()

    def _on_debug_changed(self, state: int) -> None:
        self._worker.enqueue_write("MODE_DEBUG", state == Qt.CheckState.Checked.value)

    def _update_mode_toggle_state(self, in_reset: bool) -> None:
        self._mode_toggle.setEnabled(in_reset)

    def _update_debug_state(self, continuous_active: bool) -> None:
        self._check_debug.setEnabled(not continuous_active)
        if continuous_active:
            self._check_debug.setChecked(False)

    def _update_outputs_mode(self) -> None:
        self._outputs_debug_view.set_mode(self._is_manual_mode)

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
