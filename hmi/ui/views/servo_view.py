"""Vista de Control de Servomotor.

Jog Forward/Reverse (mantener presionado), slider de velocidad,
displays de posicion actual vs target.
"""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QSlider,
    QVBoxLayout,
    QWidget,
)

from hmi.ui.widgets import IndustrialButton, SectionFrame, ServoPositionDisplay


class ServoView(QWidget):
    """Vista de control del servomotor."""

    jog_fwd = Signal(bool)
    jog_rev = Signal(bool)
    speed_changed = Signal(int)
    position_changed = Signal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._build_ui()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setSpacing(16)
        root.setContentsMargins(20, 20, 20, 20)

        title = QLabel("CONTROL SERVOMOTOR")
        title.setFont(QFont("Segoe UI", 20, QFont.Weight.Bold))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("color: #e94560; padding: 10px;")
        root.addWidget(title)

        pos_frame = SectionFrame("Posicion")
        pl = pos_frame.content_layout
        pos_row = QHBoxLayout()
        self._display_actual = ServoPositionDisplay("Posicion Actual")
        pos_row.addWidget(self._display_actual)
        self._display_target = ServoPositionDisplay("Posicion Objetivo")
        self._display_target._value_label.setStyleSheet("""
            QLabel {
                color: #ff9800;
                background-color: #0d1117;
                border: 2px solid #333333;
                border-radius: 8px;
                padding: 10px;
                min-width: 160px;
            }
        """)
        pos_row.addWidget(self._display_target)
        pos_row.addStretch()
        pl.addLayout(pos_row)

        target_row = QHBoxLayout()
        target_lbl = QLabel("Posicion Target:")
        target_lbl.setStyleSheet("color: #cccccc; font-size: 14px;")
        target_row.addWidget(target_lbl)
        self._pos_slider = QSlider(Qt.Orientation.Horizontal)
        self._pos_slider.setRange(0, 10000)
        self._pos_slider.setStyleSheet("""
            QSlider::groove:horizontal {
                height: 12px;
                background: #333333;
                border-radius: 6px;
            }
            QSlider::handle:horizontal {
                background: #ff9800;
                width: 24px;
                margin: -6px 0;
                border-radius: 12px;
            }
        """)
        self._pos_slider.valueChanged.connect(self._on_pos_changed)
        target_row.addWidget(self._pos_slider, stretch=1)
        self._pos_value_label = QLabel("0")
        self._pos_value_label.setStyleSheet("color: #ff9800; font-size: 16px; font-weight: bold;")
        self._pos_value_label.setFixedWidth(80)
        target_row.addWidget(self._pos_value_label)
        pl.addLayout(target_row)
        root.addWidget(pos_frame)

        jog_frame = SectionFrame("Jog (Mantener Presionado)")
        jl = jog_frame.content_layout

        speed_row = QHBoxLayout()
        speed_lbl = QLabel("Velocidad:")
        speed_lbl.setStyleSheet("color: #cccccc; font-size: 14px;")
        speed_row.addWidget(speed_lbl)
        self._speed_slider = QSlider(Qt.Orientation.Horizontal)
        self._speed_slider.setRange(0, 3000)
        self._speed_slider.setValue(500)
        self._speed_slider.setStyleSheet("""
            QSlider::groove:horizontal {
                height: 12px;
                background: #333333;
                border-radius: 6px;
            }
            QSlider::handle:horizontal {
                background: #00e676;
                width: 24px;
                margin: -6px 0;
                border-radius: 12px;
            }
        """)
        self._speed_slider.valueChanged.connect(self._on_speed_changed)
        speed_row.addWidget(self._speed_slider, stretch=1)
        self._speed_label = QLabel("500 RPM")
        self._speed_label.setStyleSheet("color: #00e676; font-size: 16px; font-weight: bold;")
        self._speed_label.setFixedWidth(100)
        speed_row.addWidget(self._speed_label)
        jl.addLayout(speed_row)

        jog_row = QHBoxLayout()
        jog_row.setSpacing(30)
        self._btn_jog_fwd = IndustrialButton("JOG >>>", "start", 200, 90)
        self._btn_jog_fwd.pressed.connect(lambda: self.jog_fwd.emit(True))
        self._btn_jog_fwd.released.connect(lambda: self.jog_fwd.emit(False))
        jog_row.addWidget(self._btn_jog_fwd)

        self._display_speed = ServoPositionDisplay("Velocidad Actual")
        jog_row.addWidget(self._display_speed)

        self._btn_jog_rev = IndustrialButton("<<< JOG", "stop", 200, 90)
        self._btn_jog_rev.pressed.connect(lambda: self.jog_rev.emit(True))
        self._btn_jog_rev.released.connect(lambda: self.jog_rev.emit(False))
        jog_row.addWidget(self._btn_jog_rev)
        jl.addLayout(jog_row)
        root.addWidget(jog_frame)

        torque_frame = SectionFrame("Torque")
        tl = torque_frame.content_layout
        self._display_torque = ServoPositionDisplay("Torque Actual")
        tl.addWidget(self._display_torque, alignment=Qt.AlignmentFlag.AlignCenter)
        root.addWidget(torque_frame)

        root.addStretch()

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
