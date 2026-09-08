"""Vista de Control de Servomotor.

Secciones navegables: Posicion, Jog, Velocidad.
"""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSlider,
    QVBoxLayout,
    QWidget,
)

from hmi.ui.widgets import SectionFrame, ServoPositionDisplay


class ServoView(QWidget):
    """Vista de control del servomotor con navegacion por secciones."""

    jog_fwd = Signal(bool)
    jog_rev = Signal(bool)
    speed_changed = Signal(int)
    position_changed = Signal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._current_section = 0
        self._sections = []
        self._build_ui()

    def _build_ui(self) -> None:
        self.setStyleSheet("background-color: #0f0f23;")
        root = QVBoxLayout(self)
        root.setSpacing(10)
        root.setContentsMargins(20, 10, 20, 10)

        title = QLabel("CONTROL SERVOMOTOR")
        title.setFont(QFont("Segoe UI", 18, QFont.Weight.Bold))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("color: #e94560; padding: 8px;")
        root.addWidget(title)

        nav_layout = QHBoxLayout()
        nav_layout.setSpacing(20)

        self._btn_up = QPushButton("▲")
        self._btn_up.setFixedSize(60, 40)
        self._btn_up.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        self._btn_up.setStyleSheet("""
            QPushButton {
                background-color: #16213e;
                color: #e94560;
                border: 2px solid #e94560;
                border-radius: 8px;
            }
            QPushButton:hover {
                background-color: #e94560;
                color: #ffffff;
            }
        """)
        self._btn_up.clicked.connect(self._on_nav_up)
        nav_layout.addWidget(self._btn_up)

        self._section_title = QLabel("POSICION")
        self._section_title.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        self._section_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._section_title.setStyleSheet("color: #ffffff; padding: 8px;")
        nav_layout.addWidget(self._section_title, stretch=1)

        self._btn_down = QPushButton("▼")
        self._btn_down.setFixedSize(60, 40)
        self._btn_down.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        self._btn_down.setStyleSheet("""
            QPushButton {
                background-color: #16213e;
                color: #e94560;
                border: 2px solid #e94560;
                border-radius: 8px;
            }
            QPushButton:hover {
                background-color: #e94560;
                color: #ffffff;
            }
        """)
        self._btn_down.clicked.connect(self._on_nav_down)
        nav_layout.addWidget(self._btn_down)

        root.addLayout(nav_layout)

        self._container = QVBoxLayout()
        self._container.setSpacing(15)
        root.addLayout(self._container, stretch=1)

        self._build_position_section()
        self._build_jog_section()
        self._build_speed_section()

        self._show_section(0)
        root.addStretch()

    def _build_position_section(self) -> None:
        section = QWidget(self)
        section.setVisible(False)
        layout = QVBoxLayout(section)
        layout.setSpacing(15)

        pos_frame = SectionFrame("Posicion Actual vs Objetivo", section)
        pl = pos_frame.content_layout

        displays_row = QHBoxLayout()
        displays_row.setSpacing(30)
        self._display_actual = ServoPositionDisplay("Actual")
        displays_row.addWidget(self._display_actual)

        self._display_target = ServoPositionDisplay("Objetivo")
        displays_row.addWidget(self._display_target)
        pl.addLayout(displays_row)

        layout.addWidget(pos_frame)

        slider_frame = SectionFrame("Ajustar Posicion Target", section)
        sl = slider_frame.content_layout

        slider_row = QHBoxLayout()
        slider_row.setSpacing(15)

        self._pos_slider = QSlider(Qt.Orientation.Horizontal)
        self._pos_slider.setRange(0, 10000)
        self._pos_slider.setMinimumHeight(50)
        self._pos_slider.setStyleSheet("""
            QSlider::groove:horizontal {
                height: 20px;
                background: #1a1a2e;
                border: 2px solid #333333;
                border-radius: 10px;
            }
            QSlider::handle:horizontal {
                background: #ff9800;
                width: 30px;
                height: 30px;
                margin: -5px 0;
                border-radius: 15px;
            }
            QSlider::handle:horizontal:hover {
                background: #ffa726;
            }
        """)
        self._pos_slider.valueChanged.connect(self._on_pos_changed)
        slider_row.addWidget(self._pos_slider, stretch=1)

        self._pos_value_label = QLabel("0")
        self._pos_value_label.setFont(QFont("Consolas", 16, QFont.Weight.Bold))
        self._pos_value_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._pos_value_label.setStyleSheet("""
            QLabel {
                color: #ff9800;
                background-color: #1a1a2e;
                border: 2px solid #333333;
                border-radius: 8px;
                padding: 8px 15px;
                min-width: 80px;
            }
        """)
        slider_row.addWidget(self._pos_value_label)

        sl.addLayout(slider_row)
        layout.addWidget(slider_frame)

        self._sections.append(section)
        self._container.addWidget(section)

    def _build_jog_section(self) -> None:
        section = QWidget(self)
        section.setVisible(False)
        layout = QVBoxLayout(section)
        layout.setSpacing(15)

        jog_frame = SectionFrame("Jog (Mantener Presionado)", section)
        jl = jog_frame.content_layout

        buttons_row = QHBoxLayout()
        buttons_row.setSpacing(40)

        self._btn_jog_rev = QPushButton("<<< JOG")
        self._btn_jog_rev.setMinimumHeight(80)
        self._btn_jog_rev.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        self._btn_jog_rev.setStyleSheet("""
            QPushButton {
                background-color: #c62828;
                color: #ffffff;
                border: 3px solid #ef5350;
                border-radius: 10px;
                padding: 15px 30px;
            }
            QPushButton:hover {
                background-color: #ef5350;
            }
            QPushButton:pressed {
                background-color: #b71c1c;
            }
        """)
        self._btn_jog_rev.pressed.connect(lambda: self.jog_rev.emit(True))
        self._btn_jog_rev.released.connect(lambda: self.jog_rev.emit(False))
        buttons_row.addWidget(self._btn_jog_rev)

        buttons_row.addStretch()

        self._btn_jog_fwd = QPushButton("JOG >>>")
        self._btn_jog_fwd.setMinimumHeight(80)
        self._btn_jog_fwd.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        self._btn_jog_fwd.setStyleSheet("""
            QPushButton {
                background-color: #2e7d32;
                color: #ffffff;
                border: 3px solid #4caf50;
                border-radius: 10px;
                padding: 15px 30px;
            }
            QPushButton:hover {
                background-color: #4caf50;
            }
            QPushButton:pressed {
                background-color: #1b5e20;
            }
        """)
        self._btn_jog_fwd.pressed.connect(lambda: self.jog_fwd.emit(True))
        self._btn_jog_fwd.released.connect(lambda: self.jog_fwd.emit(False))
        buttons_row.addWidget(self._btn_jog_fwd)

        jl.addLayout(buttons_row)
        layout.addWidget(jog_frame)

        torque_frame = SectionFrame("Torque", section)
        tl = torque_frame.content_layout

        torque_row = QHBoxLayout()
        self._display_torque = ServoPositionDisplay("Torque Actual")
        torque_row.addWidget(self._display_torque)
        torque_row.addStretch()
        tl.addLayout(torque_row)

        layout.addWidget(torque_frame)

        self._sections.append(section)
        self._container.addWidget(section)

    def _build_speed_section(self) -> None:
        section = QWidget(self)
        section.setVisible(False)
        layout = QVBoxLayout(section)
        layout.setSpacing(15)

        speed_frame = SectionFrame("Velocidad", section)
        sl = speed_frame.content_layout

        speed_row = QHBoxLayout()
        speed_row.setSpacing(15)

        self._speed_slider = QSlider(Qt.Orientation.Horizontal)
        self._speed_slider.setRange(0, 3000)
        self._speed_slider.setValue(500)
        self._speed_slider.setMinimumHeight(50)
        self._speed_slider.setStyleSheet("""
            QSlider::groove:horizontal {
                height: 20px;
                background: #1a1a2e;
                border: 2px solid #333333;
                border-radius: 10px;
            }
            QSlider::handle:horizontal {
                background: #00e676;
                width: 30px;
                height: 30px;
                margin: -5px 0;
                border-radius: 15px;
            }
            QSlider::handle:horizontal:hover {
                background: #69f0ae;
            }
        """)
        self._speed_slider.valueChanged.connect(self._on_speed_changed)
        speed_row.addWidget(self._speed_slider, stretch=1)

        self._speed_label = QLabel("500 RPM")
        self._speed_label.setFont(QFont("Consolas", 16, QFont.Weight.Bold))
        self._speed_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._speed_label.setStyleSheet("""
            QLabel {
                color: #00e676;
                background-color: #1a1a2e;
                border: 2px solid #333333;
                border-radius: 8px;
                padding: 8px 15px;
                min-width: 100px;
            }
        """)
        speed_row.addWidget(self._speed_label)

        sl.addLayout(speed_row)
        layout.addWidget(speed_frame)

        actual_speed_frame = SectionFrame("Velocidad Actual", section)
        asl = actual_speed_frame.content_layout

        actual_row = QHBoxLayout()
        self._display_speed = ServoPositionDisplay("Velocidad")
        actual_row.addWidget(self._display_speed)
        actual_row.addStretch()
        asl.addLayout(actual_row)

        layout.addWidget(actual_speed_frame)

        self._sections.append(section)
        self._container.addWidget(section)

    def _show_section(self, index: int) -> None:
        for i, section in enumerate(self._sections):
            section.setVisible(i == index)

        titles = ["POSICION", "JOG", "VELOCIDAD"]
        self._section_title.setText(titles[index])
        self._current_section = index

    def _on_nav_up(self) -> None:
        new_index = (self._current_section - 1) % len(self._sections)
        self._show_section(new_index)

    def _on_nav_down(self) -> None:
        new_index = (self._current_section + 1) % len(self._sections)
        self._show_section(new_index)

    def _on_speed_changed(self, value: int) -> None:
        self._speed_label.setText(f"{value} RPM")
        self.speed_changed.emit(value)

    def _on_pos_changed(self, value: int) -> None:
        self._pos_value_label.setText(str(value))
        self.position_changed.emit(value)

    def update_data(self, data: dict) -> None:
        self._display_actual.set_value(data.get("SERVO_POS_ACTUAL", 0))
        self._display_target.set_value(data.get("SERVO_POS_TARGET", 0))
        self._display_speed.set_value(data.get("SERVO_ACTUAL_SPEED", 0))
        self._display_torque.set_value(data.get("SERVO_TORQUE", 0))
