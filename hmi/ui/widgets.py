"""Widgets industriales reutilizables para HMI tactil.

Botones gigantes, LEDs de estado, toggles de valvula y displays numricos
con tema oscuro de alto contraste para pantallas industriales.
"""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal, QTimer
from PySide6.QtGui import QColor, QFont, QPainter, QPen, QBrush
from PySide6.QtWidgets import (
    QButtonGroup,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)


class StatusLED(QWidget):
    """Indicador LED circular con label."""

    def __init__(self, label: str = "", color_off: str = "#555555",
                 color_on: str = "#00e676", size: int = 24, parent=None):
        super().__init__(parent)
        self._on = False
        self._color_off = QColor(color_off)
        self._color_on = QColor(color_on)
        self._size = size
        self._label_text = label

        self.setFixedSize(size + 10, size + 30 if label else size)

    def set_on(self, on: bool) -> None:
        self._on = on
        self.update()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        color = self._color_on if self._on else self._color_off
        painter.setPen(QPen(QColor("#333333"), 1))
        painter.setBrush(QBrush(color))
        y_offset = 28 if self._label_text else 0
        painter.drawEllipse(5, 2, self._size, self._size)
        painter.end()

        if self._label_text:
            painter2 = QPainter(self)
            painter2.setPen(QPen(QColor("#cccccc")))
            font = QFont("Segoe UI", 8)
            painter2.setFont(font)
            painter2.drawText(0, self._size + 4, self.width(), 20,
                              Qt.AlignmentFlag.AlignHCenter, self._label_text)
            painter2.end()


class SimpleLED(QWidget):
    """LED circular simple y pequeno para indicadores de estado."""

    def __init__(self, size: int = 14, parent=None):
        super().__init__(parent)
        self._on = False
        self._size = size
        self._color_on = QColor("#00e676")
        self._color_off = QColor("#555555")
        self.setFixedSize(size, size)

    def set_on(self, on: bool) -> None:
        self._on = on
        self.update()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        color = self._color_on if self._on else self._color_off
        painter.setPen(QPen(QColor("#333333"), 1))
        painter.setBrush(QBrush(color))
        painter.drawEllipse(0, 0, self._size, self._size)
        painter.end()


class IndustrialButton(QPushButton):
    """Boton tactil industrial grande con estados de color."""

    STYLES = {
        "start": ("#1b5e20", "#2e7d32", "#4caf50"),
        "stop": ("#b71c1c", "#c62828", "#ef5350"),
        "emergency": ("#880e0e", "#b71c1c", "#ff1744"),
        "pause": ("#e65100", "#ef6c00", "#ff9800"),
        "cycle_stop": ("#f57f17", "#f9a825", "#fdd835"),
        "neutral": ("#263238", "#37474f", "#546e7a"),
        "reset": ("#1a1a1a", "#2d2d2d", "#404040"),
        "red_stop": ("#8b0000", "#b71c1c", "#ff1744"),
    }

    def __init__(self, label: str, style: str = "neutral",
                 min_width: int = 160, min_height: int = 80, parent=None):
        super().__init__(label, parent)
        self._style_name = style
        self.setMinimumSize(min_width, min_height)
        self.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setCheckable(True)
        self._apply_style(False)

    def _apply_style(self, checked: bool) -> None:
        dark, mid, light = self.STYLES.get(self._style_name, self.STYLES["neutral"])
        bg = light if checked else mid
        self.setStyleSheet(f"""
            QPushButton {{
                background-color: {bg};
                color: #ffffff;
                border: 2px solid {light};
                border-radius: 8px;
                padding: 10px 20px;
                font-size: 16px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: {light};
                border-color: #ffffff;
            }}
            QPushButton:pressed {{
                background-color: {dark};
            }}
            QPushButton:checked {{
                background-color: {light};
                border-color: #ffffff;
            }}
        """)

    def _setup_emergency(self) -> None:
        self.setMinimumSize(200, 100)
        self.setFont(QFont("Segoe UI", 18, QFont.Weight.Bold))


class CircularButton(QPushButton):
    """Boton circular para controles industriales."""

    STYLES = {
        "start": ("#1b5e20", "#2e7d32", "#4caf50"),
        "stop": ("#b71c1c", "#c62828", "#ef5350"),
        "reset": ("#1a1a1a", "#2d2d2d", "#404040"),
        "red_stop": ("#f57f17", "#f9a825", "#ffeb3b"),
    }

    def __init__(self, label: str, style: str = "reset", size: int = 120, parent=None):
        super().__init__(label, parent)
        self._style_name = style
        self._size = size
        self.setFixedSize(size, size)
        self.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setCheckable(True)
        self._apply_style(False)

    def _apply_style(self, checked: bool) -> None:
        dark, mid, light = self.STYLES.get(self._style_name, self.STYLES["reset"])
        bg = light if checked else mid
        self.setStyleSheet(f"""
            QPushButton {{
                background-color: {bg};
                color: #ffffff;
                border: 3px solid {light};
                border-radius: {self._size // 2}px;
                font-size: 14px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: {light};
                border-color: #ffffff;
            }}
            QPushButton:pressed {{
                background-color: {dark};
            }}
            QPushButton:checked {{
                background-color: {light};
                border-color: #ffffff;
            }}
        """)

    def setChecked(self, checked: bool) -> None:
        super().setChecked(checked)
        self._apply_style(checked)

    def set_down(self, down: bool) -> None:
        super().setDown(down)
        self._apply_style(self.isChecked())


class ModeToggle(QWidget):
    """Toggle selector between MANUAL and AUTOMATIC modes."""

    mode_changed = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._current_mode = "MANUAL"
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self._btn = QPushButton("MANUAL")
        self._btn.setCheckable(True)
        self._btn.setChecked(True)
        self._btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._btn.toggled.connect(self._on_toggled)
        layout.addWidget(self._btn)

        self._apply_style()

    def _on_toggled(self, checked: bool) -> None:
        if checked:
            self._current_mode = "MANUAL"
        else:
            self._current_mode = "AUTOMATIC"
        self._apply_style()
        self.mode_changed.emit(self._current_mode)

    def _apply_style(self) -> None:
        if self._current_mode == "MANUAL":
            style = """
                QPushButton {
                    background-color: #ff9800;
                    color: #ffffff;
                    border: 2px solid #ff9800;
                    border-radius: 6px;
                    padding: 8px 16px;
                    font-weight: bold;
                    font-size: 13px;
                }
                QPushButton:hover {
                    background-color: #ffa726;
                }
            """
        else:
            style = """
                QPushButton {
                    background-color: #00e676;
                    color: #000000;
                    border: 2px solid #00e676;
                    border-radius: 6px;
                    padding: 8px 16px;
                    font-weight: bold;
                    font-size: 13px;
                }
                QPushButton:hover {
                    background-color: #69f0ae;
                }
            """
        self._btn.setStyleSheet(style)
        self._btn.setText(self._current_mode)

    def set_mode(self, mode: str) -> None:
        if mode == self._current_mode:
            return
        self._current_mode = mode
        self._btn.setChecked(mode == "MANUAL")
        self._apply_style()

    def current_mode(self) -> str:
        return self._current_mode

    def setEnabled(self, enabled: bool) -> None:
        super().setEnabled(enabled)
        self._btn.setEnabled(enabled)
        if not enabled:
            self._btn.setStyleSheet("""
                QPushButton {
                    background-color: transparent;
                    color: #444444;
                    border: 2px solid #333333;
                    border-radius: 6px;
                    padding: 8px 16px;
                    font-weight: bold;
                    font-size: 13px;
                }
            """)


class ValveToggle(QWidget):
    """Toggle de valvula neumatica con LED + boton grande."""

    toggled_signal = Signal(int, bool)

    def __init__(self, valve_number: int, label: str | None = None, parent=None):
        super().__init__(parent)
        self._number = valve_number
        self._active = False

        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setSpacing(2)

        self._btn = QPushButton("OFF")
        self._btn.setMinimumSize(100, 50)
        self._btn.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        self._btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._btn.setCheckable(True)
        self._btn.setStyleSheet("""
            QPushButton {
                background-color: #37474f;
                color: #ffffff;
                border: 2px solid #546e7a;
                border-radius: 8px;
                padding: 8px 20px;
                font-size: 16px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #455a64;
            }
            QPushButton:checked {
                background-color: #4caf50;
                border-color: #4caf50;
            }
            QPushButton:checked:hover {
                background-color: #66bb6a;
            }
        """)
        self._btn.toggled.connect(self._on_toggled)
        layout.addWidget(self._btn)

        self._lbl = QLabel(label or f"Salida {valve_number}")
        self._lbl.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        self._lbl.setStyleSheet("color: #aaaaaa; font-size: 10px;")
        layout.addWidget(self._lbl)

    def set_label_text(self, text: str) -> None:
        self._lbl.setText(text)

    def set_button_text(self, text: str) -> None:
        self._btn.setText(text)

    def _on_toggled(self, checked: bool) -> None:
        self._active = checked
        self._btn.setText("ON" if checked else "OFF")
        self.toggled_signal.emit(self._number, checked)

    def set_state(self, active: bool) -> None:
        self._active = active
        self._btn.setChecked(active)
        self._btn.setText("ON" if active else "OFF")

    def setEnabled(self, enabled: bool) -> None:
        super().setEnabled(enabled)
        self._btn.setEnabled(enabled)
        self._lbl.setEnabled(enabled)
        if not enabled:
            self._btn.setStyleSheet("""
                QPushButton {
                    background-color: #333333;
                    color: #666666;
                    border: 2px solid #444444;
                    border-radius: 8px;
                    padding: 8px 20px;
                    font-size: 16px;
                    font-weight: bold;
                }
            """)
        else:
            self._btn.setText("ON" if self._active else "OFF")
            self._btn.setStyleSheet("""
                QPushButton {
                    background-color: #37474f;
                    color: #ffffff;
                    border: 2px solid #546e7a;
                    border-radius: 8px;
                    padding: 8px 20px;
                    font-size: 16px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: #455a64;
                }
                QPushButton:checked {
                    background-color: #4caf50;
                    border-color: #4caf50;
                }
                QPushButton:checked:hover {
                    background-color: #66bb6a;
                }
            """)


class ServoPositionDisplay(QWidget):
    """Display numerico grande tipo HMI industrial para posicion servo."""

    def __init__(self, label: str = "Posicion", parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        title = QLabel(label)
        title.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        title.setStyleSheet("color: #aaaaaa; font-size: 12px; font-weight: bold;")
        layout.addWidget(title)

        self._value_label = QLabel("0")
        self._value_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._value_label.setFont(QFont("Consolas", 36, QFont.Weight.Bold))
        self._value_label.setStyleSheet("""
            QLabel {
                color: #00e676;
                background-color: #0d1117;
                border: 2px solid #333333;
                border-radius: 8px;
                padding: 10px;
                min-width: 160px;
            }
        """)
        layout.addWidget(self._value_label)

    def set_value(self, value: int | float) -> None:
        self._value_label.setText(str(value))


class SectionFrame(QFrame):
    """Frame con titulo para agrupar controles en vistas."""

    def __init__(self, title: str, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.WindowFlags())
        self.setStyleSheet("""
            QFrame {
                background-color: #1a1a2e;
                border: 2px solid #333333;
                border-radius: 8px;
                padding: 10px;
            }
        """)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)

        self._layout = QVBoxLayout(self)
        self._layout.setSpacing(8)

        header = QLabel(title)
        header.setFont(QFont("Segoe UI", 13, QFont.Weight.Bold))
        header.setStyleSheet("color: #e94560; border: none; padding: 4px; background: transparent;")
        self._layout.addWidget(header)

    @property
    def content_layout(self) -> QVBoxLayout:
        return self._layout


class AlarmIcon(QWidget):
    """Icono dibujado con QPainter para hormonas/sensores."""

    ICON_BRUSH = "brush"
    ICON_PRESSURE = "pressure"
    ICON_CHECK = "check"
    ICON_WARNING = "warning"

    def __init__(self, icon_type: str, size: int = 80, parent=None):
        super().__init__(parent)
        self._icon_type = icon_type
        self._size = size
        self.setFixedSize(size, size)

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(QPen(QColor("#888888"), 2))
        painter.setBrush(QBrush(QColor("#888888")))

        if self._icon_type == self.ICON_BRUSH:
            self._draw_brush(painter)
        elif self._icon_type == self.ICON_PRESSURE:
            self._draw_pressure(painter)
        elif self._icon_type == self.ICON_CHECK:
            self._draw_check(painter)
        elif self._icon_type == self.ICON_WARNING:
            self._draw_warning(painter)

        painter.end()

    def _draw_brush(self, painter: QPainter) -> None:
        s = self._size
        painter.setPen(QPen(QColor("#cccccc"), 2))
        painter.setBrush(QBrush(QColor("#555555")))

        brush_width = s * 0.7
        brush_height = s * 0.3
        brush_x = (s - brush_width) / 2
        brush_y = s * 0.55
        painter.drawRect(int(brush_x), int(brush_y), int(brush_width), int(brush_height))

        painter.setBrush(QBrush(QColor("#aaaaaa")))
        painter.setPen(QPen(QColor("#888888"), 1))
        bristle_count = 8
        bristle_width = brush_width / (bristle_count + 1)
        for i in range(bristle_count):
            bx = brush_x + bristle_width * (i + 0.5)
            painter.drawLine(int(bx), int(brush_y), int(bx), int(brush_y - s * 0.45))

    def _draw_pressure(self, painter: QPainter) -> None:
        s = self._size
        cx, cy = s / 2, s / 2
        radius = s * 0.3

        painter.setPen(QPen(QColor("#cccccc"), 2))
        painter.setBrush(QBrush(QColor("#333333")))
        painter.drawEllipse(int(cx - radius), int(cy - radius), int(radius * 2), int(radius * 2))

        painter.setBrush(QBrush(QColor("#555555")))
        inner_radius = radius * 0.5
        painter.drawEllipse(int(cx - inner_radius), int(cy - inner_radius),
                           int(inner_radius * 2), int(inner_radius * 2))

        painter.setPen(QPen(QColor("#ff4444"), 2))
        arrow_len = radius * 0.4
        painter.drawLine(int(cx), int(cy - radius + 5), int(cx), int(cy - radius - arrow_len))

        painter.setPen(QPen(QColor("#888888"), 1.5))
        for angle in range(0, 360, 45):
            import math
            rad = math.radians(angle)
            x1 = cx + (radius + 3) * math.cos(rad)
            y1 = cy + (radius + 3) * math.sin(rad)
            x2 = cx + (radius + 10) * math.cos(rad)
            y2 = cy + (radius + 10) * math.sin(rad)
            painter.drawLine(int(x1), int(y1), int(x2), int(y2))

    def _draw_check(self, painter: QPainter) -> None:
        s = self._size
        cx, cy = s / 2, s / 2
        radius = s * 0.4

        painter.setBrush(QBrush(QColor("#2e7d32")))
        painter.setPen(QPen(QColor("#4caf50"), 2))
        painter.drawEllipse(int(cx - radius), int(cy - radius), int(radius * 2), int(radius * 2))

        painter.setPen(QPen(QColor("#ffffff"), 4))
        path = []
        check_points = [
            (cx - radius * 0.3, cy),
            (cx - radius * 0.05, cy + radius * 0.3),
            (cx + radius * 0.4, cy - radius * 0.25),
        ]
        for i, (px, py) in enumerate(check_points):
            if i == 0:
                painter.drawLine(int(cx - radius * 0.3), int(cy), int(cx - radius * 0.05), int(cy + radius * 0.3))
                painter.drawLine(int(cx - radius * 0.05), int(cy + radius * 0.3), int(cx + radius * 0.4), int(cy - radius * 0.25))

    def _draw_warning(self, painter: QPainter) -> None:
        s = self._size
        cx, cy = s / 2, s / 2
        size = s * 0.4

        points = [
            (cx, cy - size),
            (cx + size * 0.866, cy + size * 0.5),
            (cx - size * 0.866, cy + size * 0.5),
        ]
        painter.setBrush(QBrush(QColor("#ff9800")))
        painter.setPen(QPen(QColor("#ff9800"), 2))
        painter.drawPolygon(*points)

        painter.setPen(QPen(QColor("#000000"), 3))
        painter.drawLine(int(cx), int(cy - size * 0.3), int(cx), int(cy + size * 0.1))
        painter.drawEllipse(int(cx - 3), int(cy + size * 0.25), 6, 6)


class AlarmCard(QWidget):
    """Card de alarma grande y visible con icono y texto condicional."""

    def __init__(self, name: str, normal_text: str, alarm_text: str,
                 sensor_icon: str, parent=None):
        super().__init__(parent)
        self._is_alarm = False
        self._sensor_icon = sensor_icon
        self._normal_text = normal_text
        self._alarm_text = alarm_text
        self._blink_state = True
        self._blink_timer = QTimer(self)
        self._blink_timer.timeout.connect(self._toggle_blink)
        self._blink_timer.setInterval(400)

        self.setMinimumSize(220, 200)

        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setSpacing(10)

        self._icon = AlarmIcon(sensor_icon, 80)
        layout.addWidget(self._icon, alignment=Qt.AlignmentFlag.AlignCenter)

        self._name_label = QLabel(name)
        self._name_label.setFont(QFont("Segoe UI", 18, QFont.Weight.Bold))
        self._name_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._name_label.setStyleSheet("color: #cccccc; background: transparent;")
        layout.addWidget(self._name_label)

        self._status_label = QLabel(normal_text)
        self._status_label.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        self._status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self._status_label)

        self._update_visual(False)

    def set_normal(self) -> None:
        self._is_alarm = False
        self._blink_timer.stop()
        self._icon._icon_type = AlarmIcon.ICON_CHECK
        self._icon.update()
        self._status_label.setText(self._normal_text)
        self._update_visual(False)

    def set_alarm(self) -> None:
        self._is_alarm = True
        self._blink_timer.start()
        self._icon._icon_type = AlarmIcon.ICON_WARNING
        self._icon.update()
        self._status_label.setText(self._alarm_text)
        self._update_visual(True)

    def set_unknown(self) -> None:
        self._is_alarm = False
        self._blink_timer.stop()
        self._icon._icon_type = self._sensor_icon
        self._icon.update()
        self._status_label.setText("—")
        self._update_visual_unknown()

    def _toggle_blink(self) -> None:
        self._blink_state = not self._blink_state
        self._status_label.setStyleSheet(f"""
            QLabel {{
                color: {'#ff4444' if self._blink_state else '#880000'};
                background: transparent;
                font-weight: bold;
                font-size: 16px;
            }}
        """)

    def _update_visual(self, alarm: bool) -> None:
        if alarm:
            border_color = "#ff1744"
            bg_color = "#2d1a1a"
            text_color = "#ff4444"
        else:
            border_color = "#2e7d32"
            bg_color = "#1a2e1a"
            text_color = "#4caf50"

        self.setStyleSheet(f"""
            QWidget {{
                background-color: {bg_color};
                border: 3px solid {border_color};
                border-radius: 12px;
            }}
        """)
        self._status_label.setStyleSheet(f"""
            QLabel {{
                color: {text_color};
                background: transparent;
                font-weight: bold;
                font-size: 16px;
            }}
        """)

    def _update_visual_unknown(self) -> None:
        border_color = "#555555"
        bg_color = "#1a1a1a"
        text_color = "#888888"

        self.setStyleSheet(f"""
            QWidget {{
                background-color: {bg_color};
                border: 2px solid {border_color};
                border-radius: 12px;
            }}
        """)
        self._status_label.setStyleSheet(f"""
            QLabel {{
                color: {text_color};
                background: transparent;
                font-weight: bold;
                font-size: 16px;
            }}
        """)


class MachineStateDisplay(QWidget):
    """Display de estado de maquina con pasos y descripciones."""

    ALAMBRE_DESCRIPTIONS = {
        0: "Esperando Inicio",
        10: "Cuchilla Atras",
        20: "Cizalla Activa",
        30: "Cuchilla Adelante",
        40: "Empujando Alambre",
        50: "Lengüeta Posición",
        60: "Pinza Adelante",
        70: "Posicionando",
        80: "Ciclo Terminado",
    }

    PINZA_DESCRIPTIONS = {
        0: "Esperando",
        10: "Cierre Chucks",
        20: "Pinza Fuera",
        30: "Giro Motor",
        40: "Rasurando",
        50: "Rasurado Listo",
        60: "Tijera Arriba",
        70: "Cortando",
        80: "Cierre Tijera",
        90: "Cepillado Cortado",
    }

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumHeight(200)
        self.setStyleSheet("""
            QWidget {
                background-color: #0f0f23;
                border: 1px solid #333333;
                border-radius: 8px;
            }
        """)

        main_layout = QVBoxLayout(self)
        main_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.setSpacing(12)

        self._status_label = QLabel("ESPERANDO")
        self._status_label.setFont(QFont("Segoe UI", 24, QFont.Weight.Bold))
        self._status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._status_label.setStyleSheet("color: #00e676; background: transparent;")
        main_layout.addWidget(self._status_label)

        steps_layout = QHBoxLayout()
        steps_layout.setSpacing(30)

        alambre_frame = self._make_step_frame("ALAMBRE")
        self._alambre_step = alambre_frame.findChild(QLabel, "step_value")
        self._alambre_desc = alambre_frame.findChild(QLabel, "step_desc")
        steps_layout.addWidget(alambre_frame)

        pinza_frame = self._make_step_frame("PINZA")
        self._pinza_step = pinza_frame.findChild(QLabel, "step_value")
        self._pinza_desc = pinza_frame.findChild(QLabel, "step_desc")
        steps_layout.addWidget(pinza_frame)

        main_layout.addLayout(steps_layout)

        self._sensor_label = QLabel("Sensor: —")
        self._sensor_label.setFont(QFont("Segoe UI", 12))
        self._sensor_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._sensor_label.setStyleSheet("color: #888888; background: transparent;")
        main_layout.addWidget(self._sensor_label)

    def _make_step_frame(self, title: str) -> QFrame:
        frame = QFrame()
        frame.setStyleSheet("""
            QFrame {
                background-color: #16213e;
                border: 1px solid #333333;
                border-radius: 8px;
                padding: 10px;
                min-width: 150px;
            }
        """)
        layout = QVBoxLayout(frame)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setSpacing(4)

        title_label = QLabel(title)
        title_label.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_label.setStyleSheet("color: #e94560; background: transparent;")
        layout.addWidget(title_label)

        step_value = QLabel("0")
        step_value.setObjectName("step_value")
        step_value.setFont(QFont("Consolas", 36, QFont.Weight.Bold))
        step_value.setAlignment(Qt.AlignmentFlag.AlignCenter)
        step_value.setStyleSheet("color: #00e676; background: transparent;")
        layout.addWidget(step_value)

        step_desc = QLabel("—")
        step_desc.setObjectName("step_desc")
        step_desc.setFont(QFont("Segoe UI", 10))
        step_desc.setAlignment(Qt.AlignmentFlag.AlignCenter)
        step_desc.setStyleSheet("color: #888888; background: transparent;")
        step_desc.setWordWrap(True)
        layout.addWidget(step_desc)

        return frame

    def update_state(self, paso_alambre: int, paso_pinza: int, sensor_esperado: str = "") -> None:
        self._alambre_step.setText(str(paso_alambre))
        alambre_desc = self.ALAMBRE_DESCRIPTIONS.get(paso_alambre, "—")
        self._alambre_desc.setText(alambre_desc)

        self._pinza_step.setText(str(paso_pinza))
        pinza_desc = self.PINZA_DESCRIPTIONS.get(paso_pinza, "—")
        self._pinza_desc.setText(pinza_desc)

        if sensor_esperado:
            self._sensor_label.setText(f"Sensor: {sensor_esperado}")

        if paso_alambre == 0 and paso_pinza == 0:
            status = "ESPERANDO"
            color = "#888888"
        elif paso_alambre > 0 or paso_pinza > 0:
            status = "CICLO ACTIVO"
            color = "#00e676"
        else:
            status = "EN PROGRESO"
            color = "#ff9800"

        self._status_label.setText(status)
        self._status_label.setStyleSheet(f"color: {color}; background: transparent; font-weight: bold;")
